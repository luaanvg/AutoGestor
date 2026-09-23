"""Exporta as tabelas para estudo com Pandas, CSV e Excel."""

from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from cars.models import Customer, Sale, Vehicle


class Command(BaseCommand):
    help = "Gera CSVs, planilha Excel e resumo analítico em data_exports/."

    def handle(self, *args, **options):
        output_dir = Path(settings.BASE_DIR) / "data_exports"
        output_dir.mkdir(exist_ok=True)

        vehicles = list(
            Vehicle.objects.select_related("brand", "vehicle_type").values(
                "id",
                "vehicle_type__name",
                "brand__name",
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
            )
        )
        customers = list(Customer.objects.values("id", "name", "phone", "email", "created_at"))
        sales = list(
            Sale.objects.select_related("vehicle", "customer").values(
                "id",
                "vehicle_id",
                "customer_id",
                "sale_date",
                "final_price",
                "payment_method",
                "status",
            )
        )

        vehicles_df = pd.DataFrame(vehicles).rename(
            columns={
                "vehicle_type__name": "vehicle_type",
                "brand__name": "brand",
            }
        )
        customers_df = pd.DataFrame(customers)
        sales_df = pd.DataFrame(sales)

        # Excel não armazena timezone na célula. A conversão remove apenas o
        # fuso do valor exportado, sem alterar o dado salvo pelo Django.
        if not customers_df.empty and "created_at" in customers_df:
            customers_df["created_at"] = pd.to_datetime(
                customers_df["created_at"], utc=True
            ).dt.tz_convert(None)

        if not sales_df.empty and not vehicles_df.empty:
            analysis_df = sales_df.merge(
                vehicles_df[["id", "brand", "model", "purchase_price"]],
                left_on="vehicle_id",
                right_on="id",
                suffixes=("", "_vehicle"),
            )
            analysis_df["gross_profit"] = (
                analysis_df["final_price"].astype(float)
                - analysis_df["purchase_price"].astype(float)
            )
            analysis_df["month"] = pd.to_datetime(analysis_df["sale_date"]).dt.to_period("M").astype(str)
        else:
            analysis_df = pd.DataFrame()

        vehicles_df.to_csv(output_dir / "vehicles.csv", index=False, encoding="utf-8-sig")
        customers_df.to_csv(output_dir / "customers.csv", index=False, encoding="utf-8-sig")
        sales_df.to_csv(output_dir / "sales.csv", index=False, encoding="utf-8-sig")
        analysis_df.to_csv(output_dir / "sales_analysis.csv", index=False, encoding="utf-8-sig")

        with pd.ExcelWriter(output_dir / "autogestor_analise.xlsx", engine="openpyxl") as writer:
            vehicles_df.to_excel(writer, sheet_name="Vehicles", index=False)
            customers_df.to_excel(writer, sheet_name="Customers", index=False)
            sales_df.to_excel(writer, sheet_name="Sales", index=False)
            analysis_df.to_excel(writer, sheet_name="SalesAnalysis", index=False)

        if not analysis_df.empty:
            confirmed = analysis_df[analysis_df["status"] == Sale.Status.CONFIRMED]
            summary = {
                "confirmed_sales": int(len(confirmed)),
                "revenue": float(confirmed["final_price"].sum()),
                "gross_profit": float(confirmed["gross_profit"].sum()),
                "average_ticket": float(confirmed["final_price"].mean()) if len(confirmed) else 0,
            }
        else:
            summary = {"confirmed_sales": 0, "revenue": 0, "gross_profit": 0, "average_ticket": 0}

        pd.DataFrame([summary]).to_csv(
            output_dir / "summary.csv", index=False, encoding="utf-8-sig"
        )
        self.stdout.write(self.style.SUCCESS(f"Arquivos gerados em {output_dir}"))
