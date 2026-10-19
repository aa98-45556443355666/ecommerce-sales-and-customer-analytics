from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


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
    / "incremental_load_dimensions.sql",

    ROOT_DIR / "sql" / "warehouse"
    / "incremental_load_fact_sales.sql",
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


def get_database_config() -> dict:
    password = os.getenv("POSTGRES_PASSWORD")

    if not password:
        raise ValueError(
            "POSTGRES_PASSWORD is missing from .env"
        )

    try:
        port = int(os.getenv("POSTGRES_PORT", "5432"))
    except ValueError as exc:
        raise ValueError(
            "POSTGRES_PORT must be an integer"
        ) from exc

    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": port,
        "dbname": os.getenv("POSTGRES_DB", "ecommerce_db"),
        "user": os.getenv("POSTGRES_USER", "ecommerce"),
        "password": password,
        "connect_timeout": 10,
    }


def get_count(cursor, table_name: str) -> int:
    cursor.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    )
    return int(cursor.fetchone()[0])


def execute_sql_file(cursor, sql_file: Path) -> None:
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

    logger.info(
        "Executing %s",
        sql_file.name,
    )

    cursor.execute(sql_text)


def run_incremental_warehouse() -> dict:
    connection = None

    try:
        connection = psycopg2.connect(
            **get_database_config()
        )
        connection.autocommit = False

        with connection.cursor() as cursor:

            clean_counts = {}

            for name, table_name in CLEAN_TABLES.items():
                count = get_count(
                    cursor,
                    table_name,
                )
                clean_counts[name] = count

                if count == 0:
                    raise ValueError(
                        f"{table_name} is empty. "
                        "Run incremental transformation first."
                    )

            # Create tables/indexes if not already present.
            execute_sql_file(
                cursor,
                SQL_FILES[0],
            )

            # Upsert dimensions without deleting existing rows.
            execute_sql_file(
                cursor,
                SQL_FILES[1],
            )

            # Insert/update fact rows.
            execute_sql_file(
                cursor,
                SQL_FILES[2],
            )

            warehouse_counts = {
                name: get_count(cursor, table_name)
                for name, table_name in WAREHOUSE_TABLES.items()
            }

            expected_fact_count = clean_counts["order_items"]
            actual_fact_count = warehouse_counts["fact_sales"]

            if actual_fact_count != expected_fact_count:
                raise RuntimeError(
                    "Fact count mismatch: "
                    f"clean.order_items={expected_fact_count:,}, "
                    f"warehouse.fact_sales={actual_fact_count:,}"
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
                    f"{invalid_calculations:,} fact rows "
                    "have invalid financial calculations."
                )

        connection.commit()

        logger.info(
            "Incremental warehouse transaction committed."
        )

        return warehouse_counts

    except Exception:
        if connection is not None:
            connection.rollback()

        logger.exception(
            "Incremental warehouse failed; transaction rolled back."
        )
        raise

    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    try:
        counts = run_incremental_warehouse()

        print("\n" + "=" * 65)
        print("INCREMENTAL WAREHOUSE REPORT")
        print("=" * 65)

        for name, count in counts.items():
            print(
                f"{name:<22} {count:>14,} rows"
            )

        print("=" * 65)
        print("RESULT: SUCCESS")
        print("=" * 65)

        return 0

    except Exception as exc:
        logger.error("Pipeline stopped: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
