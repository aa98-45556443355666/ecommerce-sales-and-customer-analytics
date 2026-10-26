"""Validate the core CSV exports used by the Power BI data model."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_EXPORT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi_output"
)

TABLE_SPECS = {
    "dim_customer.csv": {
        "required_columns": {"customer_key"},
        "primary_key": "customer_key",
    },
    "dim_product.csv": {
        "required_columns": {"product_key"},
        "primary_key": "product_key",
    },
    "dim_date.csv": {
        "required_columns": {"date_key"},
        "primary_key": "date_key",
    },
    "dim_region.csv": {
        "required_columns": {"region_key"},
        "primary_key": "region_key",
    },
    "powerbi_sales_fact.csv": {
        "required_columns": {
            "customer_key",
            "product_key",
            "order_date_key",
            "region_key",
        },
        "primary_key": None,
    },
}

FOREIGN_KEYS = [
    (
        "powerbi_sales_fact.csv",
        "customer_key",
        "dim_customer.csv",
        "customer_key",
    ),
    (
        "powerbi_sales_fact.csv",
        "product_key",
        "dim_product.csv",
        "product_key",
    ),
    (
        "powerbi_sales_fact.csv",
        "order_date_key",
        "dim_date.csv",
        "date_key",
    ),
    (
        "powerbi_sales_fact.csv",
        "region_key",
        "dim_region.csv",
        "region_key",
    ),
]

def validate_powerbi_exports(export_dir: str | Path) -> list[str]:
    """
    Validate required CSV files, columns, primary keys and foreign keys.

    Returns a list of validation errors. An empty list means that
    all configured checks passed.
    """
    export_path = Path(export_dir)
    errors: list[str] = []
    dataframes: dict[str, pd.DataFrame] = {}
    parsed_keys: dict[tuple[str, str], pd.Series] = {}

    if not export_path.exists():
        return [f"Export directory does not exist: {export_path}"]

    if not export_path.is_dir():
        return [f"Export path is not a directory: {export_path}"]


    for filename, spec in TABLE_SPECS.items():
        file_path = export_path / filename

        if not file_path.is_file():
            errors.append(f"Missing required file: {filename}")
            continue

        try:
            df = pd.read_csv(file_path)
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            errors.append(f"Cannot read {filename}: {exc}")
            continue

        dataframes[filename] = df

        if df.empty:
            errors.append(f"{filename} contains no data rows.")

        missing_columns = spec["required_columns"] - set(df.columns)

        if missing_columns:
            errors.append(
                f"{filename} is missing required columns: "
                f"{', '.join(sorted(missing_columns))}"
            )

    
        primary_key = spec["primary_key"]

        if primary_key and primary_key in df.columns:
            key_values = pd.to_numeric(
                df[primary_key],
                errors="coerce",
            )

            parsed_keys[(filename, primary_key)] = key_values

            invalid_count = int(key_values.isna().sum())

            if invalid_count:
                errors.append(
                    f"{filename}.{primary_key} contains "
                    f"{invalid_count} null or non-numeric key value(s)."
                )

            duplicate_count = int(
                key_values.dropna().duplicated().sum()
            )

            if duplicate_count:
                errors.append(
                    f"{filename}.{primary_key} contains "
                    f"{duplicate_count} duplicate key value(s)."
                )


        for fact_column in (
            spec["required_columns"] if not primary_key
            else set()
        ):
            if fact_column not in df.columns:
                continue

            key_values = pd.to_numeric(
                df[fact_column],
                errors="coerce",
            )

            parsed_keys[(filename, fact_column)] = key_values

            invalid_count = int(key_values.isna().sum())

            if invalid_count:
                errors.append(
                    f"{filename}.{fact_column} contains "
                    f"{invalid_count} null or non-numeric key value(s)."
                )


    for (
        fact_file,
        fact_column,
        dimension_file,
        dimension_column,
    ) in FOREIGN_KEYS:

        fact_key = parsed_keys.get((fact_file, fact_column))
        dimension_key = parsed_keys.get(
            (dimension_file, dimension_column)
        )

        if fact_key is None or dimension_key is None:
            continue

        valid_fact_keys = fact_key.dropna()
        valid_dimension_keys = dimension_key.dropna()

        unmatched = ~valid_fact_keys.isin(valid_dimension_keys)
        unmatched_count = int(unmatched.sum())

        if unmatched_count:
            errors.append(
                f"{fact_file}.{fact_column} has "
                f"{unmatched_count} value(s) missing from "
                f"{dimension_file}.{dimension_column}."
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Power BI CSV exports."
    )

    parser.add_argument(
        "--path",
        default=str(DEFAULT_EXPORT_DIR),
        help="Directory containing the exported CSV files.",
    )

    args = parser.parse_args()

    print(f"Validating Power BI exports in: {args.path}")

    errors = validate_powerbi_exports(args.path)

    if errors:
        print("\nVALIDATION FAILED")

        for index, error in enumerate(errors, start=1):
            print(f"{index}. {error}")

        return 1

    print("\nVALIDATION PASSED")
    print("Required files, columns and key relationships look valid.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
