"""Views da aplicação.

As views recebem a requisição, chamam os models/forms e escolhem o template.
As regras de consistência da venda continuam no model ``Sale`` para também
funcionarem no admin e em futuros endpoints de API.
"""

import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CustomerForm, SaleForm, VehicleForm
from .models import Brands, Customer, Sale, Vehicle, VehicleImage, VehicleType


def _percentage_rows(rows, value_key):
    """Acrescenta largura percentual para as barras desenhadas no template."""

    rows = list(rows)
    maximum = max((row[value_key] or 0 for row in rows), default=0)
    for row in rows:
        value = row[value_key] or 0
        row["bar_width"] = round((value / maximum) * 100, 1) if maximum else 0
    return rows


def dashboard_view(request):
    confirmed_sales = Sale.objects.filter(status=Sale.Status.CONFIRMED).select_related(
        "vehicle", "vehicle__brand", "customer"
    )
    stock = Vehicle.objects.exclude(status=Vehicle.Status.SOLD)

    revenue = confirmed_sales.aggregate(total=Sum("final_price"))["total"] or Decimal("0")
    gross_profit = sum((sale.gross_profit for sale in confirmed_sales), Decimal("0"))
    sales_count = confirmed_sales.count()
    average_ticket = revenue / sales_count if sales_count else Decimal("0")
    inventory_value = stock.aggregate(total=Sum("purchase_price"))["total"] or Decimal("0")

    monthly_sales = _percentage_rows(
        confirmed_sales.annotate(month=TruncMonth("sale_date"))
        .values("month")
        .annotate(total=Sum("final_price"), quantity=Count("id"))
        .order_by("month"),
        "total",
    )
    sales_by_brand = _percentage_rows(
        confirmed_sales.values("vehicle__brand__name")
        .annotate(total=Sum("final_price"), quantity=Count("id"))
        .order_by("-quantity", "vehicle__brand__name"),
        "quantity",
    )
    stock_by_type = _percentage_rows(
        stock.values("vehicle_type__name")
        .annotate(quantity=Count("id"))
        .order_by("-quantity"),
        "quantity",
    )

    context = {
        "vehicles_total": Vehicle.objects.count(),
        "available_count": Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE).count(),
        "reserved_count": Vehicle.objects.filter(status=Vehicle.Status.RESERVED).count(),
        "sold_count": Vehicle.objects.filter(status=Vehicle.Status.SOLD).count(),
        "customer_count": Customer.objects.count(),
        "sales_count": sales_count,
        "revenue": revenue,
        "gross_profit": gross_profit,
        "average_ticket": average_ticket,
        "inventory_value": inventory_value,
        "monthly_sales": monthly_sales,
        "sales_by_brand": sales_by_brand,
        "stock_by_type": stock_by_type,
        "recent_sales": confirmed_sales[:6],
        "aging_vehicles": stock.filter(
            entry_date__lte=timezone.localdate() - timedelta(days=60)
        )
        .select_related("brand", "vehicle_type")
        .order_by("entry_date")[:6],
    }
    return render(request, "cars/dashboard.html", context)


def vehicle_list_view(request):
    vehicles = Vehicle.objects.select_related("brand", "vehicle_type").prefetch_related(
        "images"
    )
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    vehicle_type = request.GET.get("type", "")
    brand = request.GET.get("brand", "")
    minimum_price = request.GET.get("min_price", "")
    maximum_price = request.GET.get("max_price", "")

    if query:
        vehicles = vehicles.filter(
            Q(model__icontains=query)
            | Q(brand__name__icontains=query)
            | Q(license_plate__icontains=query)
        )
    if status:
        vehicles = vehicles.filter(status=status)
    if vehicle_type:
        vehicles = vehicles.filter(vehicle_type_id=vehicle_type)
    if brand:
        vehicles = vehicles.filter(brand_id=brand)
    if minimum_price:
        vehicles = vehicles.filter(asking_price__gte=minimum_price)
    if maximum_price:
        vehicles = vehicles.filter(asking_price__lte=maximum_price)

    page = Paginator(vehicles, 12).get_page(request.GET.get("page"))
    context = {
        "page": page,
        "vehicle_types": VehicleType.objects.all(),
        "brands": Brands.objects.all(),
        "status_choices": Vehicle.Status.choices,
        "filters": request.GET,
    }
    return render(request, "cars/vehicle_list.html", context)


def vehicle_detail_view(request, pk):
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("brand", "vehicle_type").prefetch_related("images", "sales"),
        pk=pk,
    )
    return render(request, "cars/vehicle_detail.html", {"vehicle": vehicle})


def _save_uploaded_images(vehicle, files):
    has_cover = vehicle.images.filter(is_cover=True).exists()
    for index, photo in enumerate(files):
        VehicleImage.objects.create(
            vehicle=vehicle,
            photo=photo,
            is_cover=not has_cover and index == 0,
        )


def vehicle_create_view(request):
    form = VehicleForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save()
        _save_uploaded_images(vehicle, request.FILES.getlist("photos"))
        messages.success(request, "Veículo cadastrado com sucesso.")
        return redirect("vehicle_detail", pk=vehicle.pk)
    return render(request, "cars/vehicle_form.html", {"form": form, "title": "Novo veículo"})


def vehicle_update_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehicleForm(request.POST or None, request.FILES or None, instance=vehicle)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save()
        _save_uploaded_images(vehicle, request.FILES.getlist("photos"))
        messages.success(request, "Veículo atualizado com sucesso.")
        return redirect("vehicle_detail", pk=vehicle.pk)
    return render(
        request,
        "cars/vehicle_form.html",
        {"form": form, "vehicle": vehicle, "title": "Editar veículo"},
    )


def vehicle_delete_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        try:
            vehicle.delete()
        except ProtectedError:
            messages.error(request, "Este veículo possui vendas e não pode ser excluído.")
            return redirect("vehicle_detail", pk=vehicle.pk)
        messages.success(request, "Veículo excluído.")
        return redirect("vehicle_list")
    return render(request, "cars/confirm_delete.html", {"object": vehicle, "type": "veículo"})


@require_POST
def vehicle_image_delete_view(request, pk):
    image = get_object_or_404(VehicleImage, pk=pk)
    vehicle = image.vehicle
    was_cover = image.is_cover
    image.delete()
    if was_cover:
        next_image = vehicle.images.first()
        if next_image:
            next_image.is_cover = True
            next_image.save(update_fields=("is_cover",))
    messages.success(request, "Imagem removida.")
    return redirect("vehicle_detail", pk=vehicle.pk)


@require_POST
def vehicle_image_cover_view(request, pk):
    image = get_object_or_404(VehicleImage, pk=pk)
    VehicleImage.objects.filter(vehicle=image.vehicle).update(is_cover=False)
    image.is_cover = True
    image.save(update_fields=("is_cover",))
    messages.success(request, "Imagem de capa alterada.")
    return redirect("vehicle_detail", pk=image.vehicle_id)


def customer_list_view(request):
    customers = Customer.objects.annotate(sales_total=Count("sales")).order_by("name", "pk")
    query = request.GET.get("q", "").strip()
    if query:
        customers = customers.filter(
            Q(name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
            | Q(document__icontains=query)
        )
    page = Paginator(customers, 15).get_page(request.GET.get("page"))
    return render(request, "cars/customer_list.html", {"page": page, "query": query})


def customer_detail_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    sales = customer.sales.select_related("vehicle", "vehicle__brand")
    return render(request, "cars/customer_detail.html", {"customer": customer, "sales": sales})


def customer_create_view(request):
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        customer = form.save()
        messages.success(request, "Cliente cadastrado com sucesso.")
        return redirect("customer_detail", pk=customer.pk)
    return render(request, "cars/customer_form.html", {"form": form, "title": "Novo cliente"})


def customer_update_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cliente atualizado com sucesso.")
        return redirect("customer_detail", pk=customer.pk)
    return render(
        request,
        "cars/customer_form.html",
        {"form": form, "customer": customer, "title": "Editar cliente"},
    )


def customer_delete_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        try:
            customer.delete()
        except ProtectedError:
            messages.error(request, "Este cliente possui vendas e não pode ser excluído.")
            return redirect("customer_detail", pk=customer.pk)
        messages.success(request, "Cliente excluído.")
        return redirect("customer_list")
    return render(request, "cars/confirm_delete.html", {"object": customer, "type": "cliente"})


def sale_list_view(request):
    sales = Sale.objects.select_related("vehicle", "vehicle__brand", "customer")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    payment_method = request.GET.get("payment", "")

    if query:
        sales = sales.filter(
            Q(vehicle__model__icontains=query)
            | Q(vehicle__brand__name__icontains=query)
            | Q(customer__name__icontains=query)
        )
    if status:
        sales = sales.filter(status=status)
    if payment_method:
        sales = sales.filter(payment_method=payment_method)

    page = Paginator(sales, 15).get_page(request.GET.get("page"))
    return render(
        request,
        "cars/sale_list.html",
        {
            "page": page,
            "status_choices": Sale.Status.choices,
            "payment_choices": Sale.PaymentMethod.choices,
            "filters": request.GET,
        },
    )


def sale_detail_view(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related("vehicle", "vehicle__brand", "customer"), pk=pk
    )
    return render(request, "cars/sale_detail.html", {"sale": sale})


def sale_create_view(request):
    initial = {}
    vehicle_id = request.GET.get("vehicle")
    if vehicle_id:
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
        initial = {"vehicle": vehicle, "final_price": vehicle.asking_price}

    form = SaleForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            sale = form.save()
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Venda registrada e estoque atualizado.")
            return redirect("sale_detail", pk=sale.pk)
    return render(request, "cars/sale_form.html", {"form": form, "title": "Registrar venda"})


def sale_update_view(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    form = SaleForm(request.POST or None, instance=sale)
    if request.method == "POST" and form.is_valid():
        try:
            sale = form.save()
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Venda atualizada.")
            return redirect("sale_detail", pk=sale.pk)
    return render(
        request,
        "cars/sale_form.html",
        {"form": form, "sale": sale, "title": "Editar venda"},
    )


@require_POST
def sale_cancel_view(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if sale.status == Sale.Status.CANCELED:
        messages.info(request, "Esta venda já estava cancelada.")
    else:
        sale.cancel()
        messages.success(request, "Venda cancelada e veículo devolvido ao estoque.")
    return redirect("sale_detail", pk=sale.pk)


def reports_view(request):
    confirmed_sales = Sale.objects.filter(status=Sale.Status.CONFIRMED).select_related(
        "vehicle", "vehicle__brand", "customer"
    )
    revenue = confirmed_sales.aggregate(total=Sum("final_price"))["total"] or Decimal("0")
    gross_profit = sum((sale.gross_profit for sale in confirmed_sales), Decimal("0"))
    average_ticket = confirmed_sales.aggregate(value=Avg("final_price"))["value"] or Decimal("0")
    stale_vehicles = Vehicle.objects.exclude(status=Vehicle.Status.SOLD).filter(
        entry_date__lte=timezone.localdate() - timedelta(days=60)
    )
    return render(
        request,
        "cars/reports.html",
        {
            "revenue": revenue,
            "gross_profit": gross_profit,
            "average_ticket": average_ticket,
            "sales_count": confirmed_sales.count(),
            "stale_vehicles": stale_vehicles.select_related("brand", "vehicle_type"),
        },
    )


def _csv_response(filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    return response


def export_sales_csv_view(request):
    response = _csv_response("vendas.csv")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "id",
            "data",
            "status",
            "cliente",
            "tipo",
            "marca",
            "modelo",
            "preco_compra",
            "preco_venda",
            "lucro_bruto",
            "forma_pagamento",
        ]
    )
    for sale in Sale.objects.select_related(
        "customer", "vehicle", "vehicle__brand", "vehicle__vehicle_type"
    ):
        writer.writerow(
            [
                sale.pk,
                sale.sale_date.isoformat(),
                sale.get_status_display(),
                sale.customer.name,
                sale.vehicle.vehicle_type.name,
                sale.vehicle.brand.name,
                sale.vehicle.model,
                sale.vehicle.purchase_price,
                sale.final_price,
                sale.gross_profit,
                sale.get_payment_method_display(),
            ]
        )
    return response


def export_vehicles_csv_view(request):
    response = _csv_response("veiculos.csv")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "id",
            "tipo",
            "marca",
            "modelo",
            "ano_modelo",
            "quilometragem",
            "preco_compra",
            "preco_anunciado",
            "status",
            "entrada_estoque",
            "dias_estoque",
        ]
    )
    for vehicle in Vehicle.objects.select_related("brand", "vehicle_type"):
        writer.writerow(
            [
                vehicle.pk,
                vehicle.vehicle_type.name,
                vehicle.brand.name,
                vehicle.model,
                vehicle.model_year or "",
                vehicle.mileage,
                vehicle.purchase_price,
                vehicle.asking_price,
                vehicle.get_status_display(),
                vehicle.entry_date.isoformat(),
                vehicle.days_in_stock,
            ]
        )
    return response


# Compatibilidade com os endereços antigos do projeto.
def legacy_auto_redirect(request):
    return redirect(reverse("vehicle_list"), permanent=True)
