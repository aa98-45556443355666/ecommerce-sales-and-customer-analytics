from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_DIR / ".env")

OUTPUT_FILE = (
    ROOT_DIR
    / "data"
    / "processed"
    / "spark_input"
    / "sales_data.csv"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


EXPORT_QUERY = """
    SELECT
        f.sales_key,
        f.order_id,
        f.item_id,

        c.customer_id,
        CONCAT_WS(
            ' ',
            c.first_name,
            c.last_name
        ) AS customer_name,

        p.product_id,
        p.product_name,
        p.category,
        p.subcategory,
        p.brand,

        TO_CHAR(
            d.full_date,
            'YYYY-MM-DD'
        ) AS order_date,

        d.year,
        d.month_number,
        d.month_name,
        d.day_of_week,
        d.day_name,

        CASE
            WHEN d.is_weekend THEN 'true'
            ELSE 'false'
        END AS is_weekend,

        r.state,
        r.city,

        f.order_status,
        f.payment_method,
        f.quantity,

        f.gross_sales,
        f.discount_amount,
        f.net_sales,
        f.total_cost,
        f.profit,

        CASE
            WHEN f.is_realized_sale THEN 'true'
            ELSE 'false'
        END AS is_realized_sale,

        CASE
            WHEN f.is_returned THEN 'true'
            ELSE 'false'
        END AS is_returned,

        f.return_reason

    FROM warehouse.fact_sales AS f

    INNER JOIN warehouse.dim_customer AS c
        ON c.customer_key = f.customer_key

    INNER JOIN warehouse.dim_product AS p
        ON p.product_key = f.product_key

    INNER JOIN warehouse.dim_date AS d
        ON d.date_key = f.order_date_key

    INNER JOIN warehouse.dim_region AS r
        ON r.region_key = f.region_key
"""


def get_database_config() -> dict:
    """Read database credentials from .env."""

    password = os.getenv("POSTGRES_PASSWORD")

    if not password:
        raise ValueError(
            "POSTGRES_PASSWORD is missing from .env"
        )

    try:
        port = int(
            os.getenv("POSTGRES_PORT", "5432")
        )
    except ValueError as exc:
        raise ValueError(
            "POSTGRES_PORT must be an integer."
        ) from exc

    return {
        "host": os.getenv(
            "POSTGRES_HOST",
            "localhost",
        ),
        "port": port,
        "dbname": os.getenv(
            "POSTGRES_DB",
            "ecommerce_db",
        ),
        "user": os.getenv(
            "POSTGRES_USER",
            "ecommerce",
        ),
        "password": password,
        "connect_timeout": 10,
    }


def export_spark_input() -> int:
    """Export the warehouse fact data for Spark processing."""

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Export to a temporary file first to avoid leaving a
    # partially written output if extraction fails.
    temporary_file = OUTPUT_FILE.with_name(
        OUTPUT_FILE.name + ".tmp"
    )

    connection = None

    try:
        logger.info(
            "Connecting to PostgreSQL..."
        )

        connection = psycopg2.connect(
            **get_database_config()
        )

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT COUNT(*) "
                "FROM warehouse.fact_sales"
            )

            source_count = int(
                cursor.fetchone()[0]
            )

            if source_count == 0:
                raise ValueError(
                    "warehouse.fact_sales is empty. "
                    "Build the warehouse before exporting."
                )

            copy_sql = (
                "COPY ("
                + EXPORT_QUERY
                + ") TO STDOUT "
                "WITH (FORMAT CSV, HEADER TRUE, NULL '')"
            )

            logger.info(
                "Exporting %s warehouse rows...",
                f"{source_count:,}",
            )

            with temporary_file.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as output:
                cursor.copy_expert(
                    copy_sql,
                    output,
                )

        connection.close()
        connection = None

        temporary_file.replace(OUTPUT_FILE)

        logger.info(
            "Spark input exported successfully: %s",
            OUTPUT_FILE,
        )

        logger.info(
            "Expected data rows: %s",
            f"{source_count:,}",
        )

        return 0

    except Exception:
        logger.exception(
            "Failed to export Spark input."
        )

        if temporary_file.exists():
            temporary_file.unlink()

        return 1

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    sys.exit(export_spark_input())
