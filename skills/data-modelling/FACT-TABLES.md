# Fact Table Design (Snowflake)

Facts hold the measurements; everything else is context. Get the **grain** and
the **type** right and aggregation is trivial; get them wrong and every
downstream query is a workaround. This is the Snowflake-flavoured companion to
the `fact-table-design` skill (see it if installed for the full treatment).

## Declare the grain first (non-negotiable)

State what **one fact row** means in business terms — "one row per order
line", "one row per daily account balance", "one row per claim lifecycle".
Choose the **most atomic** grain the source supports: atomic facts answer
questions you haven't thought of yet and roll up freely; pre-aggregated facts
can't drill down. Never mix grains in one table.

## The three fact-table types

* **Transaction** — one row per measurement event. Most common and atomic;
  rows are **inserted, never updated**. Default to this. In Snowflake, load
  via `COPY INTO` / Snowpipe append; an insert-only stream is ideal.
* **Periodic snapshot** — one row per entity per regular period (daily
  balance, monthly state). Dense — a row exists each period whether or not
  anything changed. Generate with a date spine cross-joined to entities.
* **Accumulating snapshot** — one row per workflow instance, **updated in
  place** as it passes milestones (ordered → picked → shipped → delivered),
  with one date FK per milestone plus lag measures. In Snowflake this is a
  `MERGE` that updates the milestone columns as events arrive.

Most processes warrant a transaction grain *and* a complementary snapshot —
they answer different questions; they are not alternatives.

## Snowflake DDL skeleton (transaction fact)

```sql
CREATE TABLE IF NOT EXISTS FCT_ORDER_LINE (
    -- surrogate FKs to dimensions (never natural keys)
    DATE_SK         NUMBER   NOT NULL,
    CUSTOMER_SK     NUMBER   NOT NULL,
    PRODUCT_SK      NUMBER   NOT NULL,
    -- durable keys for point-in-time reporting by current attributes
    CUSTOMER_BK     VARCHAR,
    -- degenerate dimension: id kept on the fact, no table of its own
    ORDER_NUMBER    VARCHAR  NOT NULL,
    ORDER_LINE_NO   NUMBER   NOT NULL,
    -- additive measures
    QUANTITY        NUMBER(18,2),
    EXTENDED_AMOUNT NUMBER(18,2),
    -- non-additive ratio stored as its additive COMPONENTS
    DISCOUNT_AMOUNT NUMBER(18,2),   -- numerator
    GROSS_AMOUNT    NUMBER(18,2),   -- denominator (compute % at query time)
    LOAD_TS         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

Snowflake doesn't enforce FK constraints — keep them documented and test
referential integrity (every FK resolves to a real dimension row).

## Measure additivity (mark every measure)

* **Additive** — sums across **all** dimensions (quantity, amount). Aim for
  these.
* **Semi-additive** — sums across some dimensions but **not time** (balances,
  inventory, headcount). Over time use an average or period-end value, never
  `SUM`.
* **Non-additive** — never sum (ratios, %, unit prices). Store the **additive
  components** (numerator + denominator) and compute the ratio at query time.

Document additivity beside each measure (in `schema.yml` if using dbt) — it's
the contract that stops someone `SUM`-ing a balance and shipping a wrong
number.

## Factless facts

A fact with no numeric measure — the **event itself** is the fact.

* **Event tracking** — student attended class; `COUNT(*)` is the measure.
* **Coverage** — record what *could* have happened to find what *didn't*
  (products on promotion with no sales). Without coverage, absence is
  invisible.

## Degenerate dimensions

A dimension key with no attributes (order number, ticket number) kept **on the
fact row** for grouping and lineage. Don't build a single-column table for it.

## Rules & anti-patterns

* FKs to dimensions are **surrogate keys** (see `keys` if installed for the
  full business/surrogate/composite/durable decision rules); never join facts
  on natural keys.
* Every FK points at a real row — route unknowns to the dimension's
  ghost/"unknown" row (key `-1`) so a fact is never dropped on join.
* No descriptive text on the fact (belongs on a dimension); no measures on a
  dimension.
* `NULL` is fine for a missing **measure**; never allowed in a **foreign
  key** — use the ghost row.
* SCD policy is chosen per **dimension attribute** (see [scd1.md](./scd1.md) /
  [scd2.md](./scd2.md)), not on the fact.
* Carry the **durable key** on the fact alongside the surrogate for
  point-in-time reporting by current attributes.

## Checklist

* Grain written as one unambiguous sentence; most atomic available.
* Type chosen (transaction / periodic / accumulating) and matches the question.
* Every measure marked additive / semi-additive / non-additive.
* Ratios stored as components, not as the ratio.
* All FKs surrogate; unknowns routed to ghost row; RI covered by a test.
