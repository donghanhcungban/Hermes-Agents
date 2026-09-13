---
name: profile-data
description: "Profile unfamiliar datasets before modelling or ingestion."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [data-profiling, quality, nulls, cardinality, analytics]
    related_skills: [data-modelling, data-security-classification, test-data]
---

# Profile Data

You cannot test, model, or trust data you haven't profiled. Profiling is the
sturdy foundation before the skyscraper (Ghost in the Data, "The Art of Data
Profiling"). Do it first; offer to save the results as a baseline.

Consult `docs/agents/platform.md` (if present) for the SQL dialect to emit.

This is the **bottom-up** half of data-quality assessment (DMBOK): inspect the
data itself to surface anomalies, then vet them top-down with the people who
own the business context. Each section below maps to a DMBOK **data-quality
dimension** — name the dimension when you report a finding so it carries
through into tests (see `test-data` if installed, which uses the same
vocabulary):

| Section | DQ dimension(s) |
|---|---|
| Cardinality / key uniqueness | **Uniqueness** |
| Completeness | **Completeness** |
| Distribution & outliers | **Reasonableness**, **Accuracy** (flagged) |
| Types, formats, sensitivity | **Validity**, **Privacy** |
| Drift vs baseline (in `test-data`) | **Consistency**, **Currency/Timeliness** |

(Validity = well-formed for the domain; accuracy = actually correct — profiling
can assert validity but only flags suspected accuracy issues for an SME.)

## The discipline — run every section, in order

### 1. Shape
* Total row count. Row count per partition/load date if partitioned.
* Column count, names, declared types, and (for strings) max length —
  flag any column whose real max length approaches its declared cap
  (the "Razzle Dazzle Rose" truncation trap).

### 2. Cardinality
* `COUNT(DISTINCT col)` and distinct% (`distinct / total * 100`) per column.
* Distinct% ≈ 100 → candidate key. Distinct% ≈ 0 → constant/low-signal.
  Mid-range → categorical (capture the value set for accepted-values tests).

### 3. Key uniqueness — the make-or-break check
* For each candidate business key (and composite), confirm
  `COUNT(*) = COUNT(DISTINCT key)`. **If it fails, stop and surface it** —
  a non-unique "key" silently fans out every downstream join.
* Check the key for nulls separately; a nullable key is not a key.

### 4. Completeness
* Null count AND null% per column. Separately count empty strings,
  whitespace-only, and sentinel values ('N/A', 'NULL', '-', 0 dates).
* Decide per column: is null expected, or a defect?

### 5. Distribution & outliers
* Numeric: min/max/mean/quartiles; flag impossible values (negative ages,
  future dates).
* Use null-safe comparison (`IS DISTINCT FROM` or your dialect's equivalent)
  whenever NULLs are in play.

### 6. Types, formats, sensitivity
* Confirm dates, timezones, numeric precision are what you assumed.
* Regex-scan for PII patterns (emails, phone, national IDs, postcodes) and
  classify by sensitivity so the model masks/encrypts/excludes appropriately.

### 7. Offer to save the baseline
Ask the user once: "Save this baseline to `docs/profiles/<table>.md`?"
If yes, write the profile (counts, cardinalities, null rates, observed
ranges, value sets, profiled-at date). Rules for what may be persisted:

* **Aggregates only** — counts, percentages, ranges, cardinalities. Never
  sample rows or record-level values.
* **Columns flagged as PII in step 6 get statistics only** — no observed
  value sets, no min/max for free-text identifiers.

This baseline is what data tests turn into volume/variance thresholds and
what drift detection diffs against on the next load (see `test-data` if
installed).

## Output
A short report: shape, candidate keys (with pass/fail on uniqueness),
columns that need tests, anomalies found, and an explicit "safe to build on /
not yet" verdict. Don't proceed to modeling until keys pass.

## Template

For pseudo-SQL scaffolds of every section above and the baseline report
shape, see [PROFILE-TEMPLATE.md](./PROFILE-TEMPLATE.md) (modelled on the
[data-quality profiling scripts](https://github.com/ghostinthedata-info/data-quality/tree/main/Data%20Profiling)).
Keep them tool-agnostic — swap in your engine's functions (consult
`docs/agents/platform.md` if present).
