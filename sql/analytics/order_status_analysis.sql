-- ============================================================
-- ORDER STATUS ANALYSIS
-- ============================================================

SELECT
    f.order_status,

    COUNT(DISTINCT f.order_id) AS represented_orders,

    COUNT(*) AS order_item_lines,

    SUM(f.quantity) AS units_in_order_items,

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
        100.0 * COUNT(DISTINCT f.order_id)
        / NULLIF(
            SUM(COUNT(DISTINCT f.order_id)) OVER (),
            0
        ),
        2
    ) AS percentage_of_represented_orders

FROM warehouse.fact_sales AS f

GROUP BY
    f.order_status

ORDER BY
    represented_orders DESC;