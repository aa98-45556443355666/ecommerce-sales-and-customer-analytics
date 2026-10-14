-- ============================================================
-- PRODUCT PERFORMANCE
-- ============================================================

SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.subcategory,
    p.brand,

    COUNT(DISTINCT f.order_id) AS delivered_orders,

    SUM(f.quantity) AS units_sold,

    SUM(f.quantity)
        FILTER (WHERE f.is_returned = TRUE)
        AS returned_units,

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
            FILTER (WHERE f.is_returned = FALSE),
        2
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.profit)
            FILTER (WHERE f.is_returned = FALSE),
        2
    ) AS retained_profit,

    ROUND(
        100.0 * SUM(f.quantity)
            FILTER (WHERE f.is_returned = TRUE)
        / NULLIF(SUM(f.quantity), 0),
        2
    ) AS return_rate_pct

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_product AS p
    ON p.product_key = f.product_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    p.product_id,
    p.product_name,
    p.category,
    p.subcategory,
    p.brand

ORDER BY
    net_sales_after_returns DESC,
    units_sold DESC;