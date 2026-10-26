from pathlib import Path

import pandas as pd

from src.analytics.validate_powerbi_exports import (
    validate_powerbi_exports,
)


def create_valid_exports(directory: Path) -> None:
    """Create a minimal but consistent set of Power BI CSVs."""
    directory.mkdir(parents=True, exist_ok=True)

    datasets = {
        "dim_customer.csv": {
            "customer_key": [1, 2],
        },
        "dim_product.csv": {
            "product_key": [101, 102],
        },
        "dim_date.csv": {
            "date_key": [20260101, 20260102],
        },
        "dim_region.csv": {
            "region_key": [10, 20],
        },
        "powerbi_sales_fact.csv": {
            "customer_key": [1, 2],
            "product_key": [101, 102],
            "order_date_key": [20260101, 20260102],
            "region_key": [10, 20],
        },
    }

    for filename, data in datasets.items():
        pd.DataFrame(data).to_csv(
            directory / filename,
            index=False,
        )


def test_valid_exports_pass(tmp_path):
    create_valid_exports(tmp_path)

    errors = validate_powerbi_exports(tmp_path)

    assert errors == []


def test_missing_file_is_reported(tmp_path):
    create_valid_exports(tmp_path)
    (tmp_path / "dim_region.csv").unlink()

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "Missing required file: dim_region.csv" in error
        for error in errors
    )


def test_missing_column_is_reported(tmp_path):
    create_valid_exports(tmp_path)

    pd.DataFrame(
        {"wrong_key": [1, 2]}
    ).to_csv(
        tmp_path / "dim_customer.csv",
        index=False,
    )

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "dim_customer.csv is missing required columns" in error
        for error in errors
    )


def test_duplicate_dimension_key_is_reported(tmp_path):
    create_valid_exports(tmp_path)

    pd.DataFrame(
        {"customer_key": [1, 1]}
    ).to_csv(
        tmp_path / "dim_customer.csv",
        index=False,
    )

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "duplicate key value" in error
        for error in errors
    )


def test_orphan_foreign_key_is_reported(tmp_path):
    create_valid_exports(tmp_path)

    pd.DataFrame(
        {
            "customer_key": [1],
            "product_key": [999],
            "order_date_key": [20260101],
            "region_key": [10],
        }
    ).to_csv(
        tmp_path / "powerbi_sales_fact.csv",
        index=False,
    )

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "powerbi_sales_fact.csv.product_key" in error
        and "missing from dim_product.csv.product_key" in error
        for error in errors
    )


def test_null_fact_key_is_reported(tmp_path):
    create_valid_exports(tmp_path)

    pd.DataFrame(
        {
            "customer_key": [None],
            "product_key": [101],
            "order_date_key": [20260101],
            "region_key": [10],
        }
    ).to_csv(
        tmp_path / "powerbi_sales_fact.csv",
        index=False,
    )

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "powerbi_sales_fact.csv.customer_key contains" in error
        for error in errors
    )


def test_missing_export_directory_is_reported(tmp_path):
    missing_directory = tmp_path / "not_created"

    errors = validate_powerbi_exports(missing_directory)

    assert any(
        "Export directory does not exist" in error
        for error in errors
    )
