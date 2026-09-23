"""Modelos principais do sistema de gestão de veículos.

Este arquivo concentra as regras mais importantes do negócio:

* veículos entram no estoque como disponíveis;
* uma venda confirmada muda o veículo para vendido;
* uma venda cancelada devolve o veículo ao estoque;
* um veículo não pode ter duas vendas confirmadas.

Os comentários foram mantidos de propósito para facilitar o estudo do projeto.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


class VehicleType(models.Model):
    """Tipo do veículo: carro ou moto."""

    name = models.CharField("nome", max_length=50, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "tipo de veículo"
        verbose_name_plural = "tipos de veículo"

    def __str__(self):
        return self.name


class Brands(models.Model):
    """Marca que pode estar ligada a um ou mais tipos de veículo."""

    name = models.CharField("nome", max_length=200, unique=True)
    vehicle_types = models.ManyToManyField(
        VehicleType,
        related_name="brands",
        verbose_name="tipos de veículo",
        blank=True,
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "marca"
        verbose_name_plural = "marcas"

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    """Uma unidade física no estoque da loja"""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponível"
        RESERVED = "reserved", "Reservado"
        SOLD = "sold", "Vendido"

    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.PROTECT,
        related_name="vehicles",
        verbose_name="tipo",
    )
    brand = models.ForeignKey(
        Brands,
        on_delete=models.PROTECT,
        related_name="vehicles",
        verbose_name="marca",
    )
    model = models.CharField("modelo", max_length=200)
    model_year = models.PositiveIntegerField("ano do modelo", blank=True, null=True)
    factory_year = models.PositiveIntegerField("ano de fabricação", blank=True, null=True)
    color = models.CharField("cor", max_length=60, blank=True)
    license_plate = models.CharField(
        "placa",
        max_length=10,
        blank=True,
        null=True,
        unique=True,
        help_text="Opcional. Use somente dados fictícios no projeto.",
    )
    purchase_price = models.DecimalField(
        "preço de compra",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    asking_price = models.DecimalField(
        "preço anunciado",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    mileage = models.PositiveIntegerField("quilometragem", default=0)
    status = models.CharField(
        "status",
        max_length=12,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    entry_date = models.DateField("entrada no estoque", default=timezone.localdate)
    description = models.TextField("descrição", blank=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "veículo"
        verbose_name_plural = "veículos"
        indexes = [
            models.Index(fields=("status", "entry_date"), name="vehicle_stock_idx"),
            models.Index(fields=("brand", "model"), name="vehicle_search_idx"),
        ]

    def __str__(self):
        year = f" {self.model_year}" if self.model_year else ""
        return f"{self.brand} {self.model}{year}"

    def clean(self):
        errors = {}
        current_year = timezone.localdate().year + 1

        if self.model_year and not 1886 <= self.model_year <= current_year:
            errors["model_year"] = "Informe um ano de modelo válido."
        if self.factory_year and not 1886 <= self.factory_year <= current_year:
            errors["factory_year"] = "Informe um ano de fabricação válido."
        if self.factory_year and self.model_year and self.factory_year > self.model_year:
            errors["factory_year"] = "O ano de fabricação não pode ser maior que o ano do modelo."
        if self.purchase_price and self.asking_price and self.purchase_price > self.asking_price:
            errors["asking_price"] = (
                "O preço anunciado está abaixo do preço de compra. "
                "Confirme o valor antes de salvar."
            )
        if self.brand_id and self.vehicle_type_id:
            allowed_types = self.brand.vehicle_types.all()
            if allowed_types.exists() and not allowed_types.filter(pk=self.vehicle_type_id).exists():
                errors["brand"] = "Esta marca não está associada ao tipo de veículo escolhido."

        if errors:
            raise ValidationError(errors)

    @property
    def days_in_stock(self):
        """Quantidade de dias entre a entrada e a venda (ou hoje)."""

        confirmed_sale = self.sales.filter(status=Sale.Status.CONFIRMED).first()
        end_date = confirmed_sale.sale_date if confirmed_sale else timezone.localdate()
        return max((end_date - self.entry_date).days, 0)

    @property
    def cover_image(self):
        return self.images.filter(is_cover=True).first() or self.images.first()


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="veículo",
    )
    photo = models.ImageField("foto", upload_to="vehicles/")
    is_cover = models.BooleanField("capa", default=False)
    uploaded_at = models.DateTimeField("enviada em", auto_now_add=True)

    class Meta:
        ordering = ("-is_cover", "id")
        verbose_name = "imagem do veículo"
        verbose_name_plural = "imagens dos veículos"

    def __str__(self):
        return f"Imagem de {self.vehicle}"


class Customer(models.Model):
    name = models.CharField("nome", max_length=200)
    phone = models.CharField("telefone", max_length=30)
    email = models.EmailField("e-mail", blank=True)
    document = models.CharField(
        "documento",
        max_length=30,
        blank=True,
        help_text="Opcional. Use somente documentos fictícios.",
    )
    notes = models.TextField("observações", blank=True)
    created_at = models.DateTimeField("cadastrado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        constraints = [
            models.UniqueConstraint(
                fields=("document",),
                condition=~Q(document=""),
                name="unique_non_empty_customer_document",
            )
        ]

    def __str__(self):
        return self.name


class Sale(models.Model):
    """Venda registrada e sua ligação com cliente e veículo."""

    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmada"
        CANCELED = "canceled", "Cancelada"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Dinheiro"
        PIX = "pix", "Pix"
        FINANCING = "financing", "Financiamento"
        CARD = "card", "Cartão"
        OTHER = "other", "Outro"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="sales",
        verbose_name="veículo",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="sales",
        verbose_name="cliente",
    )
    sale_date = models.DateField("data da venda", default=timezone.localdate)
    final_price = models.DecimalField(
        "valor final",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_method = models.CharField(
        "forma de pagamento",
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PIX,
    )
    status = models.CharField(
        "status",
        max_length=12,
        choices=Status.choices,
        default=Status.CONFIRMED,
        db_index=True,
    )
    notes = models.TextField("observações", blank=True)
    created_at = models.DateTimeField("registrada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        ordering = ("-sale_date", "-created_at")
        verbose_name = "venda"
        verbose_name_plural = "vendas"
        constraints = [
            models.UniqueConstraint(
                fields=("vehicle",),
                condition=Q(status="confirmed"),
                name="unique_confirmed_sale_per_vehicle",
            )
        ]

    def __str__(self):
        return f"Venda #{self.pk or 'nova'} - {self.vehicle}"

    @property
    def gross_profit(self):
        return self.final_price - self.vehicle.purchase_price

    def clean(self):
        errors = {}
        if self.vehicle_id:
            other_confirmed_sale = Sale.objects.filter(
                vehicle_id=self.vehicle_id,
                status=self.Status.CONFIRMED,
            ).exclude(pk=self.pk)
            if self.status == self.Status.CONFIRMED and other_confirmed_sale.exists():
                errors["vehicle"] = "Este veículo já possui uma venda confirmada."
            if self.sale_date and self.sale_date < self.vehicle.entry_date:
                errors["sale_date"] = "A venda não pode ocorrer antes da entrada no estoque."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Salva a venda e mantém o status do estoque sincronizado."""

        self.full_clean()
        with transaction.atomic():
            previous = Sale.objects.filter(pk=self.pk).values("vehicle_id", "status").first()
            super().save(*args, **kwargs)

            if previous and previous["vehicle_id"] != self.vehicle_id:
                Vehicle.objects.filter(pk=previous["vehicle_id"]).update(
                    status=Vehicle.Status.AVAILABLE
                )

            new_vehicle_status = (
                Vehicle.Status.SOLD
                if self.status == self.Status.CONFIRMED
                else Vehicle.Status.AVAILABLE
            )
            Vehicle.objects.filter(pk=self.vehicle_id).update(status=new_vehicle_status)

    def cancel(self):
        self.status = self.Status.CANCELED
        self.save(update_fields=("status", "updated_at"))

    def delete(self, *args, **kwargs):
        vehicle_id = self.vehicle_id
        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            if not Sale.objects.filter(
                vehicle_id=vehicle_id,
                status=self.Status.CONFIRMED,
            ).exists():
                Vehicle.objects.filter(pk=vehicle_id).update(status=Vehicle.Status.AVAILABLE)
            return result
