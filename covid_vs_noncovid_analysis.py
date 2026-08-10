"""COVID vs. Non-COVID year classification analysis.

Cleaned from a Jupyter Notebook export for use as a standalone Python script.

The script trains three classification approaches against the supplied dataset:
1. Random Forest
2. Logistic Regression
3. K-Nearest Neighbors (KNN)

Each approach is used to predict:
- ``COVID Year``
- ``Region``

Usage
-----
Place the CSV in a local ``data`` directory and run:

    python covid_vs_noncovid_analysis.py

Or provide a different CSV path:

    python covid_vs_noncovid_analysis.py --data path/to/dataset.csv

Notes
-----
- No personal/local desktop path is stored in this file.
- Classification is evaluated with accuracy, F1 score, classification reports,
  and confusion matrices rather than mean squared error.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler


DEFAULT_DATA_PATH = Path("data") / "COVID vs NonCOVID factors - April 24th, 2023.csv"
RANDOM_STATE = 42
TEST_SIZE = 0.20


# -----------------------------------------------------------------------------
# Data loading and validation
# -----------------------------------------------------------------------------

def load_data(csv_path: Path) -> pd.DataFrame:
    """Load the analysis dataset and verify its required columns."""
    dataframe = pd.read_csv(csv_path)

    required_columns = {"Country", "Region", "COVID Year", "Happiness score"}
    missing_columns = required_columns.difference(dataframe.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset is missing required column(s): {missing}")

    return dataframe


def print_dataset_overview(dataframe: pd.DataFrame) -> None:
    """Reproduce the notebook's basic exploratory checks."""
    print("\n" + "=" * 80)
    print("DATASET OVERVIEW")
    print("=" * 80)
    print(f"Rows: {len(dataframe):,}")
    print(f"Columns: {len(dataframe.columns):,}")
    print("\nRegions:")
    for region in dataframe["Region"].dropna().unique():
        print(f"  - {region}")

    print("\nFirst five rows (Country and Region removed):")
    print(dataframe.drop(columns=["Country", "Region"]).head())


# -----------------------------------------------------------------------------
# Shared evaluation helpers
# -----------------------------------------------------------------------------

def evaluate_classifier(
    model_name: str,
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    *,
    target_names: list[str] | None = None,
) -> None:
    """Print classification metrics for a fitted model."""
    print("\n" + "-" * 80)
    print(model_name)
    print("-" * 80)
    print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")

    unique_labels = np.unique(np.concatenate([np.asarray(y_true), np.asarray(y_pred)]))
    average = "binary" if len(unique_labels) == 2 else "weighted"
    print(f"F1 score ({average}): {f1_score(y_true, y_pred, average=average):.4f}")

    report_kwargs: dict[str, object] = {"zero_division": 0}
    if target_names is not None:
        report_kwargs["labels"] = np.arange(len(target_names))
        report_kwargs["target_names"] = target_names

    print("\nClassification report:")
    print(classification_report(y_true, y_pred, **report_kwargs))


def print_confusion_table(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    *,
    labels: list[str] | None = None,
    index_name: str = "Actual",
    column_name: str = "Predicted",
) -> None:
    """Print a labeled confusion matrix as a pandas table."""
    if labels is None:
        matrix = confusion_matrix(y_true, y_pred)
        labels = [str(label) for label in sorted(np.unique(np.concatenate([y_true, y_pred])))]
    else:
        encoded_labels = np.arange(len(labels))
        matrix = confusion_matrix(y_true, y_pred, labels=encoded_labels)

    table = pd.DataFrame(matrix, index=labels, columns=labels)
    table.index.name = index_name
    table.columns.name = column_name
    print("\nConfusion matrix:")
    print(table)


# -----------------------------------------------------------------------------
# Target preparation
# -----------------------------------------------------------------------------

def prepare_covid_year_data(
    dataframe: pd.DataFrame,
    *,
    drop_happiness_score: bool,
) -> tuple[pd.DataFrame, pd.Series]:
    """Create features and target for predicting COVID Year."""
    drop_columns = ["Country", "Region", "COVID Year"]
    if drop_happiness_score:
        drop_columns.append("Happiness score")

    X = dataframe.drop(columns=drop_columns)
    y = dataframe["COVID Year"]
    return X, y


def prepare_region_data(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray, LabelEncoder]:
    """Create features and an encoded target for predicting Region."""
    X = dataframe.drop(columns=["Country", "Region", "COVID Year", "Happiness score"])

    encoder = LabelEncoder()
    y = encoder.fit_transform(dataframe["Region"])
    return X, y, encoder


# -----------------------------------------------------------------------------
# Random Forest models
# -----------------------------------------------------------------------------

def run_random_forest_models(dataframe: pd.DataFrame) -> None:
    """Train Random Forest models for COVID Year and Region."""
    print("\n" + "=" * 80)
    print("RANDOM FOREST MODELS")
    print("=" * 80)

    # Part 1: Predict COVID Year.
    # The original notebook intentionally removed Happiness score here.
    X, y = prepare_covid_year_data(dataframe, drop_happiness_score=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    covid_model = RandomForestClassifier(
        n_estimators=100,
        random_state=RANDOM_STATE,
    )
    covid_model.fit(X_train, y_train)
    covid_predictions = covid_model.predict(X_test)

    evaluate_classifier("Random Forest — Predict COVID Year", y_test, covid_predictions)
    print_confusion_table(y_test, covid_predictions)

    # Part 2: Predict Region.
    X_region, y_region, encoder = prepare_region_data(dataframe)
    X_train, X_test, y_train, y_test = train_test_split(
        X_region,
        y_region,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_region,
    )

    region_model = RandomForestClassifier(
        n_estimators=15,
        criterion="entropy",
        random_state=RANDOM_STATE,
    )
    region_model.fit(X_train, y_train)
    region_predictions = region_model.predict(X_test)

    region_names = encoder.classes_.tolist()
    evaluate_classifier(
        "Random Forest — Predict Region",
        y_test,
        region_predictions,
        target_names=region_names,
    )
    print_confusion_table(
        y_test,
        region_predictions,
        labels=region_names,
        index_name="Actual Region",
        column_name="Predicted Region",
    )


# -----------------------------------------------------------------------------
# Logistic Regression models
# -----------------------------------------------------------------------------

def run_logistic_regression_models(dataframe: pd.DataFrame) -> None:
    """Train Logistic Regression models for COVID Year and Region."""
    print("\n" + "=" * 80)
    print("LOGISTIC REGRESSION MODELS")
    print("=" * 80)

    # Part 1: Predict COVID Year.
    # Happiness score is retained here to match the original notebook.
    X, y = prepare_covid_year_data(dataframe, drop_happiness_score=False)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=0,
        stratify=y,
    )

    covid_model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(solver="liblinear", max_iter=1_000)),
        ]
    )
    covid_model.fit(X_train, y_train)
    covid_predictions = covid_model.predict(X_test)

    evaluate_classifier("Logistic Regression — Predict COVID Year", y_test, covid_predictions)
    print_confusion_table(y_test, covid_predictions)

    # Part 2: Predict Region.
    X_region, y_region, encoder = prepare_region_data(dataframe)
    X_train, X_test, y_train, y_test = train_test_split(
        X_region,
        y_region,
        test_size=TEST_SIZE,
        random_state=0,
        stratify=y_region,
    )

    region_model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    solver="liblinear",
                    max_iter=1_000,
                ),
            ),
        ]
    )
    region_model.fit(X_train, y_train)
    region_predictions = region_model.predict(X_test)

    region_names = encoder.classes_.tolist()
    evaluate_classifier(
        "Logistic Regression — Predict Region",
        y_test,
        region_predictions,
        target_names=region_names,
    )
    print_confusion_table(
        y_test,
        region_predictions,
        labels=region_names,
        index_name="Actual Region",
        column_name="Predicted Region",
    )


# -----------------------------------------------------------------------------
# K-Nearest Neighbors models
# -----------------------------------------------------------------------------

def run_knn_models(dataframe: pd.DataFrame) -> None:
    """Train KNN models for COVID Year and Region."""
    print("\n" + "=" * 80)
    print("K-NEAREST NEIGHBORS MODELS")
    print("=" * 80)

    # Part 1: Predict COVID Year.
    X, y = prepare_covid_year_data(dataframe, drop_happiness_score=False)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=0,
        stratify=y,
    )

    suggested_k = max(1, round(np.sqrt(len(y_test))))
    print(f"\nSquare-root heuristic for K based on test size: {suggested_k}")
    print("Using k=7 to preserve the original notebook setting.")

    covid_model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                KNeighborsClassifier(
                    n_neighbors=7,
                    p=2,
                    metric="euclidean",
                ),
            ),
        ]
    )
    covid_model.fit(X_train, y_train)
    covid_predictions = covid_model.predict(X_test)

    evaluate_classifier("KNN — Predict COVID Year", y_test, covid_predictions)
    print_confusion_table(y_test, covid_predictions)

    # Part 2: Predict Region.
    X_region, y_region, encoder = prepare_region_data(dataframe)
    X_train, X_test, y_train, y_test = train_test_split(
        X_region,
        y_region,
        test_size=TEST_SIZE,
        random_state=0,
        stratify=y_region,
    )

    region_model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                KNeighborsClassifier(
                    n_neighbors=7,
                    p=2,
                    metric="euclidean",
                ),
            ),
        ]
    )
    region_model.fit(X_train, y_train)
    region_predictions = region_model.predict(X_test)

    region_names = encoder.classes_.tolist()
    evaluate_classifier(
        "KNN — Predict Region",
        y_test,
        region_predictions,
        target_names=region_names,
    )
    print_confusion_table(
        y_test,
        region_predictions,
        labels=region_names,
        index_name="Actual Region",
        column_name="Predicted Region",
    )


# -----------------------------------------------------------------------------
# Command-line entry point
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run COVID vs. Non-COVID year classification models."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"Path to the input CSV (default: {DEFAULT_DATA_PATH})",
    )
    return parser.parse_args()


def main() -> None:
    """Run the complete analysis."""
    args = parse_args()

    if not args.data.exists():
        raise FileNotFoundError(
            f"Could not find dataset: {args.data}\n"
            "Place the CSV in the data/ directory or pass --data PATH_TO_CSV."
        )

    covid_data = load_data(args.data)
    print_dataset_overview(covid_data)
    run_random_forest_models(covid_data)
    run_logistic_regression_models(covid_data)
    run_knn_models(covid_data)


if __name__ == "__main__":
    main()
