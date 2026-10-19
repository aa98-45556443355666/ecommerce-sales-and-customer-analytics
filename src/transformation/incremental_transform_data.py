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
    ROOT_DIR / "sql" / "transformation"
    / "create_clean_schema.sql",

    ROOT_DIR / "sql" / "transformation"
    / "incremental_transform.sql",
]


STAGING_TABLES = {
    "customers": "staging.customers",
    "products": "staging.products",
    "orders": "staging.orders",
    "order_items": "staging.order_items",
    "returns": "staging.returns",
}


CLEAN_TABLES = {
    "customers": "clean.customers",
    "products": "clean.products",
    "orders": "clean.orders",
    "order_items": "clean.order_items",
    "returns": "clean.returns",
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

    logger.info("Executing %s", sql_file.name)
    cursor.execute(sql_text)


def get_count(cursor, table_name: str) -> int:
    cursor.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    )
    return int(cursor.fetchone()[0])


def run_incremental_transformation() -> dict:
    connection = None

    try:
        connection = psycopg2.connect(
            **get_database_config()
        )
        connection.autocommit = False

        with connection.cursor() as cursor:

            # Fail early if staging is not ready.
            staging_counts = {}

            for name, table_name in STAGING_TABLES.items():
                count = get_count(
                    cursor,
                    table_name,
                )
                staging_counts[name] = count

                if count == 0:
                    raise ValueError(
                        f"{table_name} is empty. "
                        "Run ingestion before transformation."
                    )

            # Create schema/tables if not present.
            execute_sql_file(
                cursor,
                SQL_FILES[0],
            )

            # Idempotent upserts. No clean-table TRUNCATE.
            execute_sql_file(
                cursor,
                SQL_FILES[1],
            )

            clean_counts = {
                name: get_count(cursor, table_name)
                for name, table_name in CLEAN_TABLES.items()
            }

        connection.commit()

        logger.info(
            "Incremental transformation committed."
        )

        return {
            "staging": staging_counts,
            "clean": clean_counts,
        }

    except Exception:
        if connection is not None:
            connection.rollback()

        logger.exception(
            "Incremental transformation failed; "
            "transaction rolled back."
        )
        raise

    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    try:
        results = run_incremental_transformation()

        print("\n" + "=" * 65)
        print("INCREMENTAL TRANSFORMATION REPORT")
        print("=" * 65)

        print(
            f"{'Table':<18}"
            f"{'Staging Rows':>17}"
            f"{'Clean Rows':>17}"
        )

        print("-" * 65)

        for name in CLEAN_TABLES:
            print(
                f"{name:<18}"
                f"{results['staging'][name]:>17,}"
                f"{results['clean'][name]:>17,}"
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
