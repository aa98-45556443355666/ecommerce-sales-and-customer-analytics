-- ============================================================
-- CUSTOMER LIFETIME VALUE
-- ============================================================

SELECT
    c.customer_id,

    c.first_name || ' ' || c.last_name
        AS customer_name,

    c.city,
    c.state,

    COUNT(DISTINCT f.order_id)
        FILTER (WHERE f.is_realized_sale = TRUE)
        AS delivered_orders,

    COALESCE(
        SUM(f.quantity)
            FILTER (WHERE f.is_realized_sale = TRUE),
        0
    ) AS units_purchased,

    ROUND(
        COALESCE(
            SUM(f.net_sales)
                FILTER (
                    WHERE f.is_realized_sale = TRUE
                ),
            0
        ),
        2
    ) AS lifetime_sales_before_returns,

    ROUND(
        COALESCE(
            SUM(f.net_sales)
                FILTER (
                    WHERE f.is_realized_sale = TRUE
                      AND f.is_returned = FALSE
                ),
            0
        ),
        2
    ) AS lifetime_sales_after_returns,

    MAX(d.full_date)
        FILTER (WHERE f.is_realized_sale = TRUE)
        AS last_purchase_date

FROM warehouse.dim_customer AS c

LEFT JOIN warehouse.fact_sales AS f
    ON f.customer_key = c.customer_key

LEFT JOIN warehouse.dim_date AS d
    ON d.date_key = f.order_date_key

GROUP BY
    c.customer_id,
    c.first_name,
    c.last_name,
    c.city,
    c.state

ORDER BY
    lifetime_sales_after_returns DESC,
    delivered_orders DESC

LIMIT 100;