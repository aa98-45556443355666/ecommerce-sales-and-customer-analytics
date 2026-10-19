from __future__ import annotations

import csv
import hashlib
import logging
import os
import sys

from pathlib import Path

import psycopg2
import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_DIR / ".env")

CONTROL_SQL = (
    ROOT_DIR
    / "sql"
    / "control"
    / "create_etl_control.sql"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


TABLES = [
    {
        "file": "customers.csv",
        "table": "staging.customers",
        "columns": [
            "customer_id", "first_name", "last_name",
            "email", "gender", "date_of_birth",
            "city", "state", "country", "signup_date",
        ],
    },
    {
        "file": "products.csv",
        "table": "staging.products",
        "columns": [
            "product_id", "product_name", "category",
            "subcategory", "brand", "price", "cost",
        ],
    },
    {
        "file": "orders.csv",
        "table": "staging.orders",
        "columns": [
            "order_id", "customer_id", "order_date",
            "order_status", "payment_method",
            "shipping_city", "shipping_state",
        ],
    },
    {
        "file": "order_items.csv",
        "table": "staging.order_items",
        "columns": [
            "item_id", "order_id", "product_id",
            "quantity", "unit_price", "discount",
        ],
    },
    {
        "file": "returns.csv",
        "table": "staging.returns",
        "columns": [
            "return_id", "order_id", "product_id",
            "return_date", "return_reason",
        ],
    },
]


def load_project_config() -> dict:
    config_path = ROOT_DIR / "config" / "config.yaml"

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    raw_dir_value = config.get("data", {}).get("raw_dir")

    if not raw_dir_value:
        raise ValueError(
            "Missing data.raw_dir in config/config.yaml"
        )

    raw_dir = Path(raw_dir_value)

    if not raw_dir.is_absolute():
        raw_dir = ROOT_DIR / raw_dir

    return {"raw_dir": raw_dir.resolve()}


def get_database_config() -> dict:
    password = os.getenv("POSTGRES_PASSWORD")

    if not password:
        raise ValueError(
            "POSTGRES_PASSWORD missing from environment/.env"
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


def calculate_sha256(file_path: Path) -> str:
    """Calculate the file fingerprint without loading it all into memory."""

    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def validate_csv_header(file_path: Path, expected_columns: list[str]) -> None:
    if not file_path.is_file():
        raise FileNotFoundError(
            f"Required CSV not found: {file_path}"
        )

    if file_path.stat().st_size == 0:
        raise ValueError(
            f"CSV file is empty: {file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        actual_columns = next(csv.reader(file), None)

    if actual_columns != expected_columns:
        raise ValueError(
            f"Invalid header in {file_path.name}\n"
            f"Expected: {expected_columns}\n"
            f"Actual:   {actual_columns}"
        )


def validate_source_files(raw_dir: Path) -> list[dict]:
    """Validate all files before changing any staging table."""

    validated = []

    for table_config in TABLES:
        file_path = raw_dir / table_config["file"]

        validate_csv_header(
            file_path,
            table_config["columns"],
        )

        validated.append(
            {
                **table_config,
                "path": file_path,
            }
        )

        logger.info(
            "Validated %s",
            table_config["file"],
        )

    return validated


def load_changed_files(files: list[dict], database_config: dict) -> dict:
    """
    Reload only changed CSV files.

    An unchanged file is skipped only when both its fingerprint
    and the recorded PostgreSQL staging row count still match.

    All staging updates and file-state changes are transactional.
    """

    if not CONTROL_SQL.is_file():
        raise FileNotFoundError(
            f"ETL control SQL not found: {CONTROL_SQL}"
        )

    connection = None

    summary = {
        "loaded": {},
        "skipped": {},
    }

    try:
        connection = psycopg2.connect(
            **database_config
        )
        connection.autocommit = False

        with connection.cursor() as cursor:

            # Create the control table if it does not exist.
            cursor.execute(
                CONTROL_SQL.read_text(
                    encoding="utf-8"
                )
            )

            for item in files:
                file_path = item["path"]
                file_name = item["file"]
                table_name = item["table"]
                columns = item["columns"]

                file_hash = calculate_sha256(
                    file_path
                )
                file_size = file_path.stat().st_size

                cursor.execute(
                    """
                    SELECT
                        content_sha256,
                        file_size_bytes,
                        rows_loaded
                    FROM etl_control.source_file_state
                    WHERE file_name = %s
                    """,
                    (file_name,),
                )

                previous_state = cursor.fetchone()

                # Read the current staging count to detect manual
                # truncation/corruption even when the CSV is unchanged.
                cursor.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                )

                current_count = int(
                    cursor.fetchone()[0]
                )

                if previous_state is not None:
                    old_hash = previous_state[0].strip()
                    old_size = previous_state[1]
                    old_count = previous_state[2]

                    unchanged = (
                        old_hash == file_hash
                        and old_size == file_size
                        and old_count == current_count
                    )

                    if unchanged:
                        summary["skipped"][table_name] = (
                            current_count
                        )

                        logger.info(
                            "SKIPPED unchanged file: %s",
                            file_name,
                        )

                        continue

                logger.info(
                    "Loading changed file: %s",
                    file_name,
                )

                # Only this file's staging table is refreshed.
                cursor.execute(
                    f"TRUNCATE TABLE {table_name}"
                )

                column_sql = ", ".join(columns)

                copy_sql = (
                    f"COPY {table_name} ({column_sql}) "
                    "FROM STDIN "
                    "WITH (FORMAT CSV, HEADER TRUE, NULL '')"
                )

                with file_path.open(
                    "r",
                    encoding="utf-8-sig",
                    newline="",
                ) as file:
                    cursor.copy_expert(
                        copy_sql,
                        file,
                    )

                cursor.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                )

                loaded_count = int(
                    cursor.fetchone()[0]
                )

                cursor.execute(
                    """
                    INSERT INTO etl_control.source_file_state (
                        file_name,
                        content_sha256,
                        file_size_bytes,
                        rows_loaded,
                        loaded_at
                    )
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)

                    ON CONFLICT (file_name)
                    DO UPDATE SET
                        content_sha256 = EXCLUDED.content_sha256,
                        file_size_bytes = EXCLUDED.file_size_bytes,
                        rows_loaded = EXCLUDED.rows_loaded,
                        loaded_at = CURRENT_TIMESTAMP
                    """,
                    (
                        file_name,
                        file_hash,
                        file_size,
                        loaded_count,
                    ),
                )

                summary["loaded"][table_name] = loaded_count

                logger.info(
                    "Loaded %s rows into %s",
                    f"{loaded_count:,}",
                    table_name,
                )

        connection.commit()

        logger.info(
            "Source-file state and staging updates committed."
        )

        return summary

    except Exception:
        if connection is not None:
            connection.rollback()

        logger.exception(
            "Incremental ingestion failed; transaction rolled back."
        )

        raise

    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    try:
        config = load_project_config()
        raw_dir = config["raw_dir"]

        logger.info(
            "Raw data directory: %s",
            raw_dir,
        )

        files = validate_source_files(raw_dir)

        summary = load_changed_files(
            files,
            get_database_config(),
        )

        print("\n" + "=" * 62)
        print("INCREMENTAL INGESTION REPORT")
        print("=" * 62)

        print("\nReloaded files:")

        for table_name, count in summary["loaded"].items():
            print(
                f"{table_name:<27} {count:>12,} rows"
            )

        print("\nSkipped unchanged files:")

        for table_name, count in summary["skipped"].items():
            print(
                f"{table_name:<27} {count:>12,} rows"
            )

        print("=" * 62)
        print("RESULT: SUCCESS")
        print("=" * 62)

        return 0

    except Exception as exc:
        logger.error("Pipeline stopped: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
