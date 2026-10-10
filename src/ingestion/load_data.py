from __future__ import annotations

import csv
import logging
import os
import sys
from pathlib import Path

import psycopg2
import yaml
from dotenv import load_dotenv


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# TABLE MAPPING
# CSV headers must match these columns in the same order.
# ---------------------------------------------------------

TABLES = [
    {
        "file": "customers.csv",
        "table": "staging.customers",
        "columns": [
            "customer_id",
            "first_name",
            "last_name",
            "email",
            "gender",
            "date_of_birth",
            "city",
            "state",
            "country",
            "signup_date",
        ],
    },
    {
        "file": "products.csv",
        "table": "staging.products",
        "columns": [
            "product_id",
            "product_name",
            "category",
            "subcategory",
            "brand",
            "price",
            "cost",
        ],
    },
    {
        "file": "orders.csv",
        "table": "staging.orders",
        "columns": [
            "order_id",
            "customer_id",
            "order_date",
            "order_status",
            "payment_method",
            "shipping_city",
            "shipping_state",
        ],
    },
    {
        "file": "order_items.csv",
        "table": "staging.order_items",
        "columns": [
            "item_id",
            "order_id",
            "product_id",
            "quantity",
            "unit_price",
            "discount",
        ],
    },
    {
        "file": "returns.csv",
        "table": "staging.returns",
        "columns": [
            "return_id",
            "order_id",
            "product_id",
            "return_date",
            "return_reason",
        ],
    },
]


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

def load_project_config() -> dict:
    """Load configuration from config/config.yaml."""

    config_path = ROOT_DIR / "config" / "config.yaml"

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError(
            "config/config.yaml must contain a YAML mapping."
        )

    data_config = config.get("data", {})

    raw_dir_value = data_config.get("raw_dir")

    if not raw_dir_value:
        raise ValueError(
            "Missing data.raw_dir in config/config.yaml. "
            "Set it to 'data/raw'."
        )

    raw_dir = Path(raw_dir_value)

    if not raw_dir.is_absolute():
        raw_dir = ROOT_DIR / raw_dir

    return {
        "raw_dir": raw_dir.resolve(),
    }


def get_database_config() -> dict:
    """Read database connection settings from environment."""

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


# ---------------------------------------------------------
# FILE VALIDATION
# ---------------------------------------------------------

def validate_csv_header(csv_path: Path, expected_columns: list[str]) -> None:
    """Check the CSV exists and its header matches the schema."""

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Required CSV file not found: {csv_path}"
        )

    if csv_path.stat().st_size == 0:
        raise ValueError(
            f"CSV file is empty: {csv_path}"
        )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.reader(file)
        actual_columns = next(reader, None)

    if actual_columns is None:
        raise ValueError(
            f"CSV file does not contain a header: {csv_path}"
        )

    if actual_columns != expected_columns:
        raise ValueError(
            f"CSV header mismatch in {csv_path.name}.\n"
            f"Expected: {expected_columns}\n"
            f"Actual:   {actual_columns}"
        )

    logger.info("Validated CSV header: %s", csv_path.name)


def validate_all_files(raw_dir: Path) -> list[dict]:
    """Validate all source files before touching the database."""

    validated_files = []

    for table_config in TABLES:
        csv_path = raw_dir / table_config["file"]

        validate_csv_header(
            csv_path,
            table_config["columns"],
        )

        validated_files.append(
            {
                **table_config,
                "path": csv_path,
            }
        )

    return validated_files


# ---------------------------------------------------------
# POSTGRESQL INGESTION
# ---------------------------------------------------------

def load_csv_files(files: list[dict], database_config: dict) -> dict[str, int]:
    """
    Load CSV files into staging tables using PostgreSQL COPY.

    All tables are refreshed in one transaction. If any load
    fails, the transaction is rolled back.
    """

    table_names = ", ".join(
        item["table"] for item in files
    )

    truncate_sql = f"TRUNCATE TABLE {table_names}"

    loaded_counts: dict[str, int] = {}
    connection = None

    try:
        logger.info("Connecting to PostgreSQL...")

        connection = psycopg2.connect(
            **database_config
        )

        with connection:
            with connection.cursor() as cursor:

                # Start with an empty staging layer.
                # This makes a successful rerun a full refresh.
                logger.info("Refreshing staging tables...")

                cursor.execute(truncate_sql)

                # Load each CSV using PostgreSQL COPY.
                for item in files:
                    table_name = item["table"]
                    columns = item["columns"]
                    csv_path = item["path"]

                    column_sql = ", ".join(columns)

                    copy_sql = (
                        f"COPY {table_name} ({column_sql}) "
                        "FROM STDIN "
                        "WITH (FORMAT CSV, HEADER TRUE, NULL '')"
                    )

                    logger.info(
                        "Loading %s into %s...",
                        csv_path.name,
                        table_name,
                    )

                    with csv_path.open(
                        "r",
                        encoding="utf-8-sig",
                        newline="",
                    ) as csv_file:
                        cursor.copy_expert(
                            copy_sql,
                            csv_file,
                        )

                    cursor.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    )

                    row_count = cursor.fetchone()[0]

                    loaded_counts[table_name] = row_count

                    logger.info(
                        "Loaded %s rows into %s",
                        f"{row_count:,}",
                        table_name,
                    )

        # The connection context commits on successful exit.
        logger.info("Database transaction committed.")

        return loaded_counts

    except Exception:
        logger.exception(
            "Ingestion failed. The database transaction "
            "was rolled back if it had started successfully. "
            "Check the error and staging table setup."
        )
        raise

    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    """Validate source files and load them into PostgreSQL."""

    try:
        project_config = load_project_config()

        raw_dir = project_config["raw_dir"]

        logger.info("Project root: %s", ROOT_DIR)
        logger.info("Raw data directory: %s", raw_dir)

        # Validate every file before starting the DB transaction.
        validated_files = validate_all_files(raw_dir)

        database_config = get_database_config()

        # Confirm all staging tables exist before truncating.
        # COPY itself will also fail safely if a table is missing.
        counts = load_csv_files(
            validated_files,
            database_config,
        )

        print("\n" + "=" * 55)
        print("INGESTION COMPLETED SUCCESSFULLY")
        print("=" * 55)

        for table_name, row_count in counts.items():
            print(f"{table_name:<28} {row_count:>12,} rows")

        print("=" * 55)

        return 0

    except Exception as exc:
        logger.error("Pipeline stopped: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
