# Backfilling SCD2 History (Snowflake)

Use this when you must reconstruct an SCD2 dimension's history from full
source — not for ongoing incremental loads (that's [scd2.md](./scd2.md)).

## Why not just replay day by day

Day-by-day SCD2 backfills **compound errors**: a miss on Jan 3 becomes the
baseline for Jan 4, and you can't fix one day without redoing every day built
on it. The fix is a **path-independent** rebuild — a *Healing Table* — that
separates *change detection* from *period construction* and rebuilds the whole
timeline from source. The result depends only on source data, not on load
history; fix the logic, reprocess the range, and the dimension "heals."

Use it when you have full source history and rebuild time is acceptable. Keep
plain incremental for very high volume or real-time.

## The six steps (Snowflake)

1. **Effectivity table** — extract every actual change point from source;
   filter out non-changes with null-safe comparison
   (`prev IS DISTINCT FROM curr`).
2. **Time slices** — `LEAD()` over the change points to derive
   `VALID_FROM`/`VALID_TO` (left-closed/right-open).
3. **Join sources** — build a unified timeline; as-of join each source and
   **document attribute ownership** (which source wins per column).
4. **Hash** — a key-hash for identity and a row-hash for change detection;
   `COALESCE` NULLs to a sentinel so `NULL` ≠ `''`.
5. **Compress** — collapse consecutive identical states (islands-and-gaps),
   only where temporally contiguous **and** row-hash-equal.
6. **Validate** — the temporal-integrity tests from
   [scd2.md](./scd2.md) before publish.

If `slowly-changing-dimensions` is installed, its `HEALING-TABLE-TEMPLATE.md`
has tool-agnostic pseudo-SQL for all six steps — swap in the Snowflake
functions below.

### Snowflake building blocks

```sql
-- Step 1+2: change points → time slices
WITH ranked AS (
  SELECT CUSTOMER_BK, REGION, NAME, EFFECTIVE_TS,
         LAG(REGION) OVER (PARTITION BY CUSTOMER_BK ORDER BY EFFECTIVE_TS) AS prev_region,
         LAG(NAME)   OVER (PARTITION BY CUSTOMER_BK ORDER BY EFFECTIVE_TS) AS prev_name
  FROM SRC_CUSTOMER_HISTORY
),
changes AS (
  SELECT * FROM ranked
  WHERE prev_region IS DISTINCT FROM REGION
     OR prev_name   IS DISTINCT FROM NAME
     OR prev_region IS NULL                 -- first row per key
)
SELECT CUSTOMER_BK, REGION, NAME,
       EFFECTIVE_TS AS VALID_FROM,
       COALESCE(
         LEAD(EFFECTIVE_TS) OVER (PARTITION BY CUSTOMER_BK ORDER BY EFFECTIVE_TS),
         '9999-12-31'::TIMESTAMP_NTZ
       ) AS VALID_TO
FROM changes;
```

## Test harness — zero-copy clone

Never rebuild a production HST table in place on the first attempt. Snowflake
**zero-copy cloning** gives you a full-size, isolated copy in seconds at no
storage cost until you diverge:

```sql
CREATE TABLE EDWPROD.HST.DIM_CUSTOMER_HST_BACKFILL_TEST
  CLONE EDWPROD.HST.DIM_CUSTOMER_HST;
-- or clone the whole schema for a wider rehearsal:
CREATE SCHEMA EDWPROD.HST_BACKFILL_TEST CLONE EDWPROD.HST;
```

Rebuild into the clone, run the validation suite, diff against the live table,
then swap (`ALTER TABLE ... SWAP WITH`) or re-point. Drop the clone when done.

## Two-step RAW → HST staging

Stage the rebuilt timeline in a RAW landing table first, validate it there,
then promote to HST. This keeps a broken rebuild out of the published table
and gives you an inspectable artifact:

1. `RAW.DIM_CUSTOMER_BACKFILL` — output of steps 1–5, untrusted.
2. Run validation (step 6) against RAW.
3. On pass, `INSERT`/`SWAP` into `HST.DIM_CUSTOMER_HST`.

## Partition-level loads with COPY INTO

For large historical source spread across S3, load **month-level partitions**
rather than one monolithic file — it bounds memory, makes failures
re-runnable per partition, and parallelises:

```sql
COPY INTO RAW.DIM_CUSTOMER_BACKFILL
FROM @EDP_STAGE/customer/history/year=2024/month=03/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = ABORT_STATEMENT;
```

Loop the months, validate each partition's row counts against the profiling
baseline before promotion, and keep the load idempotent (truncate-and-reload
the target partition, or dedupe on the key-hash) so a re-run is safe.

## Checklist

* Rebuilt into a **zero-copy clone**, never live, on the first pass.
* Staged through **RAW**, validated, then promoted to HST.
* Loaded by **partition** (e.g. month) with per-partition row-count checks.
* All six Healing-Table steps applied; result is path-independent.
* Full [scd2.md](./scd2.md) temporal-integrity suite passes before publish.
* Load is idempotent — a re-run produces an identical table.
