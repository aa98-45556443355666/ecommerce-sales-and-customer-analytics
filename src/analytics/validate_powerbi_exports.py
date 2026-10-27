"""Validate CSV exports used by the Power BI data model."""

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
        "numeric_columns": {"customer_key"},
        "non_empty_columns": set(),
    },
    "dim_product.csv": {
        "required_columns": {"product_key"},
        "primary_key": "product_key",
        "numeric_columns": {"product_key"},
        "non_empty_columns": set(),
    },
    "dim_date.csv": {
        "required_columns": {"date_key"},
        "primary_key": "date_key",
        "numeric_columns": {"date_key"},
        "non_empty_columns": set(),
    },
    "dim_region.csv": {
        "required_columns": {"region_key"},
        "primary_key": "region_key",
        "numeric_columns": {"region_key"},
        "non_empty_columns": set(),
    },
    "powerbi_sales_fact.csv": {
        "required_columns": {
            "customer_key",
            "product_key",
            "order_date_key",
            "region_key",
        },
        "primary_key": None,
        "numeric_columns": {
            "customer_key",
            "product_key",
            "order_date_key",
            "region_key",
        },
        "non_empty_columns": set(),
    },
    "customer_segment_membership.csv": {
        "required_columns": {
            "customer_id",
            "customer_segment",
        },
        "primary_key": "customer_id",
        "numeric_columns": set(),
        "non_empty_columns": {"customer_segment"},
    },
    "return_detail.csv": {
        "required_columns": {
            "return_id",
            "order_id",
            "customer_id",
            "customer_segment",
            "product_id",
            "product_name",
            "category",
            "return_date",
            "return_date_key",
            "return_year",
            "return_month_number",
            "return_year_month",
            "return_reason",
            "shipping_city",
            "shipping_state",
            "return_records",
        },
        "primary_key": "return_id",
        "numeric_columns": {
            "return_date_key",
            "return_year",
            "return_month_number",
            "return_records",
        },
        "non_empty_columns": {
            "order_id",
            "customer_id",
            "product_id",
            "return_date",
            "return_reason",
            "customer_segment",
        },
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
    (
        "return_detail.csv",
        "return_date_key",
        "dim_date.csv",
        "date_key",
    ),
    (
        "return_detail.csv",
        "customer_id",
        "customer_segment_membership.csv",
        "customer_id",
    ),
]


def normalize_key(series: pd.Series) -> pd.Series:
    """Normalize CSV key values for comparison without losing leading zeros."""
    return series.astype("string").str.strip()


def validate_powerbi_exports(export_dir: str | Path) -> list[str]:
    """
    Validate required files, columns, keys and segment consistency.

    An empty list means all configured checks passed.
    """
    export_path = Path(export_dir)
    errors: list[str] = []
    dataframes: dict[str, pd.DataFrame] = {}

    if not export_path.exists():
        return [
            f"Export directory does not exist: {export_path}"
        ]

    if not export_path.is_dir():
        return [
            f"Export path is not a directory: {export_path}"
        ]

    for filename, spec in TABLE_SPECS.items():
        file_path = export_path / filename

        if not file_path.is_file():
            errors.append(f"Missing required file: {filename}")
            continue

        try:
            # Read identifiers as strings so leading zeros are preserved.
            df = pd.read_csv(file_path, dtype="string")
        except (
            OSError,
            UnicodeError,
            pd.errors.ParserError,
            pd.errors.EmptyDataError,
        ) as exc:
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
            keys = normalize_key(df[primary_key])
            missing_mask = keys.isna() | keys.eq("")

            if missing_mask.any():
                errors.append(
                    f"{filename}.{primary_key} contains "
                    f"{int(missing_mask.sum())} null or blank key(s)."
                )

            valid_keys = keys[~missing_mask]
            duplicate_count = int(
                valid_keys.duplicated().sum()
            )

            if duplicate_count:
                errors.append(
                    f"{filename}.{primary_key} contains "
                    f"{duplicate_count} duplicate key value(s)."
                )

        for column in spec["numeric_columns"]:
            if column not in df.columns:
                continue

            numbers = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            invalid_count = int(numbers.isna().sum())

            if invalid_count:
                errors.append(
                    f"{filename}.{column} contains "
                    f"{invalid_count} null or non-numeric value(s)."
                )
                continue

            fractional_count = int(
                (numbers % 1 != 0).sum()
            )

            if fractional_count:
                errors.append(
                    f"{filename}.{column} contains "
                    f"{fractional_count} non-integer value(s)."
                )

        for column in spec["non_empty_columns"]:
            if column not in df.columns:
                continue

            values = normalize_key(df[column])
            blank_count = int(
                (values.isna() | values.eq("")).sum()
            )

            if blank_count:
                errors.append(
                    f"{filename}.{column} contains "
                    f"{blank_count} null or blank value(s)."
                )

    for (
        fact_file,
        fact_column,
        dimension_file,
        dimension_column,
    ) in FOREIGN_KEYS:
        fact_df = dataframes.get(fact_file)
        dim_df = dataframes.get(dimension_file)

        if fact_df is None or dim_df is None:
            continue

        if (
            fact_column not in fact_df.columns
            or dimension_column not in dim_df.columns
        ):
            continue

        fact_keys = normalize_key(fact_df[fact_column])
        dimension_keys = normalize_key(
            dim_df[dimension_column]
        )

        valid_fact_keys = fact_keys[
            fact_keys.notna() & fact_keys.ne("")
        ]
        valid_dimension_keys = dimension_keys[
            dimension_keys.notna() & dimension_keys.ne("")
        ]

        unmatched_count = int(
            (~valid_fact_keys.isin(valid_dimension_keys)).sum()
        )

        if unmatched_count:
            errors.append(
                f"{fact_file}.{fact_column} has "
                f"{unmatched_count} value(s) missing from "
                f"{dimension_file}.{dimension_column}."
            )

    membership = dataframes.get(
        "customer_segment_membership.csv"
    )
    returns = dataframes.get("return_detail.csv")

    if membership is not None and returns is not None:
        required_membership = {
            "customer_id",
            "customer_segment",
        }
        required_returns = {
            "customer_id",
            "customer_segment",
        }

        if (
            required_membership.issubset(membership.columns)
            and required_returns.issubset(returns.columns)
        ):
            valid_membership = membership[
                ["customer_id", "customer_segment"]
            ].copy()

            valid_membership["customer_id"] = normalize_key(
                valid_membership["customer_id"]
            )
            valid_membership["customer_segment"] = normalize_key(
                valid_membership["customer_segment"]
            )

            segment_map = valid_membership.drop_duplicates(
                subset=["customer_id"]
            ).set_index("customer_id")["customer_segment"]

            return_customer_ids = normalize_key(
                returns["customer_id"]
            )
            expected_segments = return_customer_ids.map(
                segment_map
            )
            actual_segments = normalize_key(
                returns["customer_segment"]
            )

            comparable = (
                expected_segments.notna()
                & actual_segments.notna()
            )
            mismatch_count = int(
                (
                    comparable
                    & expected_segments.ne(actual_segments)
                ).sum()
            )

            if mismatch_count:
                errors.append(
                    "return_detail.csv has "
                    f"{mismatch_count} customer segment value(s) "
                    "that do not match customer_segment_membership.csv."
                )

    if returns is not None and "return_records" in returns.columns:
        return_counts = pd.to_numeric(
            returns["return_records"],
            errors="coerce",
        )

        invalid_return_counts = (
            return_counts.isna() | return_counts.ne(1)
        )
        invalid_count = int(invalid_return_counts.sum())

        if invalid_count:
            errors.append(
                "return_detail.csv.return_records must equal 1 "
                f"for every row; found {invalid_count} invalid row(s)."
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Power BI CSV exports."
    )
    parser.add_argument(
        "--path",
        default=str(DEFAULT_EXPORT_DIR),
        help="Directory containing exported CSV files.",
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
    print(
        "Required files, columns, keys and customer segments "
        "look valid."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
