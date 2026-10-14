-- ============================================================
-- SALES BY DAY OF WEEK
-- ============================================================

SELECT
    d.day_of_week,
    d.day_name,

    d.is_weekend,

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

INNER JOIN warehouse.dim_date AS d
    ON d.date_key = f.order_date_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    d.day_of_week,
    d.day_name,
    d.is_weekend

ORDER BY
    d.day_of_week;