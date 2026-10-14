-- ============================================================
-- REGIONAL SALES PERFORMANCE
-- ============================================================

SELECT
    r.country,
    r.state,
    r.city,

    COUNT(DISTINCT f.order_id) AS delivered_orders,

    SUM(f.quantity) AS units_sold,

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
    ) AS retained_profit

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_region AS r
    ON r.region_key = f.region_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    r.country,
    r.state,
    r.city

ORDER BY
    net_sales_after_returns DESC;