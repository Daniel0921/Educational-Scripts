"""Race Results Data Cleaning & Analysis
=====================================

Recreates the data-cleaning, summary-statistics, COUNTIFS/AVERAGEIFS, and
pivot-style analysis from the original Excel assignment using Python.

The script intentionally reads the messy *raw* worksheet rather than the
already-cleaned Excel tabs so the transformation work is reproducible.

Public-output behavior
----------------------
Participant names and race numbers are excluded from exported files by
default. Use --include-identifiers only when working locally with data you are
permitted to publish.

Example
-------
python race_results_analysis.py assignment1_race_results.xlsx --output-dir outputs/race
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RAW_SHEET = "Imported Raw Data"
RAW_COLUMNS = [
    "Place",
    "Div_Tot",
    "Division",
    "Time",
    "Pace",
    "Name",
    "Age",
    "Sex",
    "Race_Number",
    "City_State",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean and analyze a paginated race-results worksheet."
    )
    parser.add_argument("workbook", type=Path, help="Path to the source .xlsx file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/race_results"),
        help="Directory for generated CSV, Markdown, and PNG files",
    )
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
        help="Include participant names and race numbers in cleaned_data.csv",
    )
    parser.add_argument(
        "--city",
        default="Dover",
        help="City used for the city-level count example (default: Dover)",
    )
    parser.add_argument(
        "--avg-city",
        default="Kittery",
        help="City used for the city-level average-time example (default: Kittery)",
    )
    parser.add_argument(
        "--division",
        default="M1014",
        help="Division used for the division-level count example",
    )
    parser.add_argument(
        "--avg-division",
        default="M0109",
        help="Division used for the division-level average-time example",
    )
    parser.add_argument(
        "--combo-division",
        default="F3039",
        help="Division used for the division/city average example",
    )
    parser.add_argument(
        "--combo-city",
        default="Newmarket",
        help="City used for the division/city average example",
    )
    return parser.parse_args()


def _is_number(value: Any) -> bool:
    """Return True when a raw 'Place' cell represents an actual finisher row."""
    try:
        float(value)
        return pd.notna(value)
    except (TypeError, ValueError):
        return False


def division_total_to_text(value: Any) -> str | None:
    """Repair Excel's auto-conversion of values such as '1/8' into dates.

    The original Div/Tot field contains values like 1/8 and 2/12. Excel stored
    many of those as dates. pandas therefore reads them as Timestamp objects.
    Month/day reconstructs the intended rank/total notation.
    """
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return f"{value.month}/{value.day}"
    # Python datetime values can appear depending on engine/version.
    if hasattr(value, "month") and hasattr(value, "day"):
        return f"{value.month}/{value.day}"
    return str(value).strip()


def time_to_decimal_minutes(value: Any) -> float:
    """Convert an Excel time-like cell to decimal minutes.

    The race export stored '16:00' as an Excel clock time (16:00:00). In the
    source context that means 16 minutes, 0 seconds—not 16 hours of race time.
    We therefore interpret hour:minute:second as minute:second:centisecond-ish
    race notation and return decimal minutes.
    """
    if pd.isna(value):
        return np.nan

    # Longer finishing times may be returned as datetime.timedelta because
    # Excel stores them beyond a 24-hour clock boundary. In this source,
    # 1 day 17:45 represents an intended race time of 41:45, so total Excel
    # hours map directly to intended race minutes.
    if isinstance(value, pd.Timedelta) or hasattr(value, "total_seconds"):
        try:
            return float(value.total_seconds()) / 3600.0
        except (TypeError, AttributeError):
            pass

    # pandas/openpyxl commonly returns shorter values as datetime.time.
    if hasattr(value, "hour") and hasattr(value, "minute"):
        hour = float(value.hour)
        minute = float(value.minute)
        second = float(getattr(value, "second", 0))
        return hour + minute / 60.0 + second / 3600.0

    text = str(value).strip()
    parts = text.split(":")
    if len(parts) >= 2:
        minutes = float(parts[0])
        seconds = float(parts[1])
        if len(parts) == 3:
            seconds += float(parts[2]) / 60.0
        return minutes + seconds / 60.0

    return float(value)


def format_minutes(value: float) -> str | None:
    if pd.isna(value):
        return None
    total_seconds = int(round(float(value) * 60))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def split_city_state(value: Any) -> tuple[str | None, str | None]:
    """Split 'West Henrietta NY' into ('West Henrietta', 'NY')."""
    if pd.isna(value) or not str(value).strip():
        return None, None
    text = str(value).strip()
    parts = text.rsplit(" ", 1)
    if len(parts) != 2:
        return text, None
    city, state = parts
    return city.strip() or None, state.strip() or None


def split_name(value: Any) -> tuple[str | None, str | None]:
    """Match the original Excel assignment's first-space name split."""
    if pd.isna(value) or not str(value).strip():
        return None, None
    parts = str(value).strip().split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else None
    return first, last


def load_and_clean(workbook: Path) -> pd.DataFrame:
    raw = pd.read_excel(workbook, sheet_name=RAW_SHEET, header=None)
    raw = raw.iloc[:, :10].copy()
    raw.columns = RAW_COLUMNS

    # Repeated page headers and separators are removed by keeping only rows
    # whose Place value is numeric.
    race = raw[raw["Place"].map(_is_number)].copy()

    race["Place"] = pd.to_numeric(race["Place"], errors="coerce").astype("Int64")
    race["Age"] = pd.to_numeric(race["Age"], errors="coerce")
    race["Race_Number"] = pd.to_numeric(race["Race_Number"], errors="coerce").astype("Int64")

    race["Div_Tot"] = race["Div_Tot"].map(division_total_to_text)
    race["Finish_Time_Min"] = race["Time"].map(time_to_decimal_minutes)
    race["Pace_Min_Per_Mile"] = race["Pace"].map(time_to_decimal_minutes)
    race["Finish_Time"] = race["Finish_Time_Min"].map(format_minutes)
    race["Pace"] = race["Pace_Min_Per_Mile"].map(format_minutes)

    name_parts = race["Name"].map(split_name)
    race["First_Name"] = [x[0] for x in name_parts]
    race["Last_Name"] = [x[1] for x in name_parts]

    location_parts = race["City_State"].map(split_city_state)
    race["City"] = [x[0] for x in location_parts]
    race["State"] = [x[1] for x in location_parts]

    # Replace the raw time objects with human-readable fields.
    race = race.drop(columns=["Time"])

    # Stable anonymized identifier is useful for public analysis without names.
    race.insert(0, "Runner_ID", [f"R{i:03d}" for i in range(1, len(race) + 1)])
    return race.reset_index(drop=True)


def descriptive_summary(df: pd.DataFrame) -> pd.DataFrame:
    def metrics(series: pd.Series) -> dict[str, float]:
        clean = pd.to_numeric(series, errors="coerce").dropna()
        return {
            "Average": clean.mean(),
            "Population SD": clean.std(ddof=0),
            "1st Quartile": clean.quantile(0.25),
            "Median": clean.median(),
            "3rd Quartile": clean.quantile(0.75),
            "Maximum": clean.max(),
        }

    age = metrics(df["Age"])
    finish = metrics(df["Finish_Time_Min"])
    return pd.DataFrame({"Age": age, "Finishing Time (min)": finish})


def query_examples(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Python equivalents of the workbook's COUNTIFS/AVERAGEIFS examples."""
    rows = [
        {
            "Metric": "Number of finishers from city",
            "Filter": f"City = {args.city}",
            "Value": int((df["City"] == args.city).sum()),
        },
        {
            "Metric": "Average finishing time from city",
            "Filter": f"City = {args.avg_city}",
            "Value": df.loc[df["City"] == args.avg_city, "Finish_Time_Min"].mean(),
        },
        {
            "Metric": "Number of finishers by division",
            "Filter": f"Division = {args.division}",
            "Value": int((df["Division"] == args.division).sum()),
        },
        {
            "Metric": "Average finishing time by division",
            "Filter": f"Division = {args.avg_division}",
            "Value": df.loc[
                df["Division"] == args.avg_division, "Finish_Time_Min"
            ].mean(),
        },
        {
            "Metric": "Average finishing time by division/city",
            "Filter": f"Division = {args.combo_division}; City = {args.combo_city}",
            "Value": df.loc[
                (df["Division"] == args.combo_division)
                & (df["City"] == args.combo_city),
                "Finish_Time_Min",
            ].mean(),
        },
    ]
    return pd.DataFrame(rows)


def build_grouped_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    state_summary = (
        df.groupby("State", dropna=False)
        .agg(
            Finishers=("Runner_ID", "count"),
            Average_Age=("Age", "mean"),
            Average_Finish_Time_Min=("Finish_Time_Min", "mean"),
        )
        .reset_index()
        .sort_values("Finishers", ascending=False)
    )

    division_summary = (
        df.groupby("Division", dropna=False)
        .agg(
            Finishers=("Runner_ID", "count"),
            Average_Age=("Age", "mean"),
            Average_Finish_Time_Min=("Finish_Time_Min", "mean"),
            Best_Finish_Time_Min=("Finish_Time_Min", "min"),
        )
        .reset_index()
        .sort_values(["Finishers", "Division"], ascending=[False, True])
    )

    sex_state_place = (
        df.groupby(["Sex", "State"], dropna=False)
        .agg(Average_Place=("Place", "mean"), Finishers=("Runner_ID", "count"))
        .reset_index()
    )

    return {
        "state_summary": state_summary,
        "division_summary": division_summary,
        "sex_state_place": sex_state_place,
    }


def save_charts(df: pd.DataFrame, output_dir: Path) -> None:
    # Chart 1: finishing-time distribution.
    plt.figure(figsize=(8, 5))
    plt.hist(df["Finish_Time_Min"].dropna(), bins=15)
    plt.title("Distribution of Finishing Times")
    plt.xlabel("Finishing Time (minutes)")
    plt.ylabel("Number of Finishers")
    plt.tight_layout()
    plt.savefig(output_dir / "finishing_time_distribution.png", dpi=160)
    plt.close()

    # Chart 2: average finish time by state.
    state = (
        df.dropna(subset=["State"])
        .groupby("State")["Finish_Time_Min"]
        .mean()
        .sort_values()
    )
    plt.figure(figsize=(8, 5))
    state.plot(kind="bar")
    plt.title("Average Finishing Time by State")
    plt.xlabel("State")
    plt.ylabel("Average Finishing Time (minutes)")
    plt.tight_layout()
    plt.savefig(output_dir / "average_finish_time_by_state.png", dpi=160)
    plt.close()

    # Chart 3: largest divisions by number of finishers.
    division = df["Division"].value_counts().head(12).sort_values()
    plt.figure(figsize=(8, 6))
    division.plot(kind="barh")
    plt.title("Largest Divisions by Number of Finishers")
    plt.xlabel("Finishers")
    plt.ylabel("Division")
    plt.tight_layout()
    plt.savefig(output_dir / "finishers_by_division.png", dpi=160)
    plt.close()


def write_report(
    df: pd.DataFrame,
    summary: pd.DataFrame,
    queries: pd.DataFrame,
    output_dir: Path,
) -> None:
    report = f"""# Race Results Analysis — Python Output

## Dataset

- Finishers identified from raw paginated worksheet: **{len(df):,}**
- Average age: **{df['Age'].mean():.2f}**
- Average finishing time: **{df['Finish_Time_Min'].mean():.2f} minutes**
- Fastest finishing time: **{df['Finish_Time_Min'].min():.2f} minutes**
- Slowest finishing time: **{df['Finish_Time_Min'].max():.2f} minutes**

## What the script replaces

The pipeline replaces the workbook's manual cleanup, text parsing, decimal-time
calculations, descriptive statistics, `COUNTIFS`, `AVERAGEIFS`, and pivot-style
grouping with reproducible Python transformations.

## Descriptive statistics

{summary.round(3).to_markdown()}

## Filtered query examples

{queries.round(3).to_markdown(index=False)}

## Privacy

The default public export removes participant names and race numbers. The
source workbook is read locally, but public-facing output uses anonymous
`Runner_ID` values.
"""
    (output_dir / "analysis_summary.md").write_text(report, encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = load_and_clean(args.workbook)
    summary = descriptive_summary(df)
    queries = query_examples(df, args)
    grouped = build_grouped_tables(df)

    public_columns = [
        "Runner_ID",
        "Place",
        "Div_Tot",
        "Division",
        "Finish_Time",
        "Finish_Time_Min",
        "Pace",
        "Pace_Min_Per_Mile",
        "Age",
        "Sex",
        "City_State",
        "City",
        "State",
    ]
    if args.include_identifiers:
        public_columns += ["Name", "First_Name", "Last_Name", "Race_Number"]

    df[public_columns].to_csv(args.output_dir / "cleaned_race_results.csv", index=False)
    summary.to_csv(args.output_dir / "descriptive_statistics.csv")
    queries.to_csv(args.output_dir / "filtered_query_examples.csv", index=False)

    for filename, table in grouped.items():
        table.to_csv(args.output_dir / f"{filename}.csv", index=False)

    save_charts(df, args.output_dir)
    write_report(df, summary, queries, args.output_dir)

    print(f"Processed {len(df):,} finishers")
    print(f"Outputs written to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
