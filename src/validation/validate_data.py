from __future__ import annotations

import logging
import os
import sys

from dataclasses import dataclass
from pathlib import Path

import psycopg2
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

# --------------------------------------------------
# DATA QUALITY CHECK DEFINITION
# --------------------------------------------------


@dataclass(frozen=True)
class QualityCheck:
    name: str
    sql: str
    expectation: str = "zero"
    severity: str = "FAIL"


CHECKS = [

    # ----------------------------------------------
    # 1. TABLE AVAILABILITY
    # ----------------------------------------------

    QualityCheck(
        name="Customers table is not empty",
        sql="SELECT COUNT(*) FROM staging.customers",
        expectation="positive",
    ),

    QualityCheck(
        name="Products table is not empty",
        sql="SELECT COUNT(*) FROM staging.products",
        expectation="positive",
    ),

    QualityCheck(
        name="Orders table is not empty",
        sql="SELECT COUNT(*) FROM staging.orders",
        expectation="positive",
    ),

    QualityCheck(
        name="Order items table is not empty",
        sql="SELECT COUNT(*) FROM staging.order_items",
        expectation="positive",
    ),

    QualityCheck(
        name="Returns table is not empty",
        sql="SELECT COUNT(*) FROM staging.returns",
        expectation="positive",
    ),

    # ----------------------------------------------
    # 2. CUSTOMERS
    # ----------------------------------------------

    QualityCheck(
        name="Duplicate customer IDs (intentional test data)",
        sql="""
            SELECT COUNT(*)
            FROM (
                SELECT customer_id
                FROM staging.customers
                GROUP BY customer_id
                HAVING COUNT(*) > 1
            ) AS duplicates
        """,
        severity="WARN",
    ),

    QualityCheck(
        name="Missing customer emails (intentional test data)",
        sql="""
            SELECT COUNT(*)
            FROM staging.customers
            WHERE email IS NULL
               OR BTRIM(email) = ''
        """,
        severity="WARN",
    ),

    QualityCheck(
        name="Missing required customer fields",
        sql="""
            SELECT COUNT(*)
            FROM staging.customers
            WHERE customer_id IS NULL
               OR first_name IS NULL
               OR BTRIM(first_name) = ''
               OR last_name IS NULL
               OR BTRIM(last_name) = ''
               OR date_of_birth IS NULL
               OR signup_date IS NULL
        """,
    ),

    # ----------------------------------------------
    # 3. PRODUCTS
    # ----------------------------------------------

    QualityCheck(
        name="Duplicate product IDs",
        sql="""
            SELECT COUNT(*)
            FROM (
                SELECT product_id
                FROM staging.products
                GROUP BY product_id
                HAVING COUNT(*) > 1
            ) AS duplicates
        """,
    ),

    QualityCheck(
        name="Missing product categories (intentional test data)",
        sql="""
            SELECT COUNT(*)
            FROM staging.products
            WHERE category IS NULL
               OR BTRIM(category) = ''
        """,
        severity="WARN",
    ),

    QualityCheck(
        name="Missing required product fields",
        sql="""
            SELECT COUNT(*)
            FROM staging.products
            WHERE product_id IS NULL
               OR product_name IS NULL
               OR BTRIM(product_name) = ''
               OR price IS NULL
               OR cost IS NULL
        """,
    ),

    QualityCheck(
        name="Invalid product prices or costs",
        sql="""
            SELECT COUNT(*)
            FROM staging.products
            WHERE price <= 0
               OR cost < 0
               OR price < cost
        """,
    ),

    # ----------------------------------------------
    # 4. ORDERS
    # ----------------------------------------------

    QualityCheck(
        name="Duplicate order IDs (intentional test data)",
        sql="""
            SELECT COUNT(*)
            FROM (
                SELECT order_id
                FROM staging.orders
                GROUP BY order_id
                HAVING COUNT(*) > 1
            ) AS duplicates
        """,
        severity="WARN",
    ),

    QualityCheck(
        name="Missing required order fields",
        sql="""
            SELECT COUNT(*)
            FROM staging.orders
            WHERE order_id IS NULL
               OR customer_id IS NULL
               OR order_date IS NULL
               OR order_status IS NULL
               OR payment_method IS NULL
        """,
    ),

    QualityCheck(
        name="Orders referencing unknown customers",
        sql="""
            SELECT COUNT(*)
            FROM staging.orders AS o
            WHERE NOT EXISTS (
                SELECT 1
                FROM staging.customers AS c
                WHERE c.customer_id = o.customer_id
            )
        """,
    ),

    QualityCheck(
        name="Invalid order statuses",
        sql="""
            SELECT COUNT(*)
            FROM staging.orders
            WHERE order_status IS NOT NULL
              AND order_status NOT IN (
                  'Delivered',
                  'Shipped',
                  'Processing',
                  'Cancelled'
              )
        """,
    ),

    QualityCheck(
        name="Invalid payment methods",
        sql="""
            SELECT COUNT(*)
            FROM staging.orders
            WHERE payment_method IS NOT NULL
              AND payment_method NOT IN (
                  'UPI',
                  'Credit Card',
                  'Debit Card',
                  'Net Banking',
                  'COD'
              )
        """,
    ),

    # ----------------------------------------------
    # 5. ORDER ITEMS
    # ----------------------------------------------

    QualityCheck(
        name="Duplicate order item IDs",
        sql="""
            SELECT COUNT(*)
            FROM (
                SELECT item_id
                FROM staging.order_items
                GROUP BY item_id
                HAVING COUNT(*) > 1
            ) AS duplicates
        """,
    ),

    QualityCheck(
        name="Missing required order item fields",
        sql="""
            SELECT COUNT(*)
            FROM staging.order_items
            WHERE item_id IS NULL
               OR order_id IS NULL
               OR product_id IS NULL
               OR quantity IS NULL
               OR unit_price IS NULL
               OR discount IS NULL
        """,
    ),

    QualityCheck(
        name="Order items referencing unknown orders",
        sql="""
            SELECT COUNT(*)
            FROM staging.order_items AS oi
            WHERE NOT EXISTS (
                SELECT 1
                FROM staging.orders AS o
                WHERE o.order_id = oi.order_id
            )
        """,
    ),

    QualityCheck(
        name="Order items referencing unknown products",
        sql="""
            SELECT COUNT(*)
            FROM staging.order_items AS oi
            WHERE NOT EXISTS (
                SELECT 1
                FROM staging.products AS p
                WHERE p.product_id = oi.product_id
            )
        """,
    ),

    QualityCheck(
        name="Non-positive order quantities",
        sql="""
            SELECT COUNT(*)
            FROM staging.order_items
            WHERE quantity <= 0
        """,
    ),

    QualityCheck(
        name="Invalid order item prices",
        sql="""
            SELECT COUNT(*)
            FROM staging.order_items
            WHERE unit_price <= 0
        """,
    ),

    QualityCheck(
        name="Discount outside the 0-to-1 range",
        sql="""
            SELECT COUNT(*)
            FROM staging.order_items
            WHERE discount < 0
               OR discount > 1
        """,
    ),

    QualityCheck(
        name="Order item prices differ from product prices",
        sql="""
            SELECT COUNT(*)
            FROM staging.order_items AS oi
            JOIN staging.products AS p
              ON p.product_id = oi.product_id
            WHERE oi.unit_price IS DISTINCT FROM p.price
        """,
    ),

    # ----------------------------------------------
    # 6. RETURNS
    # ----------------------------------------------

    QualityCheck(
        name="Duplicate return IDs",
        sql="""
            SELECT COUNT(*)
            FROM (
                SELECT return_id
                FROM staging.returns
                GROUP BY return_id
                HAVING COUNT(*) > 1
            ) AS duplicates
        """,
    ),

    QualityCheck(
        name="Missing required return fields",
        sql="""
            SELECT COUNT(*)
            FROM staging.returns
            WHERE return_id IS NULL
               OR order_id IS NULL
               OR product_id IS NULL
               OR return_date IS NULL
               OR return_reason IS NULL
               OR BTRIM(return_reason) = ''
        """,
    ),

    QualityCheck(
        name="Returns referencing unknown orders",
        sql="""
            SELECT COUNT(*)
            FROM staging.returns AS r
            WHERE NOT EXISTS (
                SELECT 1
                FROM staging.orders AS o
                WHERE o.order_id = r.order_id
            )
        """,
    ),

    QualityCheck(
        name="Returns referencing unknown products",
        sql="""
            SELECT COUNT(*)
            FROM staging.returns AS r
            WHERE NOT EXISTS (
                SELECT 1
                FROM staging.products AS p
                WHERE p.product_id = r.product_id
            )
        """,
    ),

    QualityCheck(
        name="Returns not matching an order item",
        sql="""
            SELECT COUNT(*)
            FROM staging.returns AS r
            WHERE NOT EXISTS (
                SELECT 1
                FROM staging.order_items AS oi
                WHERE oi.order_id = r.order_id
                  AND oi.product_id = r.product_id
            )
        """,
    ),
]

# --------------------------------------------------
# STATUS EVALUATION
# --------------------------------------------------


def evaluate_count(count: int, expectation: str = "zero", severity: str = "FAIL") -> str:
    """Determine the status of a data quality check."""

    if count < 0:
        raise ValueError("Count cannot be negative.")

    if expectation not in {"zero", "positive"}:
        raise ValueError(
            "Expectation must be 'zero' or 'positive'."
        )

    if severity not in {"FAIL", "WARN"}:
        raise ValueError(
            "Severity must be 'FAIL' or 'WARN'."
        )

    if expectation == "positive":
        return "PASS" if count > 0 else "FAIL"

    if count == 0:
        return "PASS"

    return "WARN" if severity == "WARN" else "FAIL"

# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------


def get_database_config() -> dict:
    """Read PostgreSQL credentials from .env"""

    password = os.getenv("POSTGRES_PASSWORD")

    if not password:
        raise ValueError(
            "POSTGRES_PASSWORD is missing. "
            "Check your project's .env file."
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
# RUN CHECKS
# --------------------------------------------------

def run_checks() -> list[dict]:
    """Execute all checks without modifying staging data."""

    results = []
    connection = None

    try:
        logger.info("Connecting to PostgreSQL...")

        connection = psycopg2.connect(
            **get_database_config()
        )

        with connection.cursor() as cursor:
            for check in CHECKS:
                cursor.execute(check.sql)

                row = cursor.fetchone()

                if row is None:
                    raise RuntimeError(
                        f"No result returned for: {check.name}"
                    )

                count = int(row[0])

                status = evaluate_count(
                    count=count,
                    expectation=check.expectation,
                    severity=check.severity,
                )

                results.append(
                    {
                        "name": check.name,
                        "count": count,
                        "expectation": check.expectation,
                        "status": status,
                    }
                )

                logger.info(
                    "[%s] %s | count=%s",
                    status,
                    check.name,
                    f"{count:,}",
                )

        return results

    finally:
        if connection is not None:
            connection.close()


# --------------------------------------------------
# REPORT
# --------------------------------------------------

def print_report(results: list[dict]) -> None:
    """Print a readable validation summary."""

    passed = sum(
        result["status"] == "PASS"
        for result in results
    )

    warnings = sum(
        result["status"] == "WARN"
        for result in results
    )

    failed = sum(
        result["status"] == "FAIL"
        for result in results
    )

    print("\n" + "=" * 72)
    print("DATA QUALITY VALIDATION REPORT")
    print("=" * 72)

    for result in results:
        count_label = (
            "rows"
            if result["expectation"] == "positive"
            else "issues"
        )

        print(
            f"[{result['status']:<4}] "
            f"{result['name']} "
            f"({count_label}: {result['count']:,})"
        )

    print("=" * 72)
    print(f"Total checks : {len(results)}")
    print(f"Passed       : {passed}")
    print(f"Warnings     : {warnings}")
    print(f"Failed       : {failed}")
    print("=" * 72)

    if failed:
        print("RESULT: FAILED — investigate critical issues.")
    elif warnings:
        print("RESULT: PASSED WITH WARNINGS.")
    else:
        print("RESULT: ALL CHECKS PASSED.")


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

def main() -> int:
    """Run validation and return an appropriate exit code."""

    try:
        results = run_checks()
        print_report(results)

        if any(
            result["status"] == "FAIL"
            for result in results
        ):
            return 1

        return 0

    except Exception:
        logger.exception(
            "Data quality validation could not complete."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
