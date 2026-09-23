"""Formulários do sistema.

ModelForm evita repetir validações que já pertencem aos models. As validações
específicas de apresentação, como normalizar a placa, ficam neste arquivo.
"""

from django import forms

from .models import Customer, Sale, Vehicle


class StyledModelForm(forms.ModelForm):
    """Adiciona classes CSS sem repetir código em todos os formulários."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            elif isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            else:
                css_class = "form-control"
            field.widget.attrs.setdefault("class", css_class)


class VehicleForm(StyledModelForm):
    class Meta:
        model = Vehicle
        fields = (
            "vehicle_type",
            "brand",
            "model",
            "model_year",
            "factory_year",
            "color",
            "license_plate",
            "purchase_price",
            "asking_price",
            "mileage",
            "status",
            "entry_date",
            "description",
        )
        widgets = {
            "entry_date": forms.DateInput(attrs={"type": "date"}),
            "purchase_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "asking_price": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "mileage": forms.NumberInput(attrs={"min": "0"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.status == Vehicle.Status.SOLD:
            # O status vendido só pode voltar ao estoque cancelando a venda.
            self.fields["status"].choices = ((Vehicle.Status.SOLD, "Vendido"),)
            self.fields["status"].disabled = True
        else:
            self.fields["status"].choices = (
                (Vehicle.Status.AVAILABLE, "Disponível"),
                (Vehicle.Status.RESERVED, "Reservado"),
            )

    def clean_license_plate(self):
        plate = self.cleaned_data.get("license_plate")
        return plate.strip().upper() if plate else None


class CustomerForm(StyledModelForm):
    class Meta:
        model = Customer
        fields = ("name", "phone", "email", "document", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}

    def clean_document(self):
        document = self.cleaned_data.get("document", "")
        return document.strip()


class SaleForm(StyledModelForm):
    class Meta:
        model = Sale
        fields = (
            "vehicle",
            "customer",
            "sale_date",
            "final_price",
            "payment_method",
            "notes",
        )
        widgets = {
            "sale_date": forms.DateInput(attrs={"type": "date"}),
            "final_price": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available = Vehicle.objects.exclude(status=Vehicle.Status.SOLD)

        # Ao editar uma venda, o veículo já vendido precisa continuar visível.
        if self.instance.pk:
            available = Vehicle.objects.filter(pk=self.instance.vehicle_id) | available

        self.fields["vehicle"].queryset = available.select_related(
            "brand", "vehicle_type"
        ).distinct()
        self.fields["customer"].queryset = Customer.objects.order_by("name")

    def clean_vehicle(self):
        vehicle = self.cleaned_data["vehicle"]
        confirmed_sale = vehicle.sales.filter(status=Sale.Status.CONFIRMED).exclude(
            pk=self.instance.pk
        )
        if confirmed_sale.exists():
            raise forms.ValidationError("Este veículo já possui uma venda confirmada.")
        return vehicle
