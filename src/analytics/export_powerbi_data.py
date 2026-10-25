from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_DIR / ".env")

OUTPUT_DIR = (
    ROOT_DIR
    / "data"
    / "processed"
    / "powerbi_output"
)


# Table/view identifiers are fixed and defined in this repository.
EXPORT_OBJECTS = [
    # Star-schema warehouse tables: for an interactive model.
    ("warehouse", "dim_customer"),
    ("warehouse", "dim_product"),
    ("warehouse", "dim_date"),
    ("warehouse", "dim_region"),
    ("warehouse", "fact_sales"),

    # Ready-to-use analytical reporting views.
    ("analytics", "vw_executive_kpis"),
    ("analytics", "vw_monthly_sales"),
    ("analytics", "vw_category_performance"),
    ("analytics", "vw_product_performance"),
    ("analytics", "vw_customer_performance"),
    ("analytics", "vw_customer_segments"),
    ("analytics", "vw_regional_performance"),
    ("analytics", "vw_return_reasons"),
    ("analytics", "vw_payment_method_performance"),
    ("analytics", "vw_order_status_performance"),
    ("analytics", "vw_weekday_performance"),
    ("analytics", "vw_powerbi_sales_fact"),
    ("analytics", "vw_customer_segment_membership"),
    ("analytics", "vw_return_detail")
]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


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


def export_object(cursor, connection, schema_name: str, object_name: str, output_path: Path) -> int:
    """Export one table or view using PostgreSQL COPY"""

    qualified_name = sql.Identifier(
        schema_name,
        object_name,
    )

    count_query = sql.SQL(
        "SELECT COUNT(*) FROM {}"
    ).format(qualified_name)

    cursor.execute(count_query)

    row_count = int(
        cursor.fetchone()[0]
    )

    copy_query = sql.SQL(
        """
        COPY (
            SELECT * FROM {}
        )
        TO STDOUT
        WITH (FORMAT CSV, HEADER TRUE, NULL '')
        """
    ).format(qualified_name)

    temporary_path = output_path.with_name(
        output_path.name + ".tmp"
    )

    try:
        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as output_file:

            cursor.copy_expert(
                copy_query.as_string(connection),
                output_file,
            )

        temporary_path.replace(output_path)

    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise

    logger.info(
        "Exported %s.%s: %s rows",
        schema_name,
        object_name,
        f"{row_count:,}",
    )

    return row_count


def main() -> int:
    connection = None

    try:
        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            "Connecting to PostgreSQL..."
        )

        connection = psycopg2.connect(
            **get_database_config()
        )

        exported_objects = 0
        total_rows = 0

        with connection.cursor() as cursor:

            for schema_name, object_name in EXPORT_OBJECTS:

                # Use a simple filename for Power BI/Excel.
                filename = (
                    object_name.removeprefix("vw_")
                    + ".csv"
                )

                output_path = OUTPUT_DIR / filename

                row_count = export_object(
                    cursor=cursor,
                    connection=connection,
                    schema_name=schema_name,
                    object_name=object_name,
                    output_path=output_path,
                )

                exported_objects += 1
                total_rows += row_count

        print("\n" + "=" * 65)
        print("POWER BI DATA EXPORT COMPLETED")
        print("=" * 65)
        print(f"Datasets exported: {exported_objects}")
        print(f"Total rows exported: {total_rows:,}")
        print(f"Output directory: {OUTPUT_DIR}")
        print("=" * 65)

        return 0

    except Exception:
        logger.exception(
            "Power BI export failed. "
            "Check database connectivity and view creation."
        )
        return 1

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
