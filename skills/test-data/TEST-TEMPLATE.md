# Data Test Template

Copy-paste scaffolds for the core test battery, plus the per-model test-plan
shape and the Write-Audit-Publish gate. 

Two flavours below: **declarative** (dbt-style YAML) and **assertion SQL**
(every query should return zero rows = pass). Use whichever matches your
tooling (consult `docs/agents/tooling.md` if present). Substitute your
engine's functions and replace `{{model}}` / `{{col}}` / `{{key}}`.

---

## Declarative (dbt-style schema test)

```yaml
models:
  - name: {{model}}
    columns:
      - name: {{key}}
        tests:
          - unique:        { config: { severity: error } }
          - not_null:      { config: { severity: error } }
      - name: {{fk_col}}
        tests:
          - relationships:
              to: ref('{{parent_model}}')
              field: {{parent_key}}
              config: { severity: error }
      - name: status
        tests:
          - accepted_values:
              values: ['active','cancelled','pending','refunded']
              config: { severity: warn }
      - name: order_total
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              config: { severity: error }
    # freshness + volume live as source freshness / singular tests below
```

---

## Assertion SQL (zero rows = pass)

```sql
-- Uniqueness (error): every key unique
SELECT {{key}}, COUNT(*) AS n
FROM {{model}}
GROUP BY {{key}}
HAVING COUNT(*) > 1;

-- Not-null on key (error)
SELECT COUNT(*) AS null_keys FROM {{model}} WHERE {{key}} IS NULL;

-- Referential integrity (error): every FK resolves
SELECT f.{{fk_col}}
FROM {{model}} f
LEFT JOIN {{parent_model}} p ON f.{{fk_col}} = p.{{parent_key}}
WHERE p.{{parent_key}} IS NULL
  AND f.{{fk_col}} IS NOT NULL;

-- Accepted values (warn): only the agreed set
SELECT DISTINCT status
FROM {{model}}
WHERE status NOT IN ('active','cancelled','pending','refunded');

-- Freshness (error): newest row within SLA (read SLA from the pipeline spec)
SELECT MAX({{loaded_at}}) AS newest
FROM {{model}}
HAVING MAX({{loaded_at}}) < CURRENT_TIMESTAMP - INTERVAL '{{freshness_sla}}';

-- Volume / variance (warn): today's load vs baseline (docs/profiles/<table>.md)
SELECT COUNT(*) AS today_rows
FROM {{model}}
WHERE {{load_date}} = CURRENT_DATE
HAVING COUNT(*) < {{expected_min}} OR COUNT(*) > {{expected_max}};

-- Business rule (varies): e.g. returns after 30 days excluded from revenue
SELECT *
FROM {{model}}
WHERE is_revenue = TRUE
  AND returned_at IS NOT NULL
  AND returned_at <= order_date + INTERVAL '30 days';
```

---

## Per-model test plan (deliverable shape)

| Test                       | Column(s)        | Severity | Threshold / set                  |
|----------------------------|------------------|----------|----------------------------------|
| unique                     | order_id         | error    | —                                |
| not_null                   | order_id         | error    | —                                |
| relationships → dim_customer | customer_id    | error    | —                                |
| accepted_values            | status           | warn     | active/cancelled/pending/refunded |
| accepted_range             | order_total      | error    | >= 0                             |
| freshness                  | loaded_at        | error    | < 6h (from pipeline SLA)         |
| volume/variance            | (row count)      | warn     | 3,800–4,400/day (from baseline)  |
| business rule: 30-day returns | —             | error    | excluded from revenue            |

Severity rule of thumb: **error** = corrupts downstream facts (keys, RI,
not-null on keys); **warn** = soft anomaly worth a human glance. Don't let
everything become "error" — severity inflation destroys the signal.

---

## Where the tests run — Write-Audit-Publish gate

```
            ┌──────────┐     audit fails → ALERT, never publish
   source ──▶  WRITE   │────────────────────────────────┐
            │ (staging │                                 │
            │  branch) │                                 ▼
            └────┬─────┘                            (stay on staging,
                 │                                   prod untouched)
                 ▼
            ┌──────────┐   all error-tests pass
            │  AUDIT   │──────────────────────────┐
            │ (full    │                           ▼
            │ battery) │                      ┌──────────┐
            └──────────┘                      │ PUBLISH  │  back up prod first,
                                              │  (swap)  │  then swap staging in
                                              └──────────┘
```

1. **Write** — build into a staging table/branch; production untouched.
2. **Audit** — run the full battery against staging; compare row counts to
   production; validate schema, types, business rules, trend.
3. **Publish** — only on green, and only after backing up current production.
   Alert on failure; never publish on red.

Make every load idempotent so re-runs are safe (see `pipeline-design` if
installed).
