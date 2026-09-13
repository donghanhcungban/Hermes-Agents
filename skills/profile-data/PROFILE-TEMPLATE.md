# Profiling Query Template

Pseudo-SQL scaffolds for each profiling section in the skill, plus the
baseline report shape. 

These are **tool-agnostic skeletons**, not runnable code. Substitute your
engine's functions (consult `docs/agents/platform.md` if present) and replace
`{{table}}` / `{{col}}` / `{{key}}` placeholders. Run each section in order.

---

## 1. Shape

```sql
-- row count (+ per partition if partitioned)
SELECT COUNT(*) AS row_count FROM {{table}};
SELECT {{partition_col}}, COUNT(*) FROM {{table}} GROUP BY {{partition_col}} ORDER BY 1;

-- declared schema; eyeball types + string caps
-- (information_schema.columns, or DESCRIBE {{table}}, per engine)
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = '{{table}}';

-- truncation trap: real max length vs declared cap, per string column
SELECT MAX(LENGTH({{col}})) AS observed_max_len FROM {{table}};
```

## 2. Cardinality

```sql
SELECT
  COUNT(*)                                              AS total,
  COUNT(DISTINCT {{col}})                               AS distinct_vals,
  ROUND(COUNT(DISTINCT {{col}}) * 100.0 / NULLIF(COUNT(*), 0), 2) AS distinct_pct
FROM {{table}};
-- distinct_pct ~100 -> candidate key; ~0 -> constant/low-signal;
-- mid-range -> categorical (capture the value set for accepted-values tests)
```

## 3. Key uniqueness (make-or-break)

```sql
-- must hold: COUNT(*) = COUNT(DISTINCT key). Surface a failure and STOP.
SELECT
  COUNT(*)                       AS rows,
  COUNT(DISTINCT {{key}})        AS distinct_keys,
  COUNT(*) - COUNT(DISTINCT {{key}}) AS dup_keys
FROM {{table}};

-- which keys duplicate (for the surfaced report)
SELECT {{key}}, COUNT(*) AS n
FROM {{table}}
GROUP BY {{key}}
HAVING COUNT(*) > 1
ORDER BY n DESC;

-- a nullable key is not a key
SELECT COUNT(*) AS null_keys FROM {{table}} WHERE {{key}} IS NULL;
```

For a composite key, `GROUP BY col_a, col_b, ...` and apply the same checks.

## 4. Completeness

```sql
SELECT
  COUNT(*)                                          AS total,
  COUNT(*) - COUNT({{col}})                         AS null_count,
  ROUND((COUNT(*) - COUNT({{col}})) * 100.0 / NULLIF(COUNT(*),0), 2) AS null_pct,
  SUM(CASE WHEN TRIM({{col}}) = '' THEN 1 ELSE 0 END)              AS empty_string,
  SUM(CASE WHEN UPPER(TRIM({{col}})) IN ('N/A','NULL','-','NONE','UNKNOWN')
          THEN 1 ELSE 0 END)                        AS sentinel_count
FROM {{table}};
-- decide per column: is null expected, or a defect?
```

## 5. Distribution & outliers

```sql
-- numeric: spread + impossible values
SELECT
  MIN({{col}}) AS min_v,
  MAX({{col}}) AS max_v,
  AVG({{col}}) AS mean_v,
  -- quartiles: APPROX_PERCENTILE / PERCENTILE_CONT per engine
  APPROX_PERCENTILE({{col}}, 0.25) AS p25,
  APPROX_PERCENTILE({{col}}, 0.50) AS median,
  APPROX_PERCENTILE({{col}}, 0.75) AS p75
FROM {{table}};

-- flag impossibles (negative ages, future dates, etc.)
SELECT COUNT(*) AS impossible FROM {{table}}
WHERE {{col}} < 0 OR {{date_col}} > CURRENT_DATE;
```

> Use null-safe comparison (`IS DISTINCT FROM` / your dialect's equivalent)
> whenever NULLs are in play.

## 6. Types, formats, sensitivity

```sql
-- regex-scan for PII patterns; classify by sensitivity
SELECT
  SUM(CASE WHEN {{col}} ~ '^[^@]+@[^@]+\.[^@]+$' THEN 1 ELSE 0 END) AS looks_like_email,
  SUM(CASE WHEN {{col}} ~ '^\+?[0-9 ()-]{7,}$'    THEN 1 ELSE 0 END) AS looks_like_phone
FROM {{table}};
-- also confirm date formats, timezones, numeric precision match assumptions
```

---

## 7. Baseline report shape (`docs/profiles/<table>.md`)

Write this **only with the user's consent**. Aggregates only — never sample
rows or record-level values. PII columns (flagged in step 6) get statistics
only: no observed value sets, no min/max for free-text identifiers.

```markdown
# Profile: <table>

Profiled-at: 2026-01-15
Source: <where this data came from>
Verdict: safe to build on  |  not yet (keys fail / anomalies)

## Shape
- Rows: 1,240,318
- Columns: 24
- Partitioned by: load_date (≈ 4,100 rows/day)

## Candidate keys
| Key            | Unique? | Nullable? | Notes                       |
|----------------|---------|-----------|-----------------------------|
| order_id       | PASS    | no        | use as business key         |
| (order_id, ln) | PASS    | no        | grain = one row per line     |

## Cardinality & completeness
| Column     | Distinct% | Null% | Classification        |
|------------|-----------|-------|-----------------------|
| status     | 0.004     | 0     | categorical (6 values)|
| email      | 98.2      | 1.1   | PII — stats only      |

## Accepted value sets (non-PII categoricals)
- status: active, cancelled, pending, refunded, shipped, returned

## Distributions (non-PII numerics)
| Column      | Min | P25 | Median | P75 | Max   |
|-------------|-----|-----|--------|-----|-------|
| order_total | 0   | 18  | 42     | 96  | 9,940 |

## Anomalies found
- 312 rows with order_total = 0 (refunds?) — confirm with business
- email observed max length 254 vs declared VARCHAR(255) — near cap

## Columns that need tests
- order_id: uniqueness (error), not-null (error)
- status: accepted_values (warn)
- order_total: non-negative (error), volume/variance vs this baseline (warn)
```

This baseline is what `test-data` (if installed) turns into volume/variance
thresholds, and what drift detection diffs against on the next load.
