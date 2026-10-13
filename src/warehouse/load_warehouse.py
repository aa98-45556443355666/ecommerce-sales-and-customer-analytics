from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


SQL_FILES = [
    ROOT_DIR / "sql" / "warehouse"
    / "create_warehouse_schema.sql",

    ROOT_DIR / "sql" / "warehouse"
    / "load_dimensions.sql",

    ROOT_DIR / "sql" / "warehouse"
    / "load_fact_sales.sql",
]


CLEAN_TABLES = {
    "customers": "clean.customers",
    "products": "clean.products",
    "orders": "clean.orders",
    "order_items": "clean.order_items",
}

WAREHOUSE_TABLES = {
    "dim_customer": "warehouse.dim_customer",
    "dim_product": "warehouse.dim_product",
    "dim_date": "warehouse.dim_date",
    "dim_region": "warehouse.dim_region",
    "fact_sales": "warehouse.fact_sales",
}


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

def get_database_config() -> dict:
    password = os.getenv("POSTGRES_PASSWORD")

    if not password:
        raise ValueError(
            "POSTGRES_PASSWORD is missing. "
            "Check the .env file in the project root."
        )

    try:
        port = int(os.getenv("POSTGRES_PORT", "5432"))
    except ValueError as exc:
        raise ValueError(
            "POSTGRES_PORT must be a valid integer."
        ) from exc

    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": port,
        "dbname": os.getenv("POSTGRES_DB", "ecommerce_db"),
        "user": os.getenv("POSTGRES_USER", "ecommerce"),
        "password": password,
        "connect_timeout": 10,
    }

# --------------------------------------------------
# SQL FILE EXECUTION
# --------------------------------------------------


def execute_sql_file(cursor, sql_file: Path) -> None:
    """Execute a project-owned SQL script."""

    if not sql_file.is_file():
        raise FileNotFoundError(
            f"SQL file not found: {sql_file}"
        )

    sql_text = sql_file.read_text(
        encoding="utf-8"
    )

    if not sql_text.strip():
        raise ValueError(
            f"SQL file is empty: {sql_file}"
        )

    logger.info("Executing %s", sql_file.name)

    cursor.execute(sql_text)

    logger.info("Completed %s", sql_file.name)


# --------------------------------------------------
# SOURCE VALIDATION
# --------------------------------------------------

def validate_clean_tables(cursor) -> dict[str, int]:
    """Require the core cleaned tables to contain records."""

    counts = {}

    for name, table_name in CLEAN_TABLES.items():
        cursor.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        )

        count = int(cursor.fetchone()[0])
        counts[name] = count

        logger.info(
            "%s: %s rows",
            table_name,
            f"{count:,}",
        )

        if count == 0:
            raise ValueError(
                f"{table_name} is empty. "
                "Run the transformation pipeline first."
            )

    return counts


# --------------------------------------------------
# WAREHOUSE COUNTS
# --------------------------------------------------

def get_warehouse_counts(cursor) -> dict[str, int]:
    counts = {}

    for name, table_name in WAREHOUSE_TABLES.items():
        cursor.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        )

        counts[name] = int(cursor.fetchone()[0])

    return counts


# --------------------------------------------------
# DATA INTEGRITY
# --------------------------------------------------

def validate_fact_sales(cursor, clean_counts: dict) -> None:
    """Validate record counts and calculated financial fields."""

    cursor.execute(
        "SELECT COUNT(*) FROM warehouse.fact_sales"
    )

    fact_count = int(cursor.fetchone()[0])

    expected_count = clean_counts["order_items"]

    if fact_count != expected_count:
        raise RuntimeError(
            "Fact row count mismatch: "
            f"clean.order_items={expected_count:,}, "
            f"warehouse.fact_sales={fact_count:,}"
        )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM warehouse.fact_sales
        WHERE net_sales <> gross_sales - discount_amount
           OR profit <> net_sales - total_cost
        """
    )

    invalid_calculations = int(
        cursor.fetchone()[0]
    )

    if invalid_calculations != 0:
        raise RuntimeError(
            "Financial calculations failed for "
            f"{invalid_calculations:,} fact rows."
        )

    logger.info(
        "Fact count and financial checks passed."
    )


# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------

def run_warehouse_pipeline() -> dict[str, int]:
    connection = None

    try:
        logger.info("Connecting to PostgreSQL...")

        connection = psycopg2.connect(
            **get_database_config()
        )

        connection.autocommit = False

        with connection.cursor() as cursor:

            # First make sure clean source tables are ready.
            clean_counts = validate_clean_tables(
                cursor
            )

            # Create warehouse objects.
            execute_sql_file(
                cursor,
                SQL_FILES[0],
            )

            # Full-refresh dimensions and clear the old fact.
            execute_sql_file(
                cursor,
                SQL_FILES[1],
            )

            # Load the fact table using the populated dimensions.
            execute_sql_file(
                cursor,
                SQL_FILES[2],
            )

            # Validate before committing.
            validate_fact_sales(
                cursor,
                clean_counts,
            )

            warehouse_counts = get_warehouse_counts(
                cursor
            )

        connection.commit()

        logger.info(
            "Warehouse transaction committed successfully."
        )

        return warehouse_counts

    except Exception:
        if connection is not None:
            connection.rollback()

        logger.exception(
            "Warehouse pipeline failed. "
            "All changes in this transaction were rolled back."
        )

        raise

    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    try:
        counts = run_warehouse_pipeline()

        print("\n" + "=" * 60)
        print("STAR-SCHEMA DATA WAREHOUSE")
        print("=" * 60)

        for table_name, row_count in counts.items():
            print(
                f"{table_name:<20} {row_count:>12,} rows"
            )

        print("=" * 60)
        print("RESULT: SUCCESS")
        print("=" * 60)

        return 0

    except Exception as exc:
        logger.error("Pipeline stopped: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
