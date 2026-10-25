
CREATE OR REPLACE VIEW analytics.vw_customer_segment_membership AS

SELECT
    customer_id,
    customer_segment
FROM analytics.vw_customer_segments;