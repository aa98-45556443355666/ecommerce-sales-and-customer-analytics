-- ============================================================
-- MONTHLY SALES PERFORMANCE
-- ============================================================

SELECT
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
            FILTER (WHERE f.is_returned = FALSE),
        2
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.profit)
            FILTER (WHERE f.is_returned = FALSE),
        2
    ) AS retained_profit,

    ROUND(
        SUM(f.net_sales)
        / NULLIF(COUNT(DISTINCT f.order_id), 0),
        2
    ) AS average_order_value

FROM warehouse.fact_sales AS f

INNER JOIN warehouse.dim_date AS d
    ON d.date_key = f.order_date_key

WHERE f.is_realized_sale = TRUE

GROUP BY
    d.year,
    d.month_number,
    d.month_name

ORDER BY
    d.year,
    d.month_number;