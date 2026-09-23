"""Exemplo didático de análise dos dados exportados pelo AutoGestor.

Antes de executar:
    python manage.py export_analytics

Depois:
    python analytics/analise_vendas.py
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
EXPORT_DIR = BASE_DIR / "data_exports"


def main():
    vehicles = pd.read_csv(EXPORT_DIR / "vehicles.csv")
    sales = pd.read_csv(EXPORT_DIR / "sales.csv")

    # Manter somente vendas confirmadas para não somar cancelamento
    confirmed = sales[sales["status"] == "confirmed"].copy()

    # O merge é tipo um JOIN do SQL: une a venda aos dados do veículo.
    analysis = confirmed.merge(
        vehicles[["id", "brand", "model", "purchase_price"]],
        left_on="vehicle_id",
        right_on="id",
        suffixes=("", "_vehicle"),
    )
    analysis["sale_date"] = pd.to_datetime(analysis["sale_date"])
    analysis["month"] = analysis["sale_date"].dt.to_period("M").astype(str)
    analysis["gross_profit"] = analysis["final_price"] - analysis["purchase_price"]

    by_month = (
        analysis.groupby("month", as_index=False)
        .agg(revenue=("final_price", "sum"), gross_profit=("gross_profit", "sum"), sales=("id", "count"))
        .sort_values("month")
    )
    by_brand = (
        analysis.groupby("brand", as_index=False)
        .agg(revenue=("final_price", "sum"), gross_profit=("gross_profit", "sum"), sales=("id", "count"))
        .sort_values("revenue", ascending=False)
    )

    by_month.to_csv(EXPORT_DIR / "analysis_by_month.csv", index=False, encoding="utf-8-sig")
    by_brand.to_csv(EXPORT_DIR / "analysis_by_brand.csv", index=False, encoding="utf-8-sig")

    print("\nRESUMO")
    print(f"Vendas confirmadas: {len(analysis)}")
    print(f"Faturamento: R$ {analysis['final_price'].sum():,.2f}")
    print(f"Lucro bruto: R$ {analysis['gross_profit'].sum():,.2f}")
    print(f"Ticket médio: R$ {analysis['final_price'].mean():,.2f}")
    print("\nPOR MARCA")
    print(by_brand.to_string(index=False))


if __name__ == "__main__":
    main()
