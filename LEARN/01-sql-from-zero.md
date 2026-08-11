# SQL from zero — taught on your own data

You do not need to learn "SQL" in the abstract. You need to read and write the ~15
constructs that appear in this project. That is a genuinely small list, and it is the
same list that covers most Product Analyst interview questions.

**How to use this file:** type every query into the scratchpad and look at the output.
Typing, not reading, is what makes it stick.

```bash
python3 src/sql.py "SELECT * FROM orders LIMIT 5"
```

Or open an interactive session and just keep typing:

```bash
python3 src/sql.py
```

---

## Part 0 — What a database actually is

Four spreadsheets that know how to reference each other. That's it.

| table | one row = | key columns |
|---|---|---|
| `users` | one registered user | `user_id`, `signup_date`, `city`, `platform`, `acquisition_channel`, `is_member` |
| `orders` | one order | `order_id`, `user_id`, `order_ts`, `gmv`, `is_late`, `delivery_minutes`, `status` |
| `app_events` | one session doing one funnel step | `session_id`, `user_id`, `event_name`, `step_no` |
| `ab_test_assignments` | one user in the experiment | `user_id`, `variant`, `repeat_within_14d` |

The phrase **"one row = ..."** is called the **grain** of the table, and it is the single
most important thing to know about any table. Most wrong answers in SQL interviews come
from forgetting the grain — e.g. counting rows in `orders` and calling it "users".

See it yourself:

```bash
python3 src/sql.py --tables
```

`user_id` appears in all four tables. That shared column is what lets you connect them —
that's a **join key**.

---

## Part 1 — SELECT, FROM, LIMIT

The two words every query needs: **what columns** (`SELECT`) and **from which table**
(`FROM`).

```sql
SELECT city, gmv, is_late
FROM orders
LIMIT 5;
```

- `SELECT city, gmv, is_late` — give me these three columns
- `FROM orders` — out of the orders table
- `LIMIT 5` — just the first 5 rows, so you don't print 71,599 of them

`SELECT *` means "every column". Useful for looking around, bad in real queries — it
drags data you don't need.

```sql
SELECT * FROM users LIMIT 3;
```

---

## Part 2 — WHERE: keeping only some rows

`WHERE` filters **rows**. (`SELECT` picks columns, `WHERE` picks rows.)

```sql
SELECT order_id, city, gmv
FROM orders
WHERE city = 'Bengaluru'
LIMIT 5;
```

Note: **single quotes** for text in SQL, not double. Numbers need no quotes.

Combine conditions with `AND` / `OR`:

```sql
SELECT order_id, city, gmv, is_late
FROM orders
WHERE city = 'Bengaluru'
  AND is_late = 1
  AND gmv > 500
LIMIT 5;
```

Other useful filters:

```sql
WHERE status != 'cancelled'              -- not equal
WHERE city IN ('Mumbai', 'Pune')         -- one of a list
WHERE gmv BETWEEN 300 AND 600            -- inclusive range
WHERE rating IS NULL                     -- missing value (never use "= NULL")
```

> **Why `is_late = 1` and not `is_late = TRUE`?** SQLite stores booleans as 0/1. A column
> that is 0-or-1 is handy: its **average is the rate**. `AVG(is_late)` = the share of
> orders that were late. You'll use that trick constantly.

**Exercise 1.** How many orders in Mumbai were cancelled? *(Answer at the bottom.)*

---

## Part 3 — Aggregation: COUNT, SUM, AVG, and GROUP BY

Aggregate functions squash many rows into one number.

```sql
SELECT COUNT(*)      AS total_orders,
       SUM(gmv)      AS total_gmv,
       AVG(gmv)      AS aov,
       MIN(gmv)      AS smallest,
       MAX(gmv)      AS biggest
FROM orders
WHERE status = 'delivered';
```

- `COUNT(*)` — how many rows
- `AS aov` — renames the output column. Always name your columns; unnamed output is
  unreadable in a review.

**`COUNT(DISTINCT x)`** counts unique values, and the difference matters enormously:

```sql
SELECT COUNT(*)                  AS orders,
       COUNT(DISTINCT user_id)   AS ordering_users
FROM orders;
```

71,599 orders but only ~40,000 users — because users place multiple orders. Confusing
those two is the single most common analytics mistake, and it is exactly the second-order
problem your project is about.

### GROUP BY — "per something"

Any time you say the word **"per"** or **"by"** in English, you need `GROUP BY`.

```sql
SELECT city,
       COUNT(*)                        AS orders,
       ROUND(AVG(gmv), 0)              AS aov,
       ROUND(100.0 * AVG(is_late), 1)  AS late_rate_pct
FROM orders
WHERE status = 'delivered'
GROUP BY city
ORDER BY late_rate_pct DESC;
```

Read it as: *split the rows into one bucket per city, then compute those numbers inside
each bucket.*

- `ROUND(x, 1)` — 1 decimal place
- `100.0 * AVG(is_late)` — turns the 0-to-1 rate into a percentage.
  **Use `100.0`, not `100`** — integer division silently truncates and you get 0.
- `ORDER BY late_rate_pct DESC` — sort descending (`ASC` is the default)

**The rule:** every column in `SELECT` must either be inside an aggregate function or
listed in `GROUP BY`. If you break it, the database either errors or invents an answer.

### HAVING — filtering *after* grouping

```sql
SELECT city, COUNT(*) AS orders
FROM orders
GROUP BY city
HAVING COUNT(*) > 10000;
```

`WHERE` filters rows **before** grouping; `HAVING` filters groups **after**. That's the
whole difference, and it's a classic interview question.

**Exercise 2.** Average order value and order count per `acquisition_channel`. (Careful:
which table is that column in?)

---

## Part 4 — CASE WHEN: if/else inside a query

`CASE` builds a new column from a condition — the SQL version of an if-statement.

```sql
SELECT CASE WHEN is_late = 1 THEN 'Late'
            ELSE 'On time' END        AS delivery_status,
       COUNT(*)                       AS orders,
       ROUND(AVG(rating), 2)          AS avg_rating
FROM orders
WHERE status = 'delivered'
GROUP BY 1;
```

`GROUP BY 1` means "group by the 1st column in the SELECT list" — a shorthand you'll see
everywhere, including in this project's SQL.

Bucketing a number into bands is the same idea, and it's how the dose–response table in
`sql/05_drivers.sql` is built:

```sql
SELECT CASE
         WHEN delivery_minutes - promised_minutes <= 0  THEN '1. Early / on time'
         WHEN delivery_minutes - promised_minutes <= 10 THEN '2. 0-10 min late'
         WHEN delivery_minutes - promised_minutes <= 20 THEN '3. 10-20 min late'
         ELSE                                                '4. 20+ min late'
       END                              AS lateness_bucket,
       COUNT(*)                         AS orders,
       ROUND(AVG(rating), 2)            AS avg_rating
FROM orders
WHERE status = 'delivered'
GROUP BY 1
ORDER BY 1;
```

`CASE` checks conditions **in order** and stops at the first match — so the bands must go
smallest to largest or they'll overlap.

### The `CASE` + `AVG` trick (learn this one properly)

```sql
SELECT ROUND(100.0 * AVG(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 2)
       AS cancel_rate_pct
FROM orders;
```

Turn a condition into 1s and 0s, then average it → you get a **rate**. This is how you
compute "% of X that are Y" in one pass, and it's used all over `sql/`.

> **A bug worth knowing:** if you write `THEN 1` and forget `ELSE 0`, non-matching rows
> become `NULL`, and `AVG` *ignores* `NULL`s — so you get 100% every time. I made exactly
> this mistake while building `sql/01_metrics.sql`. If a rate comes out suspiciously
> round, check for a missing `ELSE 0`.

**Exercise 3.** For each `platform`, what share of orders were late? Output as a
percentage, one decimal place.

---

## Part 5 — JOIN: combining two tables

`orders` doesn't have `acquisition_channel`; `users` does. A **join** stitches them
together on the shared `user_id`.

```sql
SELECT u.acquisition_channel,
       COUNT(*)                AS orders,
       ROUND(AVG(o.gmv), 0)    AS aov
FROM orders o
JOIN users u ON u.user_id = o.user_id
WHERE o.status = 'delivered'
GROUP BY 1
ORDER BY orders DESC;
```

- `FROM orders o` — `o` is an **alias**, a nickname, so you can write `o.gmv` instead of
  `orders.gmv`
- `JOIN users u ON u.user_id = o.user_id` — pair each order with its user's row
- Once tables are joined, prefix columns with the alias so it's obvious where each came from

**The two joins you need:**

| join | keeps | use it when |
|---|---|---|
| `JOIN` (inner) | only rows that match in **both** tables | you want orders *and* their user |
| `LEFT JOIN` | **all** rows from the left table; `NULL` where no match | you want *all users*, including those who never ordered |

That distinction is a favourite interview question, and it matters here: your activation
rate (67%) needs a `LEFT JOIN` from `users`, because the whole point is the users with
**no** orders.

```sql
SELECT COUNT(*)                                          AS all_users,
       COUNT(o.user_id)                                  AS users_who_ordered,
       ROUND(100.0 * COUNT(o.user_id) / COUNT(*), 1)     AS activation_pct
FROM users u
LEFT JOIN (SELECT DISTINCT user_id FROM orders) o
       ON o.user_id = u.user_id;
```

Note `COUNT(*)` vs `COUNT(o.user_id)`: `COUNT(*)` counts every row, `COUNT(column)`
counts only **non-NULL** values — so it counts exactly the matched users. That is a real
technique, not a trick.

> That query returns **68.6%**, but your report says **67.3%**. Not a contradiction — the
> report counts only users with a *delivered* order, this one counts anyone who placed an
> order at all, including cancelled ones. **Both are right; they answer different
> questions.** Being able to say exactly that, calmly, when an interviewer points at two
> numbers that don't match is worth more than either number. Definitions are the job.

**Exercise 4.** Do Members (`is_member = 1`) have a higher average order value than
non-members?

---

## Part 6 — WITH (CTEs): breaking a hard query into steps

A **CTE** ("common table expression") is a named temporary result you build first and use
after. It is the single most important habit for writing readable SQL, and every complex
query in this project uses one.

Think of it as: *"first work out X, then use X."*

```sql
WITH first_order AS (            -- STEP 1: each user's first order date
    SELECT user_id,
           MIN(order_ts) AS first_ts
    FROM orders
    WHERE status = 'delivered'
    GROUP BY user_id
)
SELECT COUNT(*) AS users,
       MIN(first_ts) AS earliest,
       MAX(first_ts) AS latest
FROM first_order;                -- STEP 2: use it like a table
```

`MIN(order_ts)` per user = that user's **first** order. This "first event per user"
pattern is the backbone of all cohort and retention analysis — learn it cold.

### Chaining CTEs, and the "join back" pattern

To find *properties* of the first order (was it late? how big?) you need a second step:
get the first timestamp, then join back to `orders` to fetch that specific row.

```sql
WITH first_order AS (
    SELECT user_id, MIN(order_ts) AS first_ts
    FROM orders WHERE status = 'delivered'
    GROUP BY user_id
),
first_details AS (                      -- STEP 2: join back for that row's columns
    SELECT f.user_id,
           f.first_ts,
           o.gmv     AS first_gmv,
           o.is_late AS first_was_late
    FROM first_order f
    JOIN orders o
      ON o.user_id = f.user_id
     AND o.order_ts = f.first_ts        -- the join condition pins it to the FIRST order
)
SELECT CASE first_was_late WHEN 1 THEN 'Late' ELSE 'On time' END AS first_delivery,
       COUNT(*)             AS users,
       ROUND(AVG(first_gmv), 0) AS avg_first_order_value
FROM first_details
GROUP BY 1;
```

**You have just written the skeleton of your project's headline finding.** Open
`sql/05_drivers.sql` and you'll recognise the shape: same two CTEs, plus a third that
checks whether a second order followed within 30 days.

**Exercise 5.** Extend the query above to also show the average `rating` of the first
order for each group. Does a late first delivery get rated worse?

---

## Part 7 — Dates, and window functions

### Dates in SQLite

Timestamps here are text like `'2026-03-14 20:31:00'`. Three functions do everything:

```sql
SELECT STRFTIME('%Y-%m', order_ts)            AS month,      -- '2026-03'
       STRFTIME('%H',    order_ts)            AS hour,       -- '20'
       CAST(STRFTIME('%H', order_ts) AS INT)  AS hour_num,   -- 20  (a number)
       JULIANDAY('2026-06-30') - JULIANDAY(order_ts) AS days_ago
FROM orders
LIMIT 5;
```

- `STRFTIME('%Y-%m', ...)` — format a timestamp. `%Y`=year, `%m`=month, `%d`=day, `%H`=hour.
- `CAST(x AS INT)` — text to number, so you can compare with `BETWEEN 19 AND 22`.
- `JULIANDAY(a) - JULIANDAY(b)` — **number of days between two timestamps**. This is how
  "did they order again within 30 days?" is computed throughout the project.

Monthly trend, which is chart 1 of your project:

```sql
SELECT STRFTIME('%Y-%m', order_ts)  AS month,
       COUNT(*)                     AS orders,
       ROUND(AVG(gmv), 0)           AS aov
FROM orders
WHERE status = 'delivered'
GROUP BY 1
ORDER BY 1;
```

### Window functions

A window function computes across **other rows** without collapsing your result into one
row per group. Syntax: `FUNCTION() OVER (...)`.

**`LAG` — the previous row.** Used for "compared to last month" and for funnel step
conversion:

```sql
SELECT STRFTIME('%Y-%m', order_ts)                     AS month,
       COUNT(*)                                        AS orders,
       LAG(COUNT(*)) OVER (ORDER BY STRFTIME('%Y-%m', order_ts)) AS prev_month,
       ROUND(100.0 * COUNT(*)
             / LAG(COUNT(*)) OVER (ORDER BY STRFTIME('%Y-%m', order_ts)) - 100, 1)
                                                       AS growth_pct
FROM orders
WHERE status = 'delivered'
GROUP BY 1 ORDER BY 1;
```

The first row's `prev_month` is `NULL` — there's nothing before it. That's correct, not a
bug, and you should say so if asked.

**`SUM(...) OVER ()` — a total on every row**, so you can compute a share:

```sql
SELECT city,
       COUNT(*)                                            AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)  AS pct_of_all_orders
FROM orders
GROUP BY city
ORDER BY orders DESC;
```

**`NTILE(5)` — split rows into 5 equal-sized buckets**, which is exactly how RFM scoring
works in `sql/04_segmentation.sql`:

```sql
WITH per_user AS (
    SELECT user_id, COUNT(*) AS frequency, SUM(gmv) AS monetary
    FROM orders WHERE status = 'delivered'
    GROUP BY user_id
)
SELECT user_id, frequency, monetary,
       NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
       NTILE(5) OVER (ORDER BY monetary  ASC) AS m_score
FROM per_user
LIMIT 10;
```

`NTILE(5)` sorts everyone by frequency and hands out scores 1–5, each bucket holding 20%
of users. Score 5 = top 20%.

**`PARTITION BY` — restart the window per group:**

```sql
LAG(sessions) OVER (PARTITION BY platform ORDER BY step_no)
```

= "the previous step's session count, **within this platform**". That's the line that
produces the Android-vs-iOS funnel comparison in `sql/03_funnel.sql`.

**Exercise 6.** Using `NTILE(5)`, find the average lifetime GMV of the top 20% of users by
spend. What share of total GMV do they account for?

---

## Part 8 — Cheat sheet

**Order the database actually executes things** (not the order you write them):

```
FROM → JOIN → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT
```

This explains two things that confuse everyone:
- Why `WHERE` can't use an alias defined in `SELECT` (the `SELECT` hasn't run yet).
- Why `HAVING` can use aggregates but `WHERE` cannot.

| I want to... | I use |
|---|---|
| pick columns | `SELECT a, b` |
| pick rows | `WHERE x = 'y'` |
| count rows / unique things | `COUNT(*)` / `COUNT(DISTINCT user_id)` |
| a rate or "% of rows where..." | `AVG(CASE WHEN cond THEN 1 ELSE 0 END)` |
| per-something numbers | `GROUP BY something` |
| filter *after* aggregating | `HAVING COUNT(*) > 100` |
| if/else | `CASE WHEN ... THEN ... ELSE ... END` |
| add columns from another table | `JOIN other o ON o.id = t.id` |
| keep unmatched rows too | `LEFT JOIN` |
| build a query in steps | `WITH step1 AS (...), step2 AS (...)` |
| each user's first event | `MIN(ts)` in a CTE, then join back on `ts` |
| days between two timestamps | `JULIANDAY(a) - JULIANDAY(b)` |
| bucket to a month | `STRFTIME('%Y-%m', ts)` |
| previous row's value | `LAG(x) OVER (ORDER BY ...)` |
| a share of the total | `x / SUM(x) OVER ()` |
| quintile / rank buckets | `NTILE(5) OVER (ORDER BY x)` |
| restart a window per group | `... OVER (PARTITION BY g ORDER BY ...)` |

**Debugging habits that save interviews:**
1. Build in layers — run the first CTE alone, look at it, *then* add the next.
2. Sanity-check the row count after every join. If it grew, your join key isn't unique
   and you are double-counting. (This is *the* classic bug.)
3. Say the grain out loud before you write: "one row per user per month."
4. If a percentage looks impossible, suspect integer division (`100` vs `100.0`) or a
   missing `ELSE 0`.

---

## Part 9 — Now read your own project

In this order. You have seen every construct in them:

1. `sql/01_metrics.sql` — CTEs, `AVG(CASE...)`, `JULIANDAY` date maths
2. `sql/04_segmentation.sql` — `NTILE`, `SUM() OVER ()`, big `CASE` blocks
3. `sql/03_funnel.sql` — `LAG` with `PARTITION BY`, pivoting with `MAX(CASE WHEN...)`
4. `sql/02_cohort_retention.sql` — the first-event pattern plus month arithmetic
5. `sql/05_drivers.sql` — everything at once, plus stratification

Run any of them instantly, with the SQL printed above the result:

```bash
python3 src/sql.py --block cohort_matrix
python3 src/sql.py --block funnel_overall
python3 src/sql.py --block rfm_summary
```

**When you can read all five and explain what each CTE is for, you can defend the project.**

---

## Exercise answers

```bash
# 1
python3 src/sql.py "SELECT COUNT(*) AS cancelled_mumbai FROM orders WHERE city='Mumbai' AND status='cancelled'"

# 2  (acquisition_channel lives in users, so you must join)
python3 src/sql.py "
SELECT u.acquisition_channel, COUNT(*) AS orders, ROUND(AVG(o.gmv),0) AS aov
FROM orders o JOIN users u ON u.user_id = o.user_id
WHERE o.status='delivered' GROUP BY 1 ORDER BY aov DESC"

# 3
python3 src/sql.py "
SELECT platform, ROUND(100.0*AVG(is_late),1) AS late_pct
FROM orders WHERE status='delivered' GROUP BY 1"

# 4
python3 src/sql.py "
SELECT u.is_member, COUNT(*) AS orders, ROUND(AVG(o.gmv),0) AS aov
FROM orders o JOIN users u ON u.user_id=o.user_id
WHERE o.status='delivered' GROUP BY 1"

# 5
python3 src/sql.py "
WITH fo AS (SELECT user_id, MIN(order_ts) AS first_ts FROM orders WHERE status='delivered' GROUP BY user_id),
fd AS (SELECT f.user_id, o.gmv AS first_gmv, o.is_late, o.rating
       FROM fo f JOIN orders o ON o.user_id=f.user_id AND o.order_ts=f.first_ts)
SELECT CASE is_late WHEN 1 THEN 'Late' ELSE 'On time' END AS first_delivery,
       COUNT(*) AS users, ROUND(AVG(first_gmv),0) AS avg_gmv, ROUND(AVG(rating),2) AS avg_rating
FROM fd GROUP BY 1"

# 6
python3 src/sql.py "
WITH per_user AS (SELECT user_id, SUM(gmv) AS monetary FROM orders WHERE status='delivered' GROUP BY user_id),
scored AS (SELECT *, NTILE(5) OVER (ORDER BY monetary ASC) AS m_score FROM per_user)
SELECT m_score, COUNT(*) AS users, ROUND(AVG(monetary),0) AS avg_lifetime_gmv,
       ROUND(100.0*SUM(monetary)/SUM(SUM(monetary)) OVER (),1) AS pct_of_gmv
FROM scored GROUP BY 1 ORDER BY 1"
```
