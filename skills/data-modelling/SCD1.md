# SCD Type 1 — Overwrite (Snowflake)

Type 1 overwrites the old value in place. No history is kept. Choose it
**per attribute** when no one needs the prior value (e.g. a corrected typo in
a name). Kimball's caveat: an overwrite silently invalidates pre-built
aggregates and makes the *same* historical report return different totals
before vs. after — fine for a genuine correction, dangerous if anyone relies
on point-in-time consistency. When in doubt whether history matters, it's
SCD2 (see [scd2.md](./scd2.md)).

## Shape

A Type 1 dimension has one row per durable business key, a surrogate key, and
no validity columns:

```sql
CREATE TABLE IF NOT EXISTS DIM_CUSTOMER (
    CUSTOMER_SK     NUMBER       IDENTITY,      -- surrogate key
    CUSTOMER_BK     VARCHAR      NOT NULL,      -- natural/business key
    CUSTOMER_NAME   VARCHAR,
    EMAIL           VARCHAR,
    REGION          VARCHAR,
    LOAD_TS         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT UK_DIM_CUSTOMER_BK UNIQUE (CUSTOMER_BK)
);
```

Always include an "unknown"/ghost row (SK `-1`) so facts never drop on join:

```sql
INSERT INTO DIM_CUSTOMER (CUSTOMER_SK, CUSTOMER_BK, CUSTOMER_NAME, REGION)
SELECT -1, '-1', 'Unknown', 'Unknown'
WHERE NOT EXISTS (SELECT 1 FROM DIM_CUSTOMER WHERE CUSTOMER_SK = -1);
```

## Load — MERGE (upsert)

The canonical Type 1 load is a `MERGE`. Use **null-safe** comparison so a
change to/from NULL is detected; in Snowflake, two values are
distinct-aware via `IS DISTINCT FROM` (or the `<=>`-style equivalent through
`EQUAL_NULL`). Only update when something actually changed, to avoid churning
`LOAD_TS` on unchanged rows.

```sql
MERGE INTO DIM_CUSTOMER tgt
USING STG_CUSTOMER src
   ON tgt.CUSTOMER_BK = src.CUSTOMER_BK
WHEN MATCHED
   AND (    tgt.CUSTOMER_NAME IS DISTINCT FROM src.CUSTOMER_NAME
         OR tgt.EMAIL         IS DISTINCT FROM src.EMAIL
         OR tgt.REGION        IS DISTINCT FROM src.REGION )
   THEN UPDATE SET
        tgt.CUSTOMER_NAME = src.CUSTOMER_NAME,
        tgt.EMAIL         = src.EMAIL,
        tgt.REGION        = src.REGION,
        tgt.LOAD_TS       = CURRENT_TIMESTAMP()
WHEN NOT MATCHED
   THEN INSERT (CUSTOMER_BK, CUSTOMER_NAME, EMAIL, REGION)
        VALUES (src.CUSTOMER_BK, src.CUSTOMER_NAME, src.EMAIL, src.REGION);
```

> Note: Snowflake does not enforce `UNIQUE`/PK constraints — they document
> intent only. Enforce business-key uniqueness via the profiling check and a
> data test, not by trusting the constraint.

## dbt equivalent

A Type 1 dimension is a plain incremental model with `unique_key` and a
`merge` strategy — dbt generates the `MERGE` above:

```sql
{{ config(materialized='incremental', unique_key='CUSTOMER_BK',
          incremental_strategy='merge') }}

SELECT CUSTOMER_BK, CUSTOMER_NAME, EMAIL, REGION
FROM {{ ref('stg_customer') }}
```

Add a `not_null` + `unique` test on `CUSTOMER_BK` in `schema.yml`.

## Checklist

* Decided Type 1 *per attribute* — not as a table-wide default.
* Confirmed no consumer needs point-in-time truth for these columns.
* Ghost row (`-1`) present.
* `MERGE` uses null-safe change detection and only touches changed rows.
* Business-key uniqueness covered by a test (constraints aren't enforced).
