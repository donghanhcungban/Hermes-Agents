---
name: test-data
description: "Design data quality tests: nulls, integrity, freshness."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [data-testing, quality-gates, dbt, write-audit-publish, freshness]
    related_skills: [profile-data, data-modelling, data-security-classification]
---

# Test Data

Tests are the gatekeeper between bad data and your consumers. Decide what to
test, how loud each failure is, and where the gate sits.

Consult `docs/agents/platform.md` and `docs/agents/tooling.md` (if present)
for the SQL dialect and test framework to emit. SLA thresholds (freshness,
volume) are pipeline-level facts — read them from the pipeline's spec, not
from repo-wide config.

## What to test (the core battery)

* **Uniqueness** — every key (and composite) is unique. Non-negotiable.
* **Not-null** — keys and any column the business calls mandatory.
* **Referential integrity** — every fact FK resolves to a dimension row.
  Catches orphaned facts and bad joins.
* **Accepted values** — categorical columns contain only the agreed set
  (catch the fourteen spellings of "active" before they accumulate).
* **Freshness** — source/loaded-at timestamp is within the pipeline's SLA.
  Run freshness checks at least twice as often as the tightest SLA.
* **Volume & variance** — row count is within expected bounds and today's
  load isn't wildly off yesterday's (drift vs the saved profile baseline in
  `docs/profiles/`, if one exists).
* **Business rules** — singular tests for logic that needs
  joins/aggregations ("returns after 30 days are excluded from revenue").

## Name what each test defends — the DQ dimensions

Frame the battery against the **DMBOK data-quality dimensions** so coverage is
explicit and gaps are visible. Every test should map to one:

* **Completeness** — not-null / mandatory-attribute checks (and "all expected
  rows present" — see volume below).
* **Uniqueness** — key and composite-key uniqueness; no entity appears twice.
* **Validity** — values conform to the domain: accepted-values, type/format,
  range/pattern. (Valid ≠ accurate — a well-formed value can still be wrong.)
* **Accuracy** — agreement with a reference source of truth; usually a
  business-rule test comparing to a system of record, not a column check.
* **Consistency** — values don't conflict across records, datasets, or over
  time (record-level, cross-record, temporal). Referential integrity lives
  here too: every FK resolves.
* **Timeliness / currency** — freshness within SLA.
* **Reasonableness** — volume/variance within expected operational bounds
  (e.g. today within 105% of the 30-day average).

If a critical column has no test in some dimension, that's a coverage gap to
raise. (Same vocabulary `profile-data` uses to assess a dataset, if installed.)

## Severity — make failures mean something

* **error** (block the pipeline) — key uniqueness, not-null on keys,
  referential integrity, anything that corrupts downstream facts.
* **warn** (flag, don't block) — soft anomalies, a few unexpected
  categorical values, mild volume drift worth a human glance.

Tune thresholds as data grows — e.g. warn at >10 nulls, error at >100.
Severity inflation (everything is "error") destroys the signal, same as it
does for incidents.

## Where tests live — Write-Audit-Publish (Ghost in the Data)

Don't test in production after the fact. Use **WAP**:

1. **Write** — build the new data into a staging table/branch, production
   untouched.
2. **Audit** — run the full test battery against staging. Compare row counts
   to production; validate schema, types, business rules, and historical
   trend.
3. **Publish** — only if the audit passes, swap staging into production —
   **after backing up** the current production table. Alert on audit
   failure; never publish on red.

This is blue-green deployment for data: consumers never see unaudited data,
and you can roll back to the backup instantly. Make every load idempotent so
re-runs are safe (see `pipeline-design` if installed).

## Deliver

A test list per model, each with severity and (where useful) thresholds,
plus the WAP gate wired into the pipeline.

## Template

For copy-paste scaffolds of the full battery (declarative dbt-style YAML
and assertion SQL), the per-model test-plan shape, and the WAP gate, see
[TEST-TEMPLATE.md](./TEST-TEMPLATE.md) (modelled on the
[data-quality checks](https://github.com/ghostinthedata-info/data-quality/tree/main/Data%20Quality%20Checks)).
Keep them tool-agnostic — match the flavour to your stack (consult
`docs/agents/tooling.md` and `docs/agents/platform.md` if present).
