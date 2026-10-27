from pathlib import Path

import pandas as pd

from src.analytics.validate_powerbi_exports import (
    validate_powerbi_exports,
)


def create_valid_exports(directory: Path) -> None:
    """Create consistent sample CSVs for all configured exports."""
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
        "customer_segment_membership.csv": {
            "customer_id": ["C1", "C2"],
            "customer_segment": [
                "Champions",
                "Regular Customers",
            ],
        },
        "return_detail.csv": {
            "return_id": ["R1", "R2"],
            "order_id": ["O1", "O2"],
            "customer_id": ["C1", "C2"],
            "customer_segment": [
                "Champions",
                "Regular Customers",
            ],
            "product_id": ["P101", "P102"],
            "product_name": ["Product A", "Product B"],
            "category": ["Electronics", "Books"],
            "return_date": ["2026-01-01", "2026-01-02"],
            "return_date_key": [20260101, 20260102],
            "return_year": [2026, 2026],
            "return_month_number": [1, 1],
            "return_year_month": ["2026-01", "2026-01"],
            "return_reason": ["Damaged", "Wrong item"],
            "shipping_city": ["Delhi", "Ambala"],
            "shipping_state": ["Delhi", "Haryana"],
            "return_records": [1, 1],
        },
    }

    for filename, data in datasets.items():
        pd.DataFrame(data).to_csv(
            directory / filename,
            index=False,
        )


def test_valid_exports_pass(tmp_path):
    create_valid_exports(tmp_path)

    assert validate_powerbi_exports(tmp_path) == []


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
        "dim_customer.csv is missing required columns"
        in error
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


def test_orphan_fact_foreign_key_is_reported(tmp_path):
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
        "powerbi_sales_fact.csv.customer_key contains"
        in error
        for error in errors
    )


def test_missing_export_directory_is_reported(tmp_path):
    errors = validate_powerbi_exports(
        tmp_path / "not_created"
    )

    assert any(
        "Export directory does not exist" in error
        for error in errors
    )


def test_duplicate_return_id_is_reported(tmp_path):
    create_valid_exports(tmp_path)

    returns_file = tmp_path / "return_detail.csv"
    returns = pd.read_csv(returns_file, dtype="string")
    returns["return_id"] = ["R1", "R1"]
    returns.to_csv(returns_file, index=False)

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "return_detail.csv.return_id contains"
        in error
        and "duplicate" in error
        for error in errors
    )


def test_unknown_return_customer_is_reported(tmp_path):
    create_valid_exports(tmp_path)

    returns_file = tmp_path / "return_detail.csv"
    returns = pd.read_csv(returns_file, dtype="string")
    returns.loc[0, "customer_id"] = "UNKNOWN_CUSTOMER"
    returns.to_csv(returns_file, index=False)

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "return_detail.csv.customer_id" in error
        and "customer_segment_membership.csv.customer_id" in error
        for error in errors
    )


def test_return_segment_mismatch_is_reported(tmp_path):
    create_valid_exports(tmp_path)

    returns_file = tmp_path / "return_detail.csv"
    returns = pd.read_csv(returns_file, dtype="string")
    returns.loc[0, "customer_segment"] = "At Risk"
    returns.to_csv(returns_file, index=False)

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "customer segment value(s)" in error
        for error in errors
    )


def test_invalid_return_records_value_is_reported(tmp_path):
    create_valid_exports(tmp_path)

    returns_file = tmp_path / "return_detail.csv"
    returns = pd.read_csv(returns_file, dtype="string")
    returns.loc[0, "return_records"] = "2"
    returns.to_csv(returns_file, index=False)

    errors = validate_powerbi_exports(tmp_path)

    assert any(
        "return_records must equal 1" in error
        for error in errors
    )
