-- ============================================================
-- CUSTOMER RFM(Recency, Frequency, Monetary Value) SEGMENTATION
-- ============================================================

WITH customer_metrics AS (

    SELECT
        c.customer_key,
        c.customer_id,

        c.first_name || ' ' || c.last_name
            AS customer_name,

        COUNT(DISTINCT f.order_id)
            FILTER (WHERE f.is_realized_sale = TRUE)
            AS order_frequency,

        COALESCE(
            SUM(f.net_sales)
                FILTER (
                    WHERE f.is_realized_sale = TRUE
                      AND f.is_returned = FALSE
                ),
            0
        ) AS monetary_value,

        MAX(d.full_date)
            FILTER (WHERE f.is_realized_sale = TRUE)
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
        c.last_name
),

active_customers AS (

    SELECT *
    FROM customer_metrics
    WHERE order_frequency > 0

),

rfm_scores AS (

    SELECT
        customer_key,
        customer_id,
        customer_name,
        order_frequency,
        monetary_value,
        last_purchase_date,

        (
            6 - NTILE(5) OVER (
                ORDER BY last_purchase_date DESC
            )
        ) AS recency_score,

        (
            6 - NTILE(5) OVER (
                ORDER BY order_frequency DESC
            )
        ) AS frequency_score,

        (
            6 - NTILE(5) OVER (
                ORDER BY monetary_value DESC
            )
        ) AS monetary_score

    FROM active_customers
)

SELECT
    cm.customer_id,
    cm.customer_name,
    cm.order_frequency,
    ROUND(cm.monetary_value, 2) AS monetary_value,
    cm.last_purchase_date,

    s.recency_score,
    s.frequency_score,
    s.monetary_score,

    CASE
        WHEN cm.order_frequency = 0
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

FROM customer_metrics AS cm

LEFT JOIN rfm_scores AS s
    ON s.customer_key = cm.customer_key

ORDER BY
    cm.monetary_value DESC;