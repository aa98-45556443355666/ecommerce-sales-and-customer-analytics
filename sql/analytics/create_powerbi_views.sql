-- ============================================================
-- POWER BI REPORTING VIEWS
-- Source: PostgreSQL star-schema warehouse
-- ============================================================

CREATE SCHEMA IF NOT EXISTS analytics;


-- ============================================================
-- 1. EXECUTIVE KPIs
-- One row for dashboard cards
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_executive_kpis AS

SELECT
    COUNT(DISTINCT order_id)
        FILTER (WHERE is_realized_sale)
        AS delivered_orders,

    COUNT(*)
        FILTER (WHERE is_realized_sale)
        AS delivered_item_lines,

    COALESCE(
        SUM(quantity) FILTER (WHERE is_realized_sale),
        0
    ) AS delivered_units,

    ROUND(
        COALESCE(
            SUM(gross_sales)
                FILTER (WHERE is_realized_sale),
            0
        ),
        2
    ) AS gross_sales,

    ROUND(
        COALESCE(
            SUM(discount_amount)
                FILTER (WHERE is_realized_sale),
            0
        ),
        2
    ) AS total_discount,

    ROUND(
        COALESCE(
            SUM(net_sales)
                FILTER (WHERE is_realized_sale),
            0
        ),
        2
    ) AS net_sales_before_returns,

    ROUND(
        COALESCE(
            SUM(net_sales)
                FILTER (
                    WHERE is_realized_sale
                      AND NOT is_returned
                ),
            0
        ),
        2
    ) AS net_sales_after_returns,

    ROUND(
        COALESCE(
            SUM(profit)
                FILTER (
                    WHERE is_realized_sale
                      AND NOT is_returned
                ),
            0
        ),
        2
    ) AS retained_profit,

    COUNT(DISTINCT customer_key)
        FILTER (WHERE is_realized_sale)
        AS delivered_customers,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE is_realized_sale AND is_returned
        )
        / NULLIF(
            COUNT(*) FILTER (WHERE is_realized_sale),
            0
        ),
        2
    ) AS returned_item_rate_pct,

    ROUND(
        SUM(net_sales)
            FILTER (WHERE is_realized_sale)
        / NULLIF(
            COUNT(DISTINCT order_id)
                FILTER (WHERE is_realized_sale),
            0
        ),
        2
    ) AS average_order_value

FROM warehouse.fact_sales;


-- ============================================================
-- 2. MONTHLY SALES
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_monthly_sales AS

SELECT
    DATE_TRUNC('month', d.full_date)::DATE AS month_start,

    d.year,
    d.month_number,
    d.month_name,

    COUNT(DISTINCT f.order_id) AS delivered_orders,

    SUM(f.quantity) AS units_sold,

    ROUND(
        SUM(f.gross_sales),
        2
    ) AS gross_sales,

    ROUND(
        SUM(f.discount_amount),
        2
    ) AS total_discount,

    ROUND(
        SUM(f.net_sales),
        2
    ) AS net_sales_before_returns,

    ROUND(
        SUM(f.net_sales)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.profit)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS retained_profit

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_date AS d
    ON d.date_key = f.order_date_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    DATE_TRUNC('month', d.full_date)::DATE,
    d.year,
    d.month_number,
    d.month_name;


-- ============================================================
-- 3. CATEGORY PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_category_performance AS

SELECT
    p.category,

    COUNT(DISTINCT f.order_id) AS delivered_orders,

    SUM(f.quantity) AS units_sold,

    ROUND(
        SUM(f.net_sales),
        2
    ) AS net_sales_before_returns,

    ROUND(
        SUM(f.net_sales)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.profit)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS retained_profit,

    ROUND(
        100.0
        * COUNT(*) FILTER (WHERE f.is_returned)
        / NULLIF(COUNT(*), 0),
        2
    ) AS returned_item_rate_pct

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_product AS p
    ON p.product_key = f.product_key

WHERE f.is_realized_sale = TRUE

GROUP BY p.category;


-- ============================================================
-- 4. PRODUCT PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_product_performance AS

SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.subcategory,
    p.brand,

    COUNT(DISTINCT f.order_id) AS delivered_orders,

    SUM(f.quantity) AS units_sold,

    SUM(f.quantity)
        FILTER (WHERE f.is_returned)
        AS returned_units,

    ROUND(
        SUM(f.net_sales),
        2
    ) AS net_sales_before_returns,

    ROUND(
        SUM(f.net_sales)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.profit)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS retained_profit,

    ROUND(
        100.0
        * COUNT(*) FILTER (WHERE f.is_returned)
        / NULLIF(COUNT(*), 0),
        2
    ) AS returned_item_rate_pct

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_product AS p
    ON p.product_key = f.product_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    p.product_id,
    p.product_name,
    p.category,
    p.subcategory,
    p.brand;


-- ============================================================
-- 5. CUSTOMER PERFORMANCE
-- Includes customers who have no delivered orders
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_customer_performance AS

WITH customer_metrics AS (

    SELECT
        c.customer_key,
        c.customer_id,

        CONCAT_WS(
            ' ',
            c.first_name,
            c.last_name
        ) AS customer_name,

        c.city,
        c.state,
        c.signup_date,

        COUNT(DISTINCT f.order_id)
            FILTER (WHERE f.is_realized_sale)
            AS delivered_orders,

        COALESCE(
            SUM(f.quantity)
                FILTER (WHERE f.is_realized_sale),
            0
        ) AS delivered_units,

        COALESCE(
            SUM(f.net_sales)
                FILTER (WHERE f.is_realized_sale),
            0
        ) AS sales_before_returns,

        COALESCE(
            SUM(f.net_sales)
                FILTER (
                    WHERE f.is_realized_sale
                      AND NOT f.is_returned
                ),
            0
        ) AS sales_after_returns,

        COALESCE(
            SUM(f.profit)
                FILTER (
                    WHERE f.is_realized_sale
                      AND NOT f.is_returned
                ),
            0
        ) AS retained_profit,

        MAX(d.full_date)
            FILTER (WHERE f.is_realized_sale)
            AS last_purchase_date

    FROM warehouse.dim_customer AS c

    LEFT JOIN warehouse.fact_sales AS f
        ON f.customer_key = c.customer_key

    LEFT JOIN warehouse.dim_date AS d
        ON d.date_key = f.order_date_key

    GROUP BY
        c.customer_key,
        c.customer_id,
        c.first_name,
        c.last_name,
        c.city,
        c.state,
        c.signup_date
)

SELECT
    customer_key,
    customer_id,
    customer_name,
    city,
    state,
    signup_date,
    delivered_orders,
    delivered_units,

    ROUND(sales_before_returns, 2)
        AS lifetime_sales_before_returns,

    ROUND(sales_after_returns, 2)
        AS lifetime_sales_after_returns,

    ROUND(retained_profit, 2)
        AS retained_profit,

    last_purchase_date

FROM customer_metrics;


-- ============================================================
-- 6. CUSTOMER SEGMENTS
-- Relative RFM-style scores: 1 to 5
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_customer_segments AS

WITH active_customers AS (

    SELECT *
    FROM analytics.vw_customer_performance
    WHERE delivered_orders > 0

),

scored AS (

    SELECT
        customer_id,

        6 - NTILE(5) OVER (
            ORDER BY last_purchase_date DESC, customer_id
        ) AS recency_score,

        6 - NTILE(5) OVER (
            ORDER BY delivered_orders DESC, customer_id
        ) AS frequency_score,

        6 - NTILE(5) OVER (
            ORDER BY lifetime_sales_after_returns DESC,
                     customer_id
        ) AS monetary_score

    FROM active_customers

)

SELECT
    c.customer_id,
    c.customer_name,
    c.delivered_orders,
    c.lifetime_sales_after_returns,
    c.last_purchase_date,

    s.recency_score,
    s.frequency_score,
    s.monetary_score,

    CASE
        WHEN c.delivered_orders = 0
            THEN 'No Delivered Orders'

        WHEN s.recency_score >= 4
         AND s.frequency_score >= 4
         AND s.monetary_score >= 4
            THEN 'Champions'

        WHEN s.frequency_score >= 4
         AND s.monetary_score >= 3
            THEN 'Loyal Customers'

        WHEN s.recency_score >= 4
         AND s.frequency_score <= 2
            THEN 'Recent Customers'

        WHEN s.recency_score <= 2
         AND (
             s.frequency_score >= 3
             OR s.monetary_score >= 3
         )
            THEN 'At Risk'

        ELSE 'Regular Customers'
    END AS customer_segment

FROM analytics.vw_customer_performance AS c

LEFT JOIN scored AS s
    ON s.customer_id = c.customer_id;


-- ============================================================
-- 7. REGIONAL PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_regional_performance AS

SELECT
    r.country,
    r.state,
    r.city,

    COUNT(DISTINCT f.order_id) AS delivered_orders,

    SUM(f.quantity) AS units_sold,

    ROUND(
        SUM(f.net_sales)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.profit)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS retained_profit

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_region AS r
    ON r.region_key = f.region_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    r.country,
    r.state,
    r.city;


-- ============================================================
-- 8. RETURN REASONS
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_return_reasons AS

SELECT
    f.return_reason,

    COUNT(*) AS returned_item_lines,

    SUM(f.quantity) AS returned_units,

    ROUND(
        SUM(f.net_sales),
        2
    ) AS associated_net_sales

FROM warehouse.fact_sales AS f

WHERE f.is_realized_sale = TRUE
  AND f.is_returned = TRUE

GROUP BY f.return_reason;


-- ============================================================
-- 9. PAYMENT METHOD PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_payment_method_performance AS

SELECT
    f.payment_method,

    COUNT(DISTINCT f.order_id)
        AS represented_orders,

    COUNT(DISTINCT f.order_id)
        FILTER (WHERE f.is_realized_sale)
        AS delivered_orders,

    ROUND(
        SUM(f.net_sales)
            FILTER (
                WHERE f.is_realized_sale
                  AND NOT f.is_returned
            ),
        2
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.profit)
            FILTER (
                WHERE f.is_realized_sale
                  AND NOT f.is_returned
            ),
        2
    ) AS retained_profit

FROM warehouse.fact_sales AS f

GROUP BY f.payment_method;


-- ============================================================
-- 10. ORDER STATUS PERFORMANCE
-- Counts orders represented in the fact table
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_order_status_performance AS

SELECT
    f.order_status,

    COUNT(DISTINCT f.order_id) AS represented_orders,

    COUNT(*) AS item_lines,

    SUM(f.quantity) AS units,

    ROUND(
        SUM(f.net_sales),
        2
    ) AS net_sales_before_returns

FROM warehouse.fact_sales AS f

GROUP BY f.order_status;


-- ============================================================
-- 11. WEEKDAY PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_weekday_performance AS

SELECT
    d.day_of_week,
    d.day_name,
    d.is_weekend,

    COUNT(DISTINCT f.order_id) AS delivered_orders,

    SUM(f.quantity) AS units_sold,

    ROUND(
        SUM(f.net_sales)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.profit)
            FILTER (WHERE NOT f.is_returned),
        2
    ) AS retained_profit

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_date AS d
    ON d.date_key = f.order_date_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    d.day_of_week,
    d.day_name,
    d.is_weekend;


-- ============================================================
-- 12. POWER BI FACT VIEW
-- Boolean values exported as explicit true/false strings.
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_powerbi_sales_fact AS

SELECT
    sales_key,
    order_id,
    item_id,

    customer_key,
    product_key,
    order_date_key,
    region_key,

    order_status,
    payment_method,

    quantity,
    unit_price,
    discount_rate,

    gross_sales,
    discount_amount,
    net_sales,

    unit_cost,
    total_cost,
    profit,

    CASE
        WHEN is_realized_sale THEN 'true'
        ELSE 'false'
    END AS is_realized_sale,

    CASE
        WHEN is_returned THEN 'true'
        ELSE 'false'
    END AS is_returned,

    return_date_key,
    return_reason

FROM warehouse.fact_sales;
