-- ===================================================================================
-- 01_metrics.sql — Metric definitions + headline numbers
-- Engine: SQLite 3.50 (window functions available). Run via src/run_analysis.py
-- Each block is named with "-- name: <block>" so Python can load it individually.
-- ===================================================================================

-- name: headline
-- The single slide of numbers every stakeholder asks for first.
-- NOTE: we count only DELIVERED orders as revenue events; cancelled orders are
-- excluded from GMV but kept for the cancellation guardrail.
WITH o AS (
    SELECT * FROM orders WHERE status = 'delivered'
)
SELECT
    (SELECT COUNT(*) FROM users)                                   AS registered_users,
    COUNT(DISTINCT o.user_id)                                      AS ordering_users,
    ROUND(100.0 * COUNT(DISTINCT o.user_id) / (SELECT COUNT(*) FROM users), 1)
                                                                   AS activation_rate_pct,
    COUNT(*)                                                       AS orders,
    ROUND(SUM(o.gmv), 0)                                           AS gmv,
    ROUND(AVG(o.gmv), 0)                                           AS aov,
    ROUND(1.0 * COUNT(*) / COUNT(DISTINCT o.user_id), 2)           AS orders_per_ordering_user,
    ROUND(100.0 * AVG(o.is_late), 1)                               AS late_delivery_rate_pct,
    ROUND(AVG(o.rating), 2)                                        AS avg_rating
FROM o;


-- name: north_star
-- NORTH STAR: 30-day repeat rate of new users
--   = of all users whose FIRST order was >=30 days before the data cut-off,
--     what share placed a SECOND order within 30 days of the first?
-- Why this metric: it is the earliest reliable predictor of lifetime value in food
-- delivery, it is fast to move, and unlike "orders" it cannot be faked by buying
-- more traffic. Restricting to fully-matured cohorts avoids right-censoring bias.
WITH firsts AS (
    SELECT user_id,
           MIN(order_ts) AS first_ts
    FROM orders
    WHERE status = 'delivered'
    GROUP BY user_id
),
matured AS (              -- only users with a full 30-day window of observation
    SELECT f.user_id, f.first_ts
    FROM firsts f
    WHERE JULIANDAY('2026-06-30') - JULIANDAY(f.first_ts) >= 30
),
second AS (
    SELECT m.user_id,
           MAX(CASE WHEN o.order_ts > m.first_ts
                     AND JULIANDAY(o.order_ts) - JULIANDAY(m.first_ts) <= 30
                    THEN 1 ELSE 0 END) AS repeated_30d
    FROM matured m
    JOIN orders o ON o.user_id = m.user_id AND o.status = 'delivered'
    GROUP BY m.user_id
)
SELECT COUNT(*)                                AS matured_new_users,
       SUM(repeated_30d)                       AS repeated_users,
       ROUND(100.0 * AVG(repeated_30d), 2)     AS repeat_30d_rate_pct
FROM second;


-- name: monthly_trend
-- Supporting metrics over time — is the business healthy month to month?
SELECT STRFTIME('%Y-%m', order_ts)                       AS month,
       COUNT(DISTINCT user_id)                           AS active_users,
       COUNT(*)                                          AS orders,
       ROUND(SUM(gmv) / 100000.0, 1)                     AS gmv_lakh,
       ROUND(AVG(gmv), 0)                                AS aov,
       ROUND(100.0 * AVG(is_late), 1)                    AS late_rate_pct,
       ROUND(100.0 * SUM(discount) / SUM(gmv), 1)        AS discount_pct_of_gmv
FROM orders
WHERE status = 'delivered'
GROUP BY 1
ORDER BY 1;


-- name: guardrails
-- GUARDRAIL metrics: things that must NOT get worse while we push the north star.
SELECT STRFTIME('%Y-%m', order_ts)                                   AS month,
       ROUND(100.0 * AVG(CASE WHEN status='cancelled' THEN 1.0 ELSE 0 END), 2) AS cancel_rate_pct,
       ROUND(AVG(delivery_minutes), 1)                               AS avg_delivery_min,
       ROUND(AVG(rating), 2)                                         AS avg_rating,
       ROUND(AVG(gmv - discount), 0)                                 AS net_revenue_per_order
FROM orders
GROUP BY 1
ORDER BY 1;
