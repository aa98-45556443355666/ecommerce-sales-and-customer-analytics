-- ============================================================
-- E-Commerce Sales & Customer Analytics Data Platform Data Quality Checks
-- ============================================================

WITH checks AS (

    -- Table availability
    SELECT
        'Customers table is not empty' AS check_name,
        COUNT(*)::BIGINT AS measured_value,
        'positive'::TEXT AS expectation,
        'FAIL'::TEXT AS severity
    FROM staging.customers

    UNION ALL

    SELECT
        'Products table is not empty',
        COUNT(*)::BIGINT,
        'positive',
        'FAIL'
    FROM staging.products

    UNION ALL

    SELECT
        'Orders table is not empty',
        COUNT(*)::BIGINT,
        'positive',
        'FAIL'
    FROM staging.orders

    UNION ALL

    SELECT
        'Order items table is not empty',
        COUNT(*)::BIGINT,
        'positive',
        'FAIL'
    FROM staging.order_items

    UNION ALL

    SELECT
        'Returns table is not empty',
        COUNT(*)::BIGINT,
        'positive',
        'FAIL'
    FROM staging.returns

    UNION ALL

    -- Intentional synthetic data issues
    SELECT
        'Duplicate customer ID groups',
        COUNT(*)::BIGINT,
        'zero',
        'WARN'
    FROM (
        SELECT customer_id
        FROM staging.customers
        GROUP BY customer_id
        HAVING COUNT(*) > 1
    ) AS duplicates

    UNION ALL

    SELECT
        'Missing customer emails',
        COUNT(*)::BIGINT,
        'zero',
        'WARN'
    FROM staging.customers
    WHERE email IS NULL OR BTRIM(email) = ''

    UNION ALL

    SELECT
        'Missing product categories',
        COUNT(*)::BIGINT,
        'zero',
        'WARN'
    FROM staging.products
    WHERE category IS NULL OR BTRIM(category) = ''

    UNION ALL

    SELECT
        'Duplicate order ID groups',
        COUNT(*)::BIGINT,
        'zero',
        'WARN'
    FROM (
        SELECT order_id
        FROM staging.orders
        GROUP BY order_id
        HAVING COUNT(*) > 1
    ) AS duplicates

    UNION ALL

    -- Critical validation checks
    SELECT
        'Duplicate product ID groups',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM (
        SELECT product_id
        FROM staging.products
        GROUP BY product_id
        HAVING COUNT(*) > 1
    ) AS duplicates

    UNION ALL

    SELECT
        'Duplicate order item ID groups',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM (
        SELECT item_id
        FROM staging.order_items
        GROUP BY item_id
        HAVING COUNT(*) > 1
    ) AS duplicates

    UNION ALL

    SELECT
        'Missing required order fields',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM staging.orders
    WHERE order_id IS NULL
       OR customer_id IS NULL
       OR order_date IS NULL
       OR order_status IS NULL
       OR payment_method IS NULL

    UNION ALL

    SELECT
        'Orders with unknown customers',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM staging.orders AS o
    WHERE NOT EXISTS (
        SELECT 1
        FROM staging.customers AS c
        WHERE c.customer_id = o.customer_id
    )

    UNION ALL

    SELECT
        'Order items with unknown orders',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM staging.order_items AS oi
    WHERE NOT EXISTS (
        SELECT 1
        FROM staging.orders AS o
        WHERE o.order_id = oi.order_id
    )

    UNION ALL

    SELECT
        'Order items with unknown products',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM staging.order_items AS oi
    WHERE NOT EXISTS (
        SELECT 1
        FROM staging.products AS p
        WHERE p.product_id = oi.product_id
    )

    UNION ALL

    SELECT
        'Non-positive quantities',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM staging.order_items
    WHERE quantity <= 0

    UNION ALL

    SELECT
        'Invalid product prices or costs',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM staging.products
    WHERE price <= 0
       OR cost < 0
       OR price < cost

    UNION ALL

    SELECT
        'Invalid discounts',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM staging.order_items
    WHERE discount < 0
       OR discount > 1

    UNION ALL

    SELECT
        'Returns not matching order items',
        COUNT(*)::BIGINT,
        'zero',
        'FAIL'
    FROM staging.returns AS r
    WHERE NOT EXISTS (
        SELECT 1
        FROM staging.order_items AS oi
        WHERE oi.order_id = r.order_id
          AND oi.product_id = r.product_id
    )
)

SELECT
    check_name,
    measured_value,
    CASE
        WHEN expectation = 'positive'
             AND measured_value > 0
            THEN 'PASS'

        WHEN expectation = 'positive'
             AND measured_value = 0
            THEN 'FAIL'

        WHEN measured_value = 0
            THEN 'PASS'

        WHEN severity = 'WARN'
            THEN 'WARN'

        ELSE 'FAIL'
    END AS status
FROM checks
ORDER BY
    CASE
        WHEN expectation = 'positive' AND measured_value = 0
            THEN 1
        WHEN expectation = 'zero'
             AND measured_value > 0
             AND severity = 'FAIL'
            THEN 1
        WHEN expectation = 'zero'
             AND measured_value > 0
             AND severity = 'WARN'
            THEN 2
        ELSE 3
    END,
    check_name;