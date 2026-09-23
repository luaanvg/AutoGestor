"""Cria uma base fictícia para testar o sistema e montar os dashboards."""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from cars.models import Brands, Customer, Sale, Vehicle, VehicleType


class Command(BaseCommand):
    help = "Cria veículos, clientes e vendas fictícias sem apagar os dados existentes."

    def handle(self, *args, **options):
        today = timezone.localdate()
        car_type, _ = VehicleType.objects.get_or_create(name="Carro")
        bike_type, _ = VehicleType.objects.get_or_create(name="Moto")

        brand_types = {
            "Chevrolet": (car_type,),
            "Fiat": (car_type,),
            "Honda": (car_type, bike_type),
            "Toyota": (car_type,),
            "Volkswagen": (car_type,),
            "Yamaha": (bike_type,),
        }
        brands = {}
        for name, types in brand_types.items():
            brand, _ = Brands.objects.get_or_create(name=name)
            brand.vehicle_types.add(*types)
            brands[name] = brand

        customer_names = [
            "Ana Souza",
            "Bruno Lima",
            "Camila Rocha",
            "Daniel Alves",
            "Eduarda Martins",
            "Felipe Santos",
            "Gabriela Costa",
            "Henrique Gomes",
            "Isabela Ribeiro",
            "João Pereira",
            "Larissa Mendes",
            "Marcos Oliveira",
            "Natália Freitas",
            "Paulo Nunes",
            "Renata Carvalho",
        ]
        customers = []
        for index, name in enumerate(customer_names, start=1):
            customer, _ = Customer.objects.get_or_create(
                email=f"cliente{index:02d}@example.com",
                defaults={
                    "name": name,
                    "phone": f"(12) 90000-{index:04d}",
                    "document": f"DEMO-{index:04d}",
                    "notes": "Cliente fictício criado pelo comando seed_demo.",
                },
            )
            customers.append(customer)

        catalog = [
            (car_type, "Honda", "Civic", 2022, 85000, 97900),
            (car_type, "Honda", "City", 2023, 78000, 89900),
            (car_type, "Toyota", "Corolla", 2022, 98000, 112900),
            (car_type, "Toyota", "Yaris", 2021, 69000, 79900),
            (car_type, "Volkswagen", "Polo", 2023, 72000, 82900),
            (car_type, "Volkswagen", "T-Cross", 2022, 96000, 109900),
            (car_type, "Chevrolet", "Onix", 2023, 65000, 75900),
            (car_type, "Chevrolet", "Tracker", 2022, 91000, 104900),
            (car_type, "Fiat", "Argo", 2022, 59000, 69900),
            (car_type, "Fiat", "Pulse", 2023, 83000, 95900),
            (bike_type, "Honda", "CG 160", 2023, 14500, 17900),
            (bike_type, "Honda", "CB 500F", 2022, 33000, 38900),
            (bike_type, "Yamaha", "Fazer 250", 2023, 19500, 23900),
            (bike_type, "Yamaha", "MT-03", 2022, 27000, 31900),
            (bike_type, "Honda", "XRE 300", 2021, 22000, 26900),
        ]

        vehicles = []
        for index in range(30):
            vehicle_type, brand_name, model, year, purchase, asking = catalog[index % len(catalog)]
            cycle = index // len(catalog)
            plate = f"DEM{index:04d}"
            vehicle, _ = Vehicle.objects.get_or_create(
                license_plate=plate,
                defaults={
                    "vehicle_type": vehicle_type,
                    "brand": brands[brand_name],
                    "model": f"{model}{' Plus' if cycle else ''}",
                    "model_year": year,
                    "factory_year": year - (1 if index % 4 == 0 else 0),
                    "color": ("Preto", "Branco", "Prata", "Azul")[index % 4],
                    "purchase_price": Decimal(purchase + cycle * 1200),
                    "asking_price": Decimal(asking + cycle * 1500),
                    "mileage": 8000 + index * 1750,
                    "entry_date": today - timedelta(days=30 + index * 7),
                    "description": "Veículo fictício para estudo do sistema e dos relatórios.",
                },
            )
            vehicles.append(vehicle)

        confirmed_created = 0
        for index, vehicle in enumerate(vehicles[:18]):
            sale_date = vehicle.entry_date + timedelta(days=15 + (index % 6) * 5)
            sale_date = min(sale_date, today)
            sale, created = Sale.objects.get_or_create(
                vehicle=vehicle,
                status=Sale.Status.CONFIRMED,
                defaults={
                    "customer": customers[index % len(customers)],
                    "sale_date": sale_date,
                    "final_price": vehicle.asking_price - Decimal((index % 4) * 500),
                    "payment_method": (
                        Sale.PaymentMethod.PIX,
                        Sale.PaymentMethod.FINANCING,
                        Sale.PaymentMethod.CASH,
                        Sale.PaymentMethod.CARD,
                    )[index % 4],
                    "notes": "Venda fictícia gerada para análise de dados.",
                },
            )
            confirmed_created += int(created)

        canceled_vehicle = vehicles[20]
        if not canceled_vehicle.sales.filter(status=Sale.Status.CANCELED).exists():
            Sale.objects.create(
                vehicle=canceled_vehicle,
                customer=customers[-1],
                sale_date=min(canceled_vehicle.entry_date + timedelta(days=10), today),
                final_price=canceled_vehicle.asking_price,
                payment_method=Sale.PaymentMethod.FINANCING,
                status=Sale.Status.CANCELED,
                notes="Venda fictícia cancelada para demonstrar a regra de estoque.",
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Base de demonstração pronta: "
                f"{len(vehicles)} veículos, {len(customers)} clientes e "
                f"{confirmed_created} novas vendas confirmadas."
            )
        )
