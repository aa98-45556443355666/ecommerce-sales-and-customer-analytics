-- ============================================================
-- PAYMENT METHOD ANALYSIS
-- ============================================================

SELECT
    f.payment_method,

    COUNT(DISTINCT f.order_id) AS all_represented_orders,

    COUNT(DISTINCT f.order_id)
        FILTER (WHERE f.is_realized_sale = TRUE)
        AS delivered_orders,

    ROUND(
        COALESCE(
            SUM(f.net_sales)
                FILTER (WHERE f.is_realized_sale = TRUE),
            0
        ),
        2
    ) AS net_sales_before_returns,

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
    ) AS net_sales_after_returns,

    ROUND(
        SUM(f.net_sales)
            FILTER (WHERE f.is_realized_sale = TRUE)
        / NULLIF(
            COUNT(DISTINCT f.order_id)
                FILTER (
                    WHERE f.is_realized_sale = TRUE
                ),
            0
        ),
        2
    ) AS average_order_value

FROM warehouse.fact_sales AS f

GROUP BY
    f.payment_method

ORDER BY
    net_sales_after_returns DESC;