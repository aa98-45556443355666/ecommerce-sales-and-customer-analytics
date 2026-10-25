
CREATE OR REPLACE VIEW analytics.vw_return_detail AS

SELECT
    r.return_id,
    r.order_id,

    o.customer_id,
    COALESCE(
        cs.customer_segment,
        'Unknown'
    ) AS customer_segment,

    r.product_id,
    p.product_name,
    p.category,

    r.return_date::DATE AS return_date,

    TO_CHAR(
        r.return_date::DATE,
        'YYYYMMDD'
    )::INTEGER AS return_date_key,

    EXTRACT(
        YEAR FROM r.return_date
    )::INTEGER AS return_year,

    EXTRACT(
        MONTH FROM r.return_date
    )::INTEGER AS return_month_number,

    TO_CHAR(
        r.return_date::DATE,
        'YYYY-MM'
    ) AS return_year_month,

    r.return_reason,

    o.shipping_city,
    o.shipping_state,

    1::INTEGER AS return_records

FROM clean.returns AS r

INNER JOIN clean.orders AS o
    ON o.order_id = r.order_id

LEFT JOIN clean.products AS p
    ON p.product_id = r.product_id

LEFT JOIN analytics.vw_customer_segment_membership AS cs
    ON cs.customer_id = o.customer_id;