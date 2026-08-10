"""Housing Market EDA & Dynamic Pivot Analysis
============================================

Recreates the EDA, calculated fields, filtered quartiles, pivot tables, KPIs,
and charts from the original Excel assignment using Python.

Example
-------
python housing_market_analysis.py assignment2_housing_data.xlsx --output-dir outputs/housing
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RAW_SHEET = "RawData"
EXPECTED_COLUMNS = {
    "Record",
    "Sale_amount",
    "Sale_date",
    "Beds",
    "Baths",
    "Sqft_home",
    "Sqft_lot",
    "Type",
    "Build_year",
    "Town",
    "University",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run reproducible EDA and pivot-style housing analysis."
    )
    parser.add_argument("workbook", type=Path, help="Path to source .xlsx or .csv")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/housing_market"),
        help="Directory for generated outputs",
    )
    parser.add_argument(
        "--university",
        default="Virginia Tech",
        help="University used for filtered price-per-square-foot quartiles",
    )
    parser.add_argument(
        "--property-type",
        default="Multi Family",
        help="Property type used for filtered price-per-bed quartiles",
    )
    parser.add_argument(
        "--build-year",
        type=int,
        default=2014,
        help="Build year used for the filtered sale-price analysis",
    )
    parser.add_argument(
        "--min-beds",
        type=float,
        default=2,
        help="Minimum beds for the build-year filter (inclusive)",
    )
    return parser.parse_args()


def load_data(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, sheet_name=RAW_SHEET)

    missing = EXPECTED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    return df.copy()


def clean_and_engineer(df: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        "Sale_amount",
        "Beds",
        "Baths",
        "Sqft_home",
        "Sqft_lot",
        "Build_year",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["Sale_date"] = pd.to_datetime(df["Sale_date"], errors="coerce")

    # Division by zero is treated as missing rather than infinite.
    df["Sale_Amount_Per_Bed"] = np.where(
        df["Beds"] > 0, df["Sale_amount"] / df["Beds"], np.nan
    )
    df["Sale_Amount_Per_SQFT"] = np.where(
        df["Sqft_home"] > 0, df["Sale_amount"] / df["Sqft_home"], np.nan
    )

    df["Sale_Month"] = df["Sale_date"].dt.month_name().str[:3]
    df["Sale_Month_Number"] = df["Sale_date"].dt.month
    return df


def quartile_table(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return pd.Series(
            {"1st Quartile": np.nan, "Median": np.nan, "3rd Quartile": np.nan, "Maximum": np.nan}
        )
    return pd.Series(
        {
            "1st Quartile": clean.quantile(0.25),
            "Median": clean.median(),
            "3rd Quartile": clean.quantile(0.75),
            "Maximum": clean.max(),
        }
    )


def overall_summary(df: pd.DataFrame) -> pd.Series:
    sale = df["Sale_amount"].dropna()
    return pd.Series(
        {
            "Average": sale.mean(),
            "Standard Deviation (sample)": sale.std(ddof=1),
            "1st Quartile": sale.quantile(0.25),
            "Median": sale.median(),
            "3rd Quartile": sale.quantile(0.75),
            "Maximum": sale.max(),
        },
        name="Sale Amount",
    )


def filtered_analyses(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    university = quartile_table(
        df.loc[df["University"] == args.university, "Sale_Amount_Per_SQFT"]
    ).rename(f"{args.university}: Sale Amount per SQFT")

    property_type = quartile_table(
        df.loc[df["Type"] == args.property_type, "Sale_Amount_Per_Bed"]
    ).rename(f"{args.property_type}: Sale Amount per Bed")

    # The workbook's label says "at least 2" while its formula used Beds > 2.
    # This implementation follows the written requirement literally: >= min_beds.
    build_year = quartile_table(
        df.loc[
            (df["Build_year"] == args.build_year) & (df["Beds"] >= args.min_beds),
            "Sale_amount",
        ]
    ).rename(
        f"Built {args.build_year}, Beds >= {args.min_beds:g}: Sale Amount"
    )

    return pd.concat([university, property_type, build_year], axis=1)


def build_pivot_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    by_build_year = (
        df.groupby("Build_year", dropna=False)
        .agg(
            Max_Sale_Amount_Per_Bed=("Sale_Amount_Per_Bed", "max"),
            Max_Sale_Amount_Per_SQFT=("Sale_Amount_Per_SQFT", "max"),
            Max_Sale_Amount=("Sale_amount", "max"),
            Listings=("Record", "count"),
        )
        .reset_index()
        .sort_values("Build_year")
    )

    by_property_type = (
        df.groupby("Type", dropna=False)
        .agg(
            Average_Beds=("Beds", "mean"),
            Average_Baths=("Baths", "mean"),
            Average_Sale_Amount=("Sale_amount", "mean"),
            Listings=("Record", "count"),
        )
        .reset_index()
        .sort_values("Listings", ascending=False)
    )

    monthly = (
        df.dropna(subset=["Sale_Month_Number"])
        .groupby(["Sale_Month_Number", "Sale_Month"], as_index=False)
        .agg(
            Sum_Sale_Amount=("Sale_amount", "sum"),
            Sum_Sale_Amount_Per_Bed=("Sale_Amount_Per_Bed", "sum"),
            Sum_Sale_Amount_Per_SQFT=("Sale_Amount_Per_SQFT", "sum"),
            Transactions=("Record", "count"),
        )
        .sort_values("Sale_Month_Number")
    )

    by_university = (
        df.groupby("University", dropna=False)
        .agg(
            Listings=("Record", "count"),
            Average_Sale_Amount=("Sale_amount", "mean"),
            Median_Sale_Amount=("Sale_amount", "median"),
            Average_Price_Per_SQFT=("Sale_Amount_Per_SQFT", "mean"),
        )
        .reset_index()
        .sort_values("Listings", ascending=False)
    )

    return {
        "pivot_by_build_year": by_build_year,
        "pivot_by_property_type": by_property_type,
        "pivot_monthly": monthly,
        "pivot_by_university": by_university,
    }


def kpis(df: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {
            "Maximum Sale Amount": df["Sale_amount"].max(),
            "Maximum Sale Amount per SQFT": df["Sale_Amount_Per_SQFT"].max(),
            "Maximum Sale Amount per Bed": df["Sale_Amount_Per_Bed"].max(),
            "Median Sale Amount": df["Sale_amount"].median(),
            "Number of Transactions": df["Record"].count(),
        },
        name="Value",
    )


def save_charts(df: pd.DataFrame, pivots: dict[str, pd.DataFrame], output_dir: Path) -> None:
    monthly = pivots["pivot_monthly"]
    plt.figure(figsize=(9, 5))
    plt.plot(monthly["Sale_Month"], monthly["Sum_Sale_Amount"], marker="o")
    plt.title("Total Sale Amount by Month")
    plt.xlabel("Month")
    plt.ylabel("Total Sale Amount")
    plt.ticklabel_format(style="plain", axis="y")
    plt.tight_layout()
    plt.savefig(output_dir / "monthly_sale_amount.png", dpi=160)
    plt.close()

    property_type = pivots["pivot_by_property_type"].sort_values("Average_Sale_Amount")
    plt.figure(figsize=(9, 5))
    plt.barh(property_type["Type"].astype(str), property_type["Average_Sale_Amount"])
    plt.title("Average Sale Amount by Property Type")
    plt.xlabel("Average Sale Amount")
    plt.ylabel("Property Type")
    plt.ticklabel_format(style="plain", axis="x")
    plt.tight_layout()
    plt.savefig(output_dir / "average_sale_amount_by_property_type.png", dpi=160)
    plt.close()

    # Price-per-square-foot distribution gives an EDA view that the workbook's
    # static pivots do not expose directly.
    plt.figure(figsize=(9, 5))
    clean_ppsf = df["Sale_Amount_Per_SQFT"].replace([np.inf, -np.inf], np.nan).dropna()
    upper = clean_ppsf.quantile(0.99)
    plt.hist(clean_ppsf[clean_ppsf <= upper], bins=30)
    plt.title("Price per SQFT Distribution (through 99th percentile)")
    plt.xlabel("Sale Amount per SQFT")
    plt.ylabel("Transactions")
    plt.tight_layout()
    plt.savefig(output_dir / "price_per_sqft_distribution.png", dpi=160)
    plt.close()

    build_year = pivots["pivot_by_build_year"].dropna(subset=["Build_year"])
    plt.figure(figsize=(10, 5))
    plt.scatter(build_year["Build_year"], build_year["Max_Sale_Amount"])
    plt.title("Maximum Sale Amount by Build Year")
    plt.xlabel("Build Year")
    plt.ylabel("Maximum Sale Amount")
    plt.ticklabel_format(style="plain", axis="y")
    plt.tight_layout()
    plt.savefig(output_dir / "max_sale_amount_by_build_year.png", dpi=160)
    plt.close()


def write_report(
    df: pd.DataFrame,
    overall: pd.Series,
    filtered: pd.DataFrame,
    kpi_values: pd.Series,
    output_dir: Path,
) -> None:
    report = f"""# Housing Market EDA — Python Output

## Dataset

- Transactions: **{len(df):,}**
- Date range: **{df['Sale_date'].min().date()}** to **{df['Sale_date'].max().date()}**
- Universities represented: **{df['University'].nunique(dropna=True):,}**
- Property types represented: **{df['Type'].nunique(dropna=True):,}**

## Overall sale-amount statistics

{overall.round(2).to_frame().to_markdown()}

## Filtered quartile analyses

{filtered.round(2).to_markdown()}

## Dynamic KPIs

{kpi_values.round(2).to_frame().to_markdown()}

## Improvements over the workbook

- Calculated fields are generated programmatically rather than stored as formulas.
- Pivot-style tables automatically include every category/year present in new data.
- Filters are command-line parameters rather than hard-coded worksheet cells.
- Division-by-zero cases are handled as missing values instead of infinities.
- The build-year filter uses `Beds >= minimum` because the assignment wording says
  "at least" that many beds; the original Excel formula used a strict `>` test.
- All tables and plots can be regenerated by rerunning one command.
"""
    (output_dir / "analysis_summary.md").write_text(report, encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = clean_and_engineer(load_data(args.workbook))
    overall = overall_summary(df)
    filtered = filtered_analyses(df, args)
    pivot_tables = build_pivot_tables(df)
    kpi_values = kpis(df)

    df.to_csv(args.output_dir / "housing_cleaned_with_features.csv", index=False)
    overall.to_csv(args.output_dir / "overall_summary.csv", header=True)
    filtered.to_csv(args.output_dir / "filtered_quartile_analysis.csv")
    kpi_values.to_csv(args.output_dir / "kpis.csv", header=True)

    for filename, table in pivot_tables.items():
        table.to_csv(args.output_dir / f"{filename}.csv", index=False)

    save_charts(df, pivot_tables, args.output_dir)
    write_report(df, overall, filtered, kpi_values, args.output_dir)

    print(f"Processed {len(df):,} housing transactions")
    print(f"Outputs written to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
