-- ===================================================================================
-- 02_cohort_retention.sql — Classic monthly cohort retention
-- A cohort = all users whose FIRST delivered order fell in month M.
-- Retention in period k = share of that cohort placing >=1 order in month M+k.
-- ===================================================================================

-- name: cohort_matrix
WITH first_order AS (
    SELECT user_id,
           MIN(order_ts)                       AS first_ts,
           STRFTIME('%Y-%m', MIN(order_ts))    AS cohort_month
    FROM orders
    WHERE status = 'delivered'
    GROUP BY user_id
),
activity AS (
    SELECT f.user_id,
           f.cohort_month,
           STRFTIME('%Y-%m', o.order_ts)       AS active_month,
           -- months elapsed = 12*(year diff) + (month diff)
           (CAST(STRFTIME('%Y', o.order_ts) AS INT) - CAST(STRFTIME('%Y', f.first_ts) AS INT)) * 12
         + (CAST(STRFTIME('%m', o.order_ts) AS INT) - CAST(STRFTIME('%m', f.first_ts) AS INT))
                                               AS period_index
    FROM first_order f
    JOIN orders o ON o.user_id = f.user_id AND o.status = 'delivered'
),
sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size FROM first_order GROUP BY 1
)
SELECT a.cohort_month,
       s.cohort_size,
       a.period_index,
       COUNT(DISTINCT a.user_id)                                       AS active_users,
       ROUND(100.0 * COUNT(DISTINCT a.user_id) / s.cohort_size, 1)     AS retention_pct
FROM activity a
JOIN sizes s ON s.cohort_month = a.cohort_month
GROUP BY 1, 2, 3
ORDER BY 1, 3;


-- name: cohort_by_late
-- The same curve, split by whether the user's FIRST delivery was late.
-- This is the chart that carries the whole project.
WITH first_order AS (
    SELECT o.user_id,
           MIN(o.order_ts) AS first_ts
    FROM orders o WHERE o.status = 'delivered'
    GROUP BY o.user_id
),
first_flag AS (
    SELECT f.user_id, f.first_ts,
           MAX(o.is_late) AS first_was_late      -- MAX over the single matching row
    FROM first_order f
    JOIN orders o ON o.user_id = f.user_id AND o.order_ts = f.first_ts
    GROUP BY f.user_id, f.first_ts
),
activity AS (
    SELECT ff.user_id, ff.first_was_late,
           (CAST(STRFTIME('%Y', o.order_ts) AS INT) - CAST(STRFTIME('%Y', ff.first_ts) AS INT)) * 12
         + (CAST(STRFTIME('%m', o.order_ts) AS INT) - CAST(STRFTIME('%m', ff.first_ts) AS INT))
                                                 AS period_index
    FROM first_flag ff
    JOIN orders o ON o.user_id = ff.user_id AND o.status = 'delivered'
),
sizes AS (
    SELECT first_was_late, COUNT(*) AS n FROM first_flag GROUP BY 1
)
SELECT CASE a.first_was_late WHEN 1 THEN 'First delivery LATE'
                             ELSE 'First delivery ON TIME' END        AS segment,
       a.period_index,
       ROUND(100.0 * COUNT(DISTINCT a.user_id) / s.n, 1)              AS retention_pct,
       s.n                                                            AS cohort_size
FROM activity a
JOIN sizes s ON s.first_was_late = a.first_was_late
GROUP BY 1, 2, 4
ORDER BY 1, 2;
