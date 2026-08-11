-- ===================================================================================
-- 03_funnel.sql — Session funnel: app_open → search → restaurant_view →
--                 add_to_cart → checkout_start → payment_success
-- Definition: a SESSION counts at a step if it fired that event at least once.
-- Step conversion = sessions at step k / sessions at step k-1.
-- ===================================================================================

-- name: funnel_overall
WITH step_sessions AS (
    SELECT event_name, step_no, COUNT(DISTINCT session_id) AS sessions
    FROM app_events
    GROUP BY 1, 2
)
SELECT step_no,
       event_name,
       sessions,
       ROUND(100.0 * sessions / MAX(sessions) OVER (), 1)                    AS pct_of_top,
       ROUND(100.0 * sessions / LAG(sessions) OVER (ORDER BY step_no), 1)    AS step_conv_pct,
       ROUND(100.0 - 100.0 * sessions / LAG(sessions) OVER (ORDER BY step_no), 1)
                                                                             AS step_dropoff_pct
FROM step_sessions
ORDER BY step_no;


-- name: funnel_by_platform
-- Segmenting the funnel is where the actual insight lives: an overall funnel tells
-- you a step is weak, a segmented funnel tells you WHO it is weak for.
WITH step_sessions AS (
    SELECT platform, event_name, step_no, COUNT(DISTINCT session_id) AS sessions
    FROM app_events
    GROUP BY 1, 2, 3
)
SELECT platform,
       step_no,
       event_name,
       sessions,
       ROUND(100.0 * sessions / LAG(sessions) OVER (PARTITION BY platform ORDER BY step_no), 1)
                                                          AS step_conv_pct
FROM step_sessions
ORDER BY platform, step_no;


-- name: funnel_by_city
WITH step_sessions AS (
    SELECT city, step_no, COUNT(DISTINCT session_id) AS sessions
    FROM app_events
    GROUP BY 1, 2
),
pivoted AS (
    SELECT city,
           MAX(CASE WHEN step_no = 1 THEN sessions END) AS app_open,
           MAX(CASE WHEN step_no = 4 THEN sessions END) AS add_to_cart,
           MAX(CASE WHEN step_no = 5 THEN sessions END) AS checkout_start,
           MAX(CASE WHEN step_no = 6 THEN sessions END) AS payment_success
    FROM step_sessions GROUP BY city
)
SELECT city,
       app_open,
       ROUND(100.0 * payment_success / app_open, 1)      AS session_to_order_pct,
       ROUND(100.0 * payment_success / checkout_start, 1) AS payment_success_pct
FROM pivoted
ORDER BY session_to_order_pct;


-- name: payment_leak_size
-- How many orders are we losing at the payment step on Android, if Android
-- converted at the iOS rate? (The "size the prize" query.)
WITH s AS (
    SELECT platform,
           COUNT(DISTINCT CASE WHEN step_no = 5 THEN session_id END) AS checkout,
           COUNT(DISTINCT CASE WHEN step_no = 6 THEN session_id END) AS paid
    FROM app_events GROUP BY platform
)
SELECT
    (SELECT ROUND(100.0 * paid / checkout, 1) FROM s WHERE platform='Android') AS android_pay_conv_pct,
    (SELECT ROUND(100.0 * paid / checkout, 1) FROM s WHERE platform='iOS')     AS ios_pay_conv_pct,
    (SELECT ROUND(checkout * (SELECT 1.0*paid/checkout FROM s WHERE platform='iOS') - paid, 0)
     FROM s WHERE platform='Android')                                          AS recoverable_orders_6mo;
