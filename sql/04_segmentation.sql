-- ===================================================================================
-- 04_segmentation.sql — RFM segmentation (Recency / Frequency / Monetary)
-- Scores 1–5 per dimension using NTILE, then maps to business-readable segments.
-- Reference date = 2026-06-30 (the data cut-off).
-- ===================================================================================

-- name: rfm_users
WITH base AS (
    SELECT user_id,
           JULIANDAY('2026-06-30') - JULIANDAY(MAX(order_ts)) AS recency_days,
           COUNT(*)                                           AS frequency,
           SUM(gmv)                                           AS monetary
    FROM orders
    WHERE status = 'delivered'
    GROUP BY user_id
),
scored AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,   -- recent = high
           NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
           NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM base
)
SELECT user_id, recency_days, frequency, monetary, r_score, f_score, m_score,
       CASE
           WHEN r_score >= 4 AND f_score >= 4               THEN 'Champions'
           WHEN r_score >= 3 AND f_score >= 3               THEN 'Loyal'
           WHEN r_score >= 4 AND f_score <= 2               THEN 'New / Promising'
           WHEN r_score <= 2 AND f_score >= 4               THEN 'At Risk (was valuable)'
           WHEN r_score <= 2 AND f_score <= 2               THEN 'Hibernating / Churned'
           ELSE 'Needs Attention'
       END AS segment
FROM scored;


-- name: rfm_summary
-- Size and value each segment: "who are they, how many, how much GMV do they carry?"
WITH base AS (
    SELECT user_id,
           JULIANDAY('2026-06-30') - JULIANDAY(MAX(order_ts)) AS recency_days,
           COUNT(*) AS frequency, SUM(gmv) AS monetary
    FROM orders WHERE status = 'delivered' GROUP BY user_id
),
scored AS (
    SELECT *, NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
              NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score
    FROM base
),
seg AS (
    SELECT *, CASE
           WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
           WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
           WHEN r_score >= 4 AND f_score <= 2 THEN 'New / Promising'
           WHEN r_score <= 2 AND f_score >= 4 THEN 'At Risk (was valuable)'
           WHEN r_score <= 2 AND f_score <= 2 THEN 'Hibernating / Churned'
           ELSE 'Needs Attention' END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*)                                                     AS users,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)           AS pct_users,
       ROUND(SUM(monetary) / 100000.0, 1)                           AS gmv_lakh,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_gmv,
       ROUND(AVG(frequency), 2)                                     AS avg_orders,
       ROUND(AVG(monetary), 0)                                      AS avg_lifetime_gmv,
       ROUND(AVG(recency_days), 0)                                  AS avg_recency_days
FROM seg
GROUP BY segment
ORDER BY pct_gmv DESC;


-- name: behaviour_by_channel
-- Acquisition-channel quality: cheap traffic that never repeats is not growth.
WITH first_order AS (
    SELECT user_id, MIN(order_ts) AS first_ts FROM orders
    WHERE status='delivered' GROUP BY user_id
),
per_user AS (
    SELECT u.user_id, u.acquisition_channel, u.is_member,
           COUNT(o.order_id)  AS orders,
           SUM(o.gmv)         AS gmv,
           SUM(o.discount)    AS discount
    FROM users u
    JOIN orders o ON o.user_id = u.user_id AND o.status='delivered'
    GROUP BY 1,2,3
)
SELECT acquisition_channel,
       COUNT(*)                                              AS ordering_users,
       ROUND(100.0 * AVG(CASE WHEN orders > 1 THEN 1.0 ELSE 0 END), 1) AS repeat_rate_pct,
       ROUND(AVG(orders), 2)                                 AS orders_per_user,
       ROUND(AVG(gmv), 0)                                    AS gmv_per_user,
       ROUND(100.0 * SUM(discount) / SUM(gmv), 1)            AS discount_pct_of_gmv
FROM per_user
GROUP BY 1
ORDER BY repeat_rate_pct DESC;


-- name: hour_of_day
SELECT CAST(STRFTIME('%H', order_ts) AS INT) AS hour,
       COUNT(*)                              AS orders,
       ROUND(AVG(gmv), 0)                    AS aov,
       ROUND(100.0 * AVG(is_late), 1)        AS late_rate_pct
FROM orders WHERE status='delivered'
GROUP BY 1 ORDER BY 1;
