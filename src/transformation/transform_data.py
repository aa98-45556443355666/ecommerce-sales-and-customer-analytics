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
    ROOT_DIR / "sql" / "transformation"
    / "create_clean_schema.sql",

    ROOT_DIR / "sql" / "transformation"
    / "transform_staging_to_clean.sql",
]

TABLE_MAP = {
    "customers": ("staging.customers", "clean.customers"),
    "products": ("staging.products", "clean.products"),
    "orders": ("staging.orders", "clean.orders"),
    "order_items": (
        "staging.order_items",
        "clean.order_items",
    ),
    "returns": ("staging.returns", "clean.returns"),
}


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

def get_database_config() -> dict:
    """Read PostgreSQL credentials from .env"""

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
    """Execute a complete SQL script."""

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

    logger.info("Executing SQL file: %s", sql_file.name)

    cursor.execute(sql_text)

    logger.info("Finished SQL file: %s", sql_file.name)


def get_row_count(cursor, table_name: str) -> int:
    """Return the count for a fixed project table."""

    cursor.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    )

    result = cursor.fetchone()

    if result is None:
        raise RuntimeError(
            f"Could not retrieve count for {table_name}"
        )

    return int(result[0])


def get_table_counts(cursor, table_position: int) -> dict[str, int]:
    """Return counts from staging or clean tables."""

    counts = {}

    for name, table_names in TABLE_MAP.items():
        table_name = table_names[table_position]

        counts[name] = get_row_count(
            cursor,
            table_name,
        )

    return counts


# --------------------------------------------------
# TRANSFORMATION PIPELINE
# --------------------------------------------------

def run_transformation() -> tuple[dict, dict]:
    """
    Create the clean schema and transform staging data.

    Everything runs inside one database transaction.
    If a SQL statement fails, changes are rolled back.
    """

    connection = None

    try:
        logger.info("Connecting to PostgreSQL...")

        connection = psycopg2.connect(
            **get_database_config()
        )

        connection.autocommit = False

        with connection.cursor() as cursor:

            staging_counts = get_table_counts(
                cursor,
                table_position=0,
            )

            empty_tables = [
                table_name
                for table_name, count in staging_counts.items()
                if count == 0
            ]

            if empty_tables:
                raise ValueError(
                    "Source staging tables are empty: "
                    + ", ".join(empty_tables)
                    + ". Run the ingestion pipeline first."
                )

            logger.info(
                "All staging tables contain data."
            )

            # Create clean schema and tables.
            execute_sql_file(
                cursor,
                SQL_FILES[0],
            )

            # Refresh and populate the clean layer.
            execute_sql_file(
                cursor,
                SQL_FILES[1],
            )

            # Retrieve results before committing.
            clean_counts = get_table_counts(
                cursor,
                table_position=1,
            )

        connection.commit()

        logger.info(
            "Transformation transaction committed."
        )

        return staging_counts, clean_counts

    except Exception:
        if connection is not None:
            connection.rollback()

        logger.exception(
            "Transformation failed. "
            "Database changes were rolled back."
        )

        raise

    finally:
        if connection is not None:
            connection.close()


def print_report(staging_counts: dict[str, int], clean_counts: dict[str, int]) -> None:
    """Display staging and clean row counts."""

    print("\n" + "=" * 75)
    print("DATA CLEANING & TRANSFORMATION REPORT")
    print("=" * 75)

    print(
        f"{'Table':<18}"
        f"{'Staging Rows':>15}"
        f"{'Clean Rows':>15}"
        f"{'Removed':>12}"
    )

    print("-" * 75)

    for table_name in TABLE_MAP:
        source_count = staging_counts[table_name]
        clean_count = clean_counts[table_name]

        removed_count = source_count - clean_count

        print(
            f"{table_name:<18}"
            f"{source_count:>15,}"
            f"{clean_count:>15,}"
            f"{removed_count:>12,}"
        )

    print("=" * 75)
    print("RESULT: TRANSFORMATION COMPLETED SUCCESSFULLY")
    print("=" * 75)


def main() -> int:
    try:
        staging_counts, clean_counts = run_transformation()

        print_report(
            staging_counts,
            clean_counts,
        )

        return 0

    except Exception as exc:
        logger.error(
            "Pipeline stopped: %s",
            exc,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
