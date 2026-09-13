---
name: data-modelling
description: "Design analytics data models: Kimball, SCD, fact tables."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [data-modelling, kimball, scd, fact-tables, analytics, star-schema]
    related_skills: [profile-data, data-security-classification, test-data]
---

# Data Modeling

This is the **entry point** for any analytics modeling task. It does not do
the deep work itself — it sequences the work and hands off to the focused
skills and reference files below. 
emit Snowflake SQL unless `docs/agents/platform.md` says otherwise.

Kimball's core move: **separate measurements (facts) from context
(dimensions)**, declare the grain before anything else, and pick history
policy per attribute. Never default everything to Type 2.

## Workflow (do not reorder)

### 0. Profile first — you cannot model what you haven't profiled

Before any design, run the **`profile-data`** skill (if installed) on each
source table. You need row counts, candidate-key uniqueness, null/blank
rates, cardinality, and type/precision facts. **Do not declare a key or a
grain until key-uniqueness passes.** If `profile-data` is not installed, at
minimum confirm `COUNT(*) = COUNT(DISTINCT <business_key>)` and check the key
for nulls.

### 1. Clarify before designing — ask, don't assume

A fuzzy grain is the #1 dimensional-design failure. Ask the questions in the
**Clarifying questions** section below and wait for answers before emitting
DDL. The most expensive modeling mistakes are committed silently at this step.

### 2. Apply the four-step Kimball process

Hand off to **`dimensional-modeling`** (if installed) for the full flow.
Summary:

1. **Select the business process** — the verb (taking an order, a payment).
2. **Declare the grain** — one unambiguous sentence; most atomic possible.
3. **Identify the dimensions** — who/what/where/when/why/how.
4. **Identify the facts** — numeric measures true to the grain.

### 3. Design the facts

Hand off to **`fact-table-design`** (if installed) and to
[FACT-TABLES.md](./FACT-TABLES.md) for the Snowflake
treatment — transaction vs periodic vs accumulating snapshot, and additivity
classification for every measure.

### 4. Design the dimensions and choose history policy per attribute

Surrogate-key every dimension; keep the natural/business key as a column for
lineage, and for SCD2 carry the **durable ("super-natural") key** that ties
all versions of an entity together — and put that durable key on the fact too,
so you can report all history by current attributes. See **`keys`** (if
installed) for the full decision rules, composite-key validation, and
anti-patterns. Most warehouses (Snowflake included) don't enforce key
uniqueness — **test** every key for unique + not-null.

For each dimension attribute, decide the SCD type. Hand off to
**`slowly-changing-dimensions`** (if installed) for the full type catalogue.
For the two you'll reach for >90% of the time, use the Snowflake-specific
references:

* [SCD1.md](./SCD1.md) — overwrite (Type 1).
* [SCD2.md](./SCD2.md) — history rows (Type 2).

### 5. Backfill, if loading history into an SCD2

Only when you must reconstruct history from full source. See
[BACKFILLING.md](./BACKFILLING.md) for the
deterministic, rebuildable (Healing Tables) approach in Snowflake — zero-copy
clone test harness, two-step RAW→HST staging, and partition-level loads.

## Clarifying questions (ask these before emitting DDL)

Ask only the ones not already answered by profiling or the user:

1. **Grain** — what does exactly one row in the target table represent, in
   business terms? (If they can't say it in one sentence, the grain isn't set.)
2. **Business process / fact type** — is this a measurement event
   (transaction), a state-at-a-point (periodic snapshot), or a workflow with
   milestones (accumulating snapshot)?
3. **Business key** — which column(s) uniquely identify the entity? Did
   uniqueness pass in profiling?
4. **History** — for each changing attribute: does anyone need to know its
   value *as of a past date*? If yes → Type 2; if only "latest" matters →
   Type 1; if it never changes → Type 0.
5. **Source history available?** — is full source history present (enables a
   clean backfill/rebuild), or only current state going forward?
6. **Volume & latency** — high-volume/real-time (favours plain incremental)
   or batch with acceptable rebuild time (favours Healing-Table rebuild)?
7. **Measures** — what gets counted/summed, and is each one additive,
   semi-additive (don't sum over time), or non-additive (a ratio — store the
   components)?

## Reference files (deeper knowledge)

| File | When to open it |
|---|---|
| [SCD1.md](./SCD1.md) | Overwrite-in-place dimension attributes on Snowflake. |
| [SCD2.md](./SCD2.md) | History-tracking dimensions, effectivity intervals, validation. |
| [BACKFILLING.md](./BACKFILLING.md) | Loading/rebuilding history into an SCD2 deterministically. |
| [FACT-TABLES.md](./FACT-TABLES.md) | Fact grain, the three types, additivity, factless/degenerate. |

## Related skills (compose with these if installed)

* `profile-data` — run first (step 0).
* `dimensional-modeling` — the four-step process and dimension techniques.
* `slowly-changing-dimensions` — the full SCD type catalogue (0–7).
* `fact-table-design` — grain/type selection and measure discipline.
* `keys` — business/surrogate/composite/durable key design and anti-patterns.
* `test-data` / `keys` / `conformed-dimensions` — if installed, for tests,
  surrogate-key rules, and the bus matrix.

## Output contract

End every modeling task with: the **one-sentence grain** per table, the chosen **fact
type** (or SCD type per attribute), candidate-key **uniqueness verdict**, and
a Snowflake **DDL skeleton**. Use naming from `CONTEXT.md` if present.
