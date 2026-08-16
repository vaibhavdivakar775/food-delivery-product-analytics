-- ===================================================================================
-- 04_segmentation.sql — RFM segmentation (Recency / Frequency / Monetary)
-- Scores 1–5 per dimension using NTILE, then maps to business-readable segments.
-- Reference date = 2026-06-30 (the data cut-off).
-- ===================================================================================

-- name: rfm_summary
-- Size and value each segment: "who are they, how many, how much GMV do they carry?"
--
-- SEGMENT DEFINITION: segments are cut on RECENCY x FREQUENCY only. Monetary is
-- reported per segment (gmv_lakh, avg_lifetime_gmv) but is deliberately NOT part of the
-- segment rule, because in food delivery M is largely a function of F -- more orders
-- means more spend -- so scoring on both double-counts the same behaviour and produces
-- segments that are hard to act on. R and F answer the two questions a growth team can
-- actually do something about: are they still here, and how often do they order?
--
-- NTILE(5) OVER (ORDER BY recency_days DESC): recency_days is "days since last order",
-- so DESC puts the LARGEST gap first -- meaning tile 1 = most lapsed, tile 5 = most
-- recent. Higher r_score = better, which is what the CASE below assumes.
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
WITH per_user AS (              -- one row per user who has ever ordered
    SELECT u.user_id, u.acquisition_channel,
           COUNT(o.order_id)  AS orders,
           SUM(o.gmv)         AS gmv,
           SUM(o.discount)    AS discount
    FROM users u
    JOIN orders o ON o.user_id = u.user_id AND o.status='delivered'
    GROUP BY 1,2
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
