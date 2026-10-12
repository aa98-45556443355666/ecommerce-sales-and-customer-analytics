-- ============================================================
-- E-Commerce Sales & Customer Analytics Data Platform
-- Staging-to-Clean Transformation
-- ============================================================

TRUNCATE TABLE
    clean.returns,
    clean.order_items,
    clean.orders,
    clean.products,
    clean.customers
RESTART IDENTITY;


-- ============================================================
-- 1. CLEAN CUSTOMERS
-- ============================================================

INSERT INTO clean.customers (
    customer_id,
    first_name,
    last_name,
    email,
    gender,
    date_of_birth,
    city,
    state,
    country,
    signup_date
)
SELECT DISTINCT ON (c.customer_id)
    c.customer_id,
    BTRIM(c.first_name),
    BTRIM(c.last_name),
    LOWER(NULLIF(BTRIM(c.email), '')),
    COALESCE(
        NULLIF(INITCAP(BTRIM(c.gender)), ''),
        'Unknown'
    ),
    c.date_of_birth,
    COALESCE(NULLIF(BTRIM(c.city), ''), 'Unknown'),
    COALESCE(NULLIF(BTRIM(c.state), ''), 'Unknown'),
    COALESCE(NULLIF(BTRIM(c.country), ''), 'India'),
    c.signup_date
FROM staging.customers AS c
WHERE c.customer_id IS NOT NULL
  AND NULLIF(BTRIM(c.first_name), '') IS NOT NULL
  AND NULLIF(BTRIM(c.last_name), '') IS NOT NULL
  AND c.date_of_birth IS NOT NULL
  AND c.signup_date IS NOT NULL
  AND c.date_of_birth <= c.signup_date
  AND c.signup_date <= CURRENT_DATE
ORDER BY
    c.customer_id,
    (NULLIF(BTRIM(c.email), '') IS NULL),
    c.signup_date DESC NULLS LAST,
    c.first_name,
    c.last_name;


-- ============================================================
-- 2. CLEAN PRODUCTS
-- ============================================================

INSERT INTO clean.products (
    product_id,
    product_name,
    category,
    subcategory,
    brand,
    price,
    cost
)
SELECT DISTINCT ON (p.product_id)
    p.product_id,
    BTRIM(p.product_name),
    COALESCE(
        NULLIF(INITCAP(BTRIM(p.category)), ''),
        'Unknown'
    ),
    COALESCE(
        NULLIF(BTRIM(p.subcategory), ''),
        'Unknown'
    ),
    COALESCE(
        NULLIF(BTRIM(p.brand), ''),
        'Unknown'
    ),
    p.price,
    p.cost
FROM staging.products AS p
WHERE p.product_id IS NOT NULL
  AND NULLIF(BTRIM(p.product_name), '') IS NOT NULL
  AND p.price IS NOT NULL
  AND p.cost IS NOT NULL
  AND p.price > 0
  AND p.cost >= 0
  AND p.price >= p.cost
ORDER BY
    p.product_id,
    (NULLIF(BTRIM(p.category), '') IS NULL),
    p.product_name;


-- ============================================================
-- 3. CLEAN ORDERS
-- ============================================================

INSERT INTO clean.orders (
    order_id,
    customer_id,
    order_date,
    order_status,
    payment_method,
    shipping_city,
    shipping_state
)
SELECT DISTINCT ON (o.order_id)
    o.order_id,
    o.customer_id,
    o.order_date,
    BTRIM(o.order_status),
    BTRIM(o.payment_method),
    COALESCE(
        NULLIF(BTRIM(o.shipping_city), ''),
        'Unknown'
    ),
    COALESCE(
        NULLIF(BTRIM(o.shipping_state), ''),
        'Unknown'
    )
FROM staging.orders AS o
INNER JOIN clean.customers AS c
    ON c.customer_id = o.customer_id
WHERE o.order_id IS NOT NULL
  AND o.order_date IS NOT NULL
  AND o.order_date <= CURRENT_DATE
  AND o.order_status IS NOT NULL
  AND BTRIM(o.order_status) IN (
      'Delivered',
      'Shipped',
      'Processing',
      'Cancelled'
  )
  AND o.payment_method IS NOT NULL
  AND BTRIM(o.payment_method) IN (
      'UPI',
      'Credit Card',
      'Debit Card',
      'Net Banking',
      'COD'
  )
ORDER BY
    o.order_id,
    o.order_date DESC NULLS LAST,
    o.customer_id;


-- ============================================================
-- 4. CLEAN ORDER ITEMS
-- ============================================================

WITH deduplicated_item_ids AS (
    SELECT DISTINCT ON (oi.item_id)
        oi.item_id,
        oi.order_id,
        oi.product_id,
        oi.quantity,
        oi.unit_price,
        oi.discount
    FROM staging.order_items AS oi
    WHERE oi.item_id IS NOT NULL
    ORDER BY
        oi.item_id,
        oi.order_id,
        oi.product_id
)
INSERT INTO clean.order_items (
    item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount
)
SELECT DISTINCT ON (
    oi.order_id,
    oi.product_id
)
    oi.item_id,
    oi.order_id,
    oi.product_id,
    oi.quantity,
    oi.unit_price,
    oi.discount
FROM deduplicated_item_ids AS oi
INNER JOIN clean.orders AS o
    ON o.order_id = oi.order_id
INNER JOIN clean.products AS p
    ON p.product_id = oi.product_id
WHERE oi.quantity IS NOT NULL
  AND oi.quantity > 0
  AND oi.unit_price IS NOT NULL
  AND oi.unit_price > 0
  AND oi.discount IS NOT NULL
  AND oi.discount BETWEEN 0 AND 1
  AND ROUND(oi.unit_price, 2) = ROUND(p.price, 2)
ORDER BY
    oi.order_id,
    oi.product_id,
    oi.item_id;

-- ============================================================
-- 5. CLEAN RETURNS
-- ============================================================

INSERT INTO clean.returns (
    return_id,
    order_id,
    product_id,
    return_date,
    return_reason
)
SELECT DISTINCT ON (r.return_id)
    r.return_id,
    r.order_id,
    r.product_id,
    r.return_date,
    BTRIM(r.return_reason)
FROM staging.returns AS r
INNER JOIN clean.order_items AS oi
    ON oi.order_id = r.order_id
   AND oi.product_id = r.product_id
INNER JOIN clean.orders AS o
    ON o.order_id = r.order_id
WHERE r.return_id IS NOT NULL
  AND r.return_date IS NOT NULL
  AND r.return_date >= o.order_date
  AND NULLIF(BTRIM(r.return_reason), '') IS NOT NULL
ORDER BY
    r.return_id,
    r.return_date DESC;