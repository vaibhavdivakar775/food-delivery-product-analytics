-- ===================================================================================
-- 05_drivers.sql — What actually drives the 2nd order?
-- The whole project hinges on this file, so it is deliberately careful:
--   (a) a raw comparison,
--   (b) the same comparison STRATIFIED by the obvious confounders (city, channel,
--       membership, platform) so we are not just re-discovering "Bengaluru has bad traffic
--       AND different users",
--   (c) a dose-response check (more minutes late -> lower repeat rate).
-- If an effect survives stratification and shows a dose-response, it is worth acting on.
-- ===================================================================================

-- name: first_order_features
-- One row per activated user = the modelling/analysis table for the repeat question.
WITH firsts AS (
    SELECT user_id, MIN(order_ts) AS first_ts
    FROM orders WHERE status='delivered' GROUP BY user_id
),
fo AS (
    SELECT f.user_id, f.first_ts, o.order_id AS first_order_id,
           o.city, o.platform, o.cuisine, o.gmv AS first_gmv, o.discount AS first_discount,
           o.delivery_minutes, o.promised_minutes, o.is_late, o.rating,
           CAST(STRFTIME('%H', o.order_ts) AS INT) AS first_hour
    FROM firsts f
    JOIN orders o ON o.user_id = f.user_id AND o.order_ts = f.first_ts
),
repeat_flag AS (
    SELECT fo.user_id,
           MAX(CASE WHEN o.order_ts > fo.first_ts
                     AND JULIANDAY(o.order_ts) - JULIANDAY(fo.first_ts) <= 30
                    THEN 1 ELSE 0 END) AS repeated_30d
    FROM fo JOIN orders o ON o.user_id = fo.user_id AND o.status='delivered'
    GROUP BY fo.user_id
)
SELECT fo.*, u.acquisition_channel, u.is_member, r.repeated_30d,
       ROUND(fo.delivery_minutes - fo.promised_minutes, 1) AS minutes_late
FROM fo
JOIN users u  ON u.user_id = fo.user_id
JOIN repeat_flag r ON r.user_id = fo.user_id
WHERE JULIANDAY('2026-06-30') - JULIANDAY(fo.first_ts) >= 30;   -- matured cohorts only


-- name: repeat_by_late
SELECT CASE is_late WHEN 1 THEN 'Late' ELSE 'On time' END AS first_delivery,
       COUNT(*)                                           AS users,
       ROUND(100.0 * AVG(repeated_30d), 2)                AS repeat_30d_pct
FROM ({first_order_features})
GROUP BY 1 ORDER BY 1;


-- name: repeat_by_late_stratified
-- Same effect, held constant within city x channel x membership x platform cells.
-- We then weight each cell by its size to get an adjusted overall gap.
WITH f AS ({first_order_features}),
cells AS (
    SELECT city, acquisition_channel, is_member, platform,
           SUM(CASE WHEN is_late=1 THEN 1 ELSE 0 END)                       AS n_late,
           SUM(CASE WHEN is_late=0 THEN 1 ELSE 0 END)                       AS n_ontime,
           AVG(CASE WHEN is_late=1 THEN 1.0*repeated_30d END)               AS p_late,
           AVG(CASE WHEN is_late=0 THEN 1.0*repeated_30d END)               AS p_ontime
    FROM f
    GROUP BY 1,2,3,4
    HAVING n_late >= 20 AND n_ontime >= 20            -- drop unstable cells
)
SELECT COUNT(*)                                                        AS cells_used,
       SUM(n_late + n_ontime)                                          AS users_covered,
       ROUND(100.0 * SUM((p_ontime - p_late) * (n_late + n_ontime))
                   / SUM(n_late + n_ontime), 2)                        AS adjusted_gap_pp,
       ROUND(100.0 * SUM(p_ontime * (n_late+n_ontime)) / SUM(n_late+n_ontime), 2) AS wtd_ontime_pct,
       ROUND(100.0 * SUM(p_late   * (n_late+n_ontime)) / SUM(n_late+n_ontime), 2) AS wtd_late_pct
FROM cells;


-- name: dose_response
-- Does *more* lateness hurt *more*? The answer here is a THRESHOLD, not a smooth slope:
-- flat for the first 10 minutes, then a step down, then roughly flat again. A threshold
-- that lands exactly where the promised ETA was broken is strong evidence the
-- relationship is real and not an artifact of who happens to get late orders.
SELECT CASE
         WHEN minutes_late <= 0  THEN '1. Early / on time'
         WHEN minutes_late <= 10 THEN '2. 0-10 min late'
         WHEN minutes_late <= 20 THEN '3. 10-20 min late'
         WHEN minutes_late <= 30 THEN '4. 20-30 min late'
         ELSE                        '5. 30+ min late'
       END                                     AS lateness_bucket,
       COUNT(*)                                AS users,
       ROUND(AVG(rating), 2)                   AS avg_first_rating,
       ROUND(100.0 * AVG(repeated_30d), 2)     AS repeat_30d_pct
FROM ({first_order_features})
GROUP BY 1 ORDER BY 1;


-- name: repeat_by_segment
-- Every other candidate driver, ranked, so we can say "lateness is the biggest one".
WITH f AS ({first_order_features})
SELECT 'city'    AS dimension, city    AS value, COUNT(*) AS users,
       ROUND(100.0*AVG(repeated_30d),2) AS repeat_pct FROM f GROUP BY 2
UNION ALL
SELECT 'channel', acquisition_channel, COUNT(*), ROUND(100.0*AVG(repeated_30d),2) FROM f GROUP BY 2
UNION ALL
SELECT 'platform', platform, COUNT(*), ROUND(100.0*AVG(repeated_30d),2) FROM f GROUP BY 2
UNION ALL
SELECT 'member', CASE is_member WHEN 1 THEN 'Member' ELSE 'Non-member' END,
       COUNT(*), ROUND(100.0*AVG(repeated_30d),2) FROM f GROUP BY 2
UNION ALL
SELECT 'first_rating', CASE WHEN rating >= 4.5 THEN '4.5-5.0'
                            WHEN rating >= 3.5 THEN '3.5-4.0' ELSE '<3.5' END,
       COUNT(*), ROUND(100.0*AVG(repeated_30d),2) FROM f GROUP BY 2
ORDER BY dimension, repeat_pct DESC;


-- name: late_by_city_hour
-- WHERE is the lateness concentrated? (This is what Ops can actually act on.)
SELECT city,
       CASE WHEN CAST(STRFTIME('%H', order_ts) AS INT) BETWEEN 12 AND 14 THEN 'Lunch peak'
            WHEN CAST(STRFTIME('%H', order_ts) AS INT) BETWEEN 19 AND 22 THEN 'Dinner peak'
            ELSE 'Off peak' END                    AS daypart,
       COUNT(*)                                    AS orders,
       ROUND(100.0 * AVG(is_late), 1)              AS late_rate_pct,
       ROUND(AVG(delivery_minutes), 1)             AS avg_minutes
FROM orders WHERE status='delivered'
GROUP BY 1,2
ORDER BY late_rate_pct DESC;
