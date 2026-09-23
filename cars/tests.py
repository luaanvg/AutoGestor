from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Brands, Customer, Sale, Vehicle, VehicleType


class BaseDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.vehicle_type, _ = VehicleType.objects.get_or_create(name="Carro")
        cls.brand = Brands.objects.create(name="Marca Teste")
        cls.brand.vehicle_types.add(cls.vehicle_type)
        cls.customer = Customer.objects.create(
            name="Cliente Teste",
            phone="(12) 99999-9999",
            email="cliente@example.com",
        )
        cls.vehicle = Vehicle.objects.create(
            vehicle_type=cls.vehicle_type,
            brand=cls.brand,
            model="Modelo Teste",
            model_year=2024,
            factory_year=2024,
            purchase_price=Decimal("50000.00"),
            asking_price=Decimal("60000.00"),
            mileage=10000,
            entry_date=timezone.localdate() - timedelta(days=30),
        )


class SaleRuleTests(BaseDataMixin, TestCase):
    def test_confirmed_sale_marks_vehicle_as_sold(self):
        sale = Sale.objects.create(
            vehicle=self.vehicle,
            customer=self.customer,
            final_price=Decimal("59000.00"),
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.SOLD)
        self.assertEqual(sale.gross_profit, Decimal("9000.00"))

    def test_canceled_sale_returns_vehicle_to_stock(self):
        sale = Sale.objects.create(
            vehicle=self.vehicle,
            customer=self.customer,
            final_price=Decimal("59000.00"),
        )
        sale.cancel()
        self.vehicle.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.CANCELED)
        self.assertEqual(self.vehicle.status, Vehicle.Status.AVAILABLE)

    def test_vehicle_cannot_have_two_confirmed_sales(self):
        Sale.objects.create(
            vehicle=self.vehicle,
            customer=self.customer,
            final_price=Decimal("59000.00"),
        )
        duplicate = Sale(
            vehicle=self.vehicle,
            customer=self.customer,
            final_price=Decimal("58000.00"),
        )
        with self.assertRaises(ValidationError):
            duplicate.save()

    def test_sale_before_stock_entry_is_invalid(self):
        sale = Sale(
            vehicle=self.vehicle,
            customer=self.customer,
            sale_date=self.vehicle.entry_date - timedelta(days=1),
            final_price=Decimal("59000.00"),
        )
        with self.assertRaises(ValidationError):
            sale.save()


class VehicleValidationTests(BaseDataMixin, TestCase):
    def test_factory_year_cannot_be_after_model_year(self):
        vehicle = Vehicle(
            vehicle_type=self.vehicle_type,
            brand=self.brand,
            model="Ano inválido",
            model_year=2023,
            factory_year=2024,
            purchase_price=Decimal("10.00"),
            asking_price=Decimal("20.00"),
        )
        with self.assertRaises(ValidationError):
            vehicle.full_clean()

    def test_days_in_stock_is_calculated(self):
        self.assertGreaterEqual(self.vehicle.days_in_stock, 30)


class ViewTests(BaseDataMixin, TestCase):
    def test_dashboard_renders(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Painel gerencial")

    def test_vehicle_filter(self):
        response = self.client.get(reverse("vehicle_list"), {"q": "Modelo Teste"})
        self.assertContains(response, "Modelo Teste")

    def test_sale_creation_updates_stock(self):
        response = self.client.post(
            reverse("sale_create"),
            {
                "vehicle": self.vehicle.pk,
                "customer": self.customer.pk,
                "sale_date": timezone.localdate().isoformat(),
                "final_price": "59000.00",
                "payment_method": Sale.PaymentMethod.PIX,
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.SOLD)

    def test_customer_sale_and_report_pages_render(self):
        sale = Sale.objects.create(
            vehicle=self.vehicle,
            customer=self.customer,
            final_price=Decimal("59000.00"),
        )
        urls = (
            reverse("customer_list"),
            reverse("customer_create"),
            reverse("customer_detail", args=[self.customer.pk]),
            reverse("customer_update", args=[self.customer.pk]),
            reverse("sale_list"),
            reverse("sale_create"),
            reverse("sale_detail", args=[sale.pk]),
            reverse("sale_update", args=[sale.pk]),
            reverse("reports"),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_cancel_sale_endpoint_returns_vehicle_to_stock(self):
        sale = Sale.objects.create(
            vehicle=self.vehicle,
            customer=self.customer,
            final_price=Decimal("59000.00"),
        )
        response = self.client.post(reverse("sale_cancel", args=[sale.pk]))
        self.assertRedirects(response, reverse("sale_detail", args=[sale.pk]))
        sale.refresh_from_db()
        self.vehicle.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.CANCELED)
        self.assertEqual(self.vehicle.status, Vehicle.Status.AVAILABLE)

    def test_csv_exports(self):
        vehicle_response = self.client.get(reverse("export_vehicles_csv"))
        sale_response = self.client.get(reverse("export_sales_csv"))
        self.assertEqual(vehicle_response.status_code, 200)
        self.assertEqual(sale_response.status_code, 200)
        self.assertIn("text/csv", vehicle_response["Content-Type"])


class DemoCommandTests(TestCase):
    def test_seed_demo_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        first_counts = (Vehicle.objects.count(), Customer.objects.count(), Sale.objects.count())
        call_command("seed_demo", verbosity=0)
        second_counts = (Vehicle.objects.count(), Customer.objects.count(), Sale.objects.count())
        self.assertEqual(first_counts, second_counts)
