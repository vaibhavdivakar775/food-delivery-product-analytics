-- ===================================================================================
-- 06_ab_test.sql — Experiment readout: "Next-Order Nudge"
--   Hypothesis: sending a ₹75-off coupon valid 7 days, immediately after a user's
--   FIRST delivered order, increases the share who order again within 14 days.
--   Unit of randomisation: user (assigned at first-order completion). 50/50 split.
-- The statistics (z-test, CI, power) live in Python; SQL produces the clean inputs.
-- ===================================================================================

-- name: srm_check
-- SAMPLE RATIO MISMATCH check — ALWAYS run this before reading any result.
-- If the observed split is far from 50/50, the assignment or logging is broken and
-- the whole experiment is untrustworthy, no matter how good the lift looks.
SELECT variant, COUNT(*) AS users,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM ab_test_assignments
GROUP BY variant;


-- name: ab_balance
-- Pre-experiment balance: the two arms should look alike on things decided BEFORE
-- assignment (first-order GMV, lateness, city). If not, randomisation is suspect.
SELECT a.variant,
       COUNT(*)                                    AS users,
       ROUND(AVG(o.gmv), 1)                        AS first_order_aov,
       ROUND(100.0 * AVG(o.is_late), 2)            AS first_late_pct,
       ROUND(AVG(o.rating), 3)                     AS first_rating
FROM ab_test_assignments a
JOIN orders o ON o.order_id = a.first_order_id
GROUP BY a.variant;


-- name: ab_primary
-- PRIMARY metric: repeat order within 14 days of the first order.
SELECT variant,
       COUNT(*)                                  AS n,
       SUM(repeat_within_14d)                    AS conversions,
       ROUND(100.0 * AVG(repeat_within_14d), 3)  AS repeat_14d_pct
FROM ab_test_assignments
GROUP BY variant;


-- name: ab_guardrails
-- GUARDRAILS: a win on the primary metric is not a ship decision on its own.
--   1. AOV of the 2nd order — did the coupon make people trade down?
--   2. Cancellation rate of the 2nd order — did we buy junk orders?
--   3. Coupon cost per incremental order — is it worth it?
SELECT variant,
       COUNT(*)                                                   AS n,
       ROUND(AVG(second_order_aov), 1)                            AS second_order_aov,
       ROUND(100.0 * AVG(second_order_cancelled), 2)              AS second_cancel_pct,
       ROUND(SUM(coupon_cost), 0)                                 AS total_coupon_cost
FROM ab_test_assignments
GROUP BY variant;


-- name: ab_by_segment
-- Heterogeneous treatment effects: is the nudge worth sending to EVERYONE, or only
-- to the users whose first delivery went badly? (Targeting beats blanket discounting.)
SELECT CASE o.is_late WHEN 1 THEN 'First delivery LATE' ELSE 'First delivery ON TIME' END AS segment,
       a.variant,
       COUNT(*)                                   AS n,
       SUM(a.repeat_within_14d)                   AS conversions,
       ROUND(100.0 * AVG(a.repeat_within_14d), 2) AS repeat_14d_pct
FROM ab_test_assignments a
JOIN orders o ON o.order_id = a.first_order_id
GROUP BY 1, 2
ORDER BY 1, 2;
