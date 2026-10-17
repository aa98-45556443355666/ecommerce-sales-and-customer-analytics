from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DecimalType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)
from pyspark.sql.window import Window


ROOT_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT_DIR
    / "data"
    / "processed"
    / "spark_input"
    / "sales_data.csv"
)

OUTPUT_DIR = (
    ROOT_DIR
    / "data"
    / "processed"
    / "spark_output"
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# CSV SCHEMA
# --------------------------------------------------

SALES_SCHEMA = StructType(
    [
        StructField("sales_key", LongType(), True),
        StructField("order_id", LongType(), True),
        StructField("item_id", LongType(), True),

        StructField("customer_id", LongType(), True),
        StructField("customer_name", StringType(), True),

        StructField("product_id", LongType(), True),
        StructField("product_name", StringType(), True),
        StructField("category", StringType(), True),
        StructField("subcategory", StringType(), True),
        StructField("brand", StringType(), True),

        StructField("order_date", DateType(), True),
        StructField("year", IntegerType(), True),
        StructField("month_number", IntegerType(), True),
        StructField("month_name", StringType(), True),
        StructField("day_of_week", IntegerType(), True),
        StructField("day_name", StringType(), True),
        StructField("is_weekend", BooleanType(), True),

        StructField("state", StringType(), True),
        StructField("city", StringType(), True),

        StructField("order_status", StringType(), True),
        StructField("payment_method", StringType(), True),
        StructField("quantity", IntegerType(), True),

        StructField(
            "gross_sales",
            DecimalType(14, 2),
            True,
        ),

        StructField(
            "discount_amount",
            DecimalType(14, 2),
            True,
        ),

        StructField(
            "net_sales",
            DecimalType(14, 2),
            True,
        ),

        StructField(
            "total_cost",
            DecimalType(14, 2),
            True,
        ),

        StructField(
            "profit",
            DecimalType(14, 2),
            True,
        ),

        StructField(
            "is_realized_sale",
            BooleanType(),
            True,
        ),

        StructField(
            "is_returned",
            BooleanType(),
            True,
        ),

        StructField(
            "return_reason",
            StringType(),
            True,
        ),
    ]
)


def zero_money():
    """Create a decimal zero expression after Spark starts."""
    return F.lit(0).cast(
        DecimalType(14, 2)
    )


# --------------------------------------------------
# SPARK SESSION
# --------------------------------------------------

def create_spark_session() -> SparkSession:
    """Create a local Spark session."""

    # Use the same Python executable for Spark workers.
    os.environ.setdefault(
        "PYSPARK_PYTHON",
        sys.executable,
    )

    os.environ.setdefault(
        "PYSPARK_DRIVER_PYTHON",
        sys.executable,
    )

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName(
            "EcommerceSalesAnalytics"
        )
        .config(
            "spark.sql.shuffle.partitions",
            "8",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    return spark


# --------------------------------------------------
# READ INPUT
# --------------------------------------------------

def read_sales_data(
    spark: SparkSession,
) -> DataFrame:
    """Read the PostgreSQL export into a Spark DataFrame."""

    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            f"Spark input not found: {INPUT_FILE}\n"
            "Run src/spark/export_spark_input.py first."
        )

    if INPUT_FILE.stat().st_size == 0:
        raise ValueError(
            f"Spark input is empty: {INPUT_FILE}"
        )

    logger.info(
        "Reading Spark input: %s",
        INPUT_FILE,
    )

    df = (
        spark.read
        .schema(SALES_SCHEMA)
        .option("header", True)
        .option("dateFormat", "yyyy-MM-dd")
        .option("nullValue", "")
        .option("mode", "FAILFAST")
        .csv(INPUT_FILE.as_uri())
    )

    return df


# --------------------------------------------------
# INPUT VALIDATION
# --------------------------------------------------

def validate_spark_input(
    df: DataFrame,
) -> int:
    """Validate required columns before aggregating."""

    row_count = df.count()

    if row_count == 0:
        raise ValueError(
            "Spark input contains no data rows."
        )

    required_columns = [
        "sales_key",
        "order_id",
        "item_id",
        "customer_id",
        "product_id",
        "category",
        "order_date",
        "year",
        "month_number",
        "state",
        "city",
        "quantity",
        "gross_sales",
        "discount_amount",
        "net_sales",
        "total_cost",
        "profit",
        "is_realized_sale",
        "is_returned",
    ]

    missing_required = (
        df.filter(
            F.expr(
                " OR ".join(
                    f"`{column}` IS NULL"
                    for column in required_columns
                )
            )
        )
        .limit(1)
        .count()
    )

    if missing_required:
        raise ValueError(
            "Required Spark input columns contain NULL values."
        )

    invalid_measures = (
        df.filter(
            (F.col("quantity") <= 0)
            | (F.col("gross_sales") < 0)
            | (F.col("discount_amount") < 0)
            | (F.col("net_sales") < 0)
            | (F.col("total_cost") < 0)
            | (
                F.col("net_sales")
                != (
                    F.col("gross_sales")
                    - F.col("discount_amount")
                )
            )
            | (
                F.col("profit")
                != (
                    F.col("net_sales")
                    - F.col("total_cost")
                )
            )
        )
        .limit(1)
        .count()
    )

    if invalid_measures:
        raise ValueError(
            "Invalid financial or quantity measures found."
        )

    logger.info(
        "Validated %s Spark input records.",
        f"{row_count:,}",
    )

    return row_count


# --------------------------------------------------
# OUTPUT WRITER
# --------------------------------------------------

def write_report(
    df: DataFrame,
    report_name: str,
) -> None:
    """Write a report to a Spark-managed CSV directory."""

    output_path = (
        OUTPUT_DIR / report_name
    )

    row_count = df.count()

    (
        df.write
        .mode("overwrite")
        .option("header", True)
        .option("nullValue", "")
        .csv(output_path.as_uri())
    )

    logger.info(
        "Wrote report '%s': %s rows → %s",
        report_name,
        f"{row_count:,}",
        output_path,
    )


# --------------------------------------------------
# MONTHLY SALES
# --------------------------------------------------

def build_monthly_sales(
    sales: DataFrame,
) -> DataFrame:

    delivered = sales.filter(
        F.col("is_realized_sale")
    )

    report = (
        delivered
        .groupBy(
            "year",
            "month_number",
            "month_name",
        )
        .agg(
            F.countDistinct(
                "order_id"
            ).alias("delivered_orders"),

            F.sum(
                "quantity"
            ).alias("units_sold"),

            F.sum(
                "gross_sales"
            ).alias("gross_sales"),

            F.sum(
                "discount_amount"
            ).alias("total_discount"),

            F.sum(
                "net_sales"
            ).alias("net_sales_before_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("net_sales"),
                ).otherwise(zero_money())
            ).alias("net_sales_after_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("profit"),
                ).otherwise(zero_money())
            ).alias("retained_profit"),

            F.count(
                F.lit(1)
            ).alias("delivered_item_lines"),

            F.sum(
                F.when(
                    F.col("is_returned"),
                    1,
                ).otherwise(0)
            ).alias("returned_item_lines"),
        )
    )

    return (
        report
        .withColumn(
            "returned_item_rate_pct",
            F.round(
                F.when(
                    F.col("delivered_item_lines") > 0,
                    100.0
                    * F.col("returned_item_lines")
                    / F.col("delivered_item_lines"),
                ).otherwise(F.lit(0.0)),
                2,
            ),
        )
        .orderBy(
            "year",
            "month_number",
        )
    )


# --------------------------------------------------
# CATEGORY PERFORMANCE
# --------------------------------------------------

def build_category_sales(
    sales: DataFrame,
) -> DataFrame:

    delivered = sales.filter(
        F.col("is_realized_sale")
    )

    return (
        delivered
        .groupBy("category")
        .agg(
            F.countDistinct(
                "order_id"
            ).alias("delivered_orders"),

            F.sum(
                "quantity"
            ).alias("units_sold"),

            F.sum(
                "net_sales"
            ).alias("net_sales_before_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("net_sales"),
                ).otherwise(zero_money())
            ).alias("net_sales_after_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("profit"),
                ).otherwise(zero_money())
            ).alias("retained_profit"),
        )
        .orderBy(
            F.desc("net_sales_after_returns")
        )
    )


# --------------------------------------------------
# PRODUCT PERFORMANCE
# --------------------------------------------------

def build_product_performance(
    sales: DataFrame,
) -> DataFrame:

    delivered = sales.filter(
        F.col("is_realized_sale")
    )

    report = (
        delivered
        .groupBy(
            "product_id",
            "product_name",
            "category",
            "subcategory",
            "brand",
        )
        .agg(
            F.countDistinct(
                "order_id"
            ).alias("delivered_orders"),

            F.sum(
                "quantity"
            ).alias("units_sold"),

            F.sum(
                F.when(
                    F.col("is_returned"),
                    F.col("quantity"),
                ).otherwise(0)
            ).alias("returned_units"),

            F.sum(
                "net_sales"
            ).alias("net_sales_before_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("net_sales"),
                ).otherwise(zero_money())
            ).alias("net_sales_after_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("profit"),
                ).otherwise(zero_money())
            ).alias("retained_profit"),

            F.count(
                F.lit(1)
            ).alias("item_lines"),

            F.sum(
                F.when(
                    F.col("is_returned"),
                    1,
                ).otherwise(0)
            ).alias("returned_item_lines"),
        )
    )

    return (
        report
        .withColumn(
            "return_rate_pct",
            F.round(
                100.0
                * F.col("returned_item_lines")
                / F.col("item_lines"),
                2,
            ),
        )
        .drop(
            "item_lines",
            "returned_item_lines",
        )
        .orderBy(
            F.desc("net_sales_after_returns")
        )
    )


# --------------------------------------------------
# REGIONAL PERFORMANCE
# --------------------------------------------------

def build_regional_performance(
    sales: DataFrame,
) -> DataFrame:

    delivered = sales.filter(
        F.col("is_realized_sale")
    )

    return (
        delivered
        .groupBy(
            "state",
            "city",
        )
        .agg(
            F.countDistinct(
                "order_id"
            ).alias("delivered_orders"),

            F.sum(
                "quantity"
            ).alias("units_sold"),

            F.sum(
                "net_sales"
            ).alias("net_sales_before_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("net_sales"),
                ).otherwise(zero_money())
            ).alias("net_sales_after_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("profit"),
                ).otherwise(zero_money())
            ).alias("retained_profit"),
        )
        .orderBy(
            F.desc("net_sales_after_returns")
        )
    )


# --------------------------------------------------
# CUSTOMER PERFORMANCE
# --------------------------------------------------

def build_customer_performance(
    sales: DataFrame,
) -> DataFrame:

    return (
        sales
        .groupBy(
            "customer_id",
            "customer_name",
        )
        .agg(
            F.countDistinct(
                F.when(
                    F.col("is_realized_sale"),
                    F.col("order_id"),
                )
            ).alias("delivered_orders"),

            F.sum(
                F.when(
                    F.col("is_realized_sale"),
                    F.col("quantity"),
                ).otherwise(0)
            ).alias("delivered_units"),

            F.sum(
                F.when(
                    F.col("is_realized_sale"),
                    F.col("net_sales"),
                ).otherwise(zero_money())
            ).alias("sales_before_returns"),

            F.sum(
                F.when(
                    F.col("is_realized_sale")
                    & ~F.col("is_returned"),
                    F.col("net_sales"),
                ).otherwise(zero_money())
            ).alias("sales_after_returns"),

            F.sum(
                F.when(
                    F.col("is_realized_sale")
                    & ~F.col("is_returned"),
                    F.col("profit"),
                ).otherwise(zero_money())
            ).alias("retained_profit"),

            F.max(
                F.when(
                    F.col("is_realized_sale"),
                    F.col("order_date"),
                )
            ).alias("last_purchase_date"),
        )
        .orderBy(
            F.desc("sales_after_returns")
        )
    )


# --------------------------------------------------
# RFM CUSTOMER SEGMENTATION
# --------------------------------------------------

def build_customer_segments(
    customer_performance: DataFrame,
) -> DataFrame:

    active = customer_performance.filter(
        F.col("delivered_orders") > 0
    )

    recency_window = Window.orderBy(
        F.col("last_purchase_date").desc(),
        F.col("customer_id").asc(),
    )

    frequency_window = Window.orderBy(
        F.col("delivered_orders").desc(),
        F.col("customer_id").asc(),
    )

    monetary_window = Window.orderBy(
        F.col("sales_after_returns").desc(),
        F.col("customer_id").asc(),
    )

    scored = (
        active
        .withColumn(
            "recency_score",
            6 - F.ntile(5).over(recency_window),
        )
        .withColumn(
            "frequency_score",
            6 - F.ntile(5).over(frequency_window),
        )
        .withColumn(
            "monetary_score",
            6 - F.ntile(5).over(monetary_window),
        )
    )

    scored = scored.withColumn(
        "customer_segment",
        F.when(
            (F.col("recency_score") >= 4)
            & (F.col("frequency_score") >= 4)
            & (F.col("monetary_score") >= 4),
            F.lit("Champions"),
        )
        .when(
            (F.col("frequency_score") >= 4)
            & (F.col("monetary_score") >= 3),
            F.lit("Loyal Customers"),
        )
        .when(
            (F.col("recency_score") >= 4)
            & (F.col("frequency_score") <= 2),
            F.lit("Recent Customers"),
        )
        .when(
            (F.col("recency_score") <= 2)
            & (
                (F.col("frequency_score") >= 3)
                | (F.col("monetary_score") >= 3)
            ),
            F.lit("At Risk"),
        )
        .otherwise(
            F.lit("Regular Customers")
        ),
    )

    scored_columns = [
        "customer_id",
        "recency_score",
        "frequency_score",
        "monetary_score",
        "customer_segment",
    ]

    return (
        customer_performance
        .join(
            scored.select(*scored_columns),
            on="customer_id",
            how="left",
        )
        .withColumn(
            "customer_segment",
            F.when(
                F.col("delivered_orders") == 0,
                F.lit("No Delivered Orders"),
            ).otherwise(
                F.col("customer_segment")
            ),
        )
        .orderBy(
            F.desc("sales_after_returns")
        )
    )


# --------------------------------------------------
# RETURN REASONS
# --------------------------------------------------

def build_return_analysis(
    sales: DataFrame,
) -> DataFrame:

    returned = sales.filter(
        F.col("is_realized_sale")
        & F.col("is_returned")
    )

    return (
        returned
        .groupBy("return_reason")
        .agg(
            F.count(
                F.lit(1)
            ).alias("returned_item_lines"),

            F.sum(
                "quantity"
            ).alias("returned_units"),

            F.sum(
                "net_sales"
            ).alias("associated_net_sales"),

            F.sum(
                "profit"
            ).alias("original_profit_before_return_adjustment"),
        )
        .orderBy(
            F.desc("returned_units")
        )
    )


# --------------------------------------------------
# WEEKDAY / WEEKEND SALES
# --------------------------------------------------

def build_weekday_sales(
    sales: DataFrame,
) -> DataFrame:

    delivered = sales.filter(
        F.col("is_realized_sale")
    )

    return (
        delivered
        .groupBy(
            "day_of_week",
            "day_name",
            "is_weekend",
        )
        .agg(
            F.countDistinct(
                "order_id"
            ).alias("delivered_orders"),

            F.sum(
                "quantity"
            ).alias("units_sold"),

            F.sum(
                "net_sales"
            ).alias("net_sales_before_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("net_sales"),
                ).otherwise(zero_money())
            ).alias("net_sales_after_returns"),

            F.sum(
                F.when(
                    ~F.col("is_returned"),
                    F.col("profit"),
                ).otherwise(zero_money())
            ).alias("retained_profit"),
        )
        .orderBy("day_of_week")
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main() -> int:
    spark = None

    try:
        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        spark = create_spark_session()

        sales = read_sales_data(spark)

        input_count = validate_spark_input(
            sales
        )

        logger.info(
            "Starting analytical aggregations..."
        )

        reports = {
            "monthly_sales": build_monthly_sales(sales),
            "category_sales": build_category_sales(sales),
            "product_performance": build_product_performance(sales),
            "regional_performance": build_regional_performance(sales),
            "customer_performance": build_customer_performance(sales),
            "return_reasons": build_return_analysis(sales),
            "weekday_sales": build_weekday_sales(sales),
        }

        # Customer segmentation depends on the calculated
        # customer-performance report.
        reports["customer_segments"] = (
            build_customer_segments(
                reports["customer_performance"]
            )
        )

        for report_name, report_df in reports.items():
            write_report(
                report_df,
                report_name,
            )

        print("\n" + "=" * 65)
        print("PYSPARK ANALYTICS COMPLETED SUCCESSFULLY")
        print("=" * 65)
        print(f"Input fact rows: {input_count:,}")
        print(f"Reports generated: {len(reports)}")
        print(f"Output directory: {OUTPUT_DIR}")
        print("=" * 65)

        return 0

    except Exception:
        logger.exception(
            "PySpark processing failed."
        )

        return 1

    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    sys.exit(main())
