# Pipeline Patterns

A pipeline is **assembled as a recipe**: pick one pattern from each stage —
**Ingestion → Transformation → Delivery** — and combine them. Patterns are
deliberately generic so an engineer can delete what they don't need and drop in
the specifics for their source. Stage colours below match the SVG overview zones
in the solution-design template (source = cyan, ingest = blue, transform =
purple, delivery = green).

Pick the *thinnest* pattern that meets the freshness and historization SLAs.
Complexity is a cost paid forever; only buy it when a consumer need demands it.

---

## Stage 1 — Ingestion (how data lands in raw)

| Pattern | Shape | Use when |
|---|---|---|
| **API extract** | Scheduled pull from a REST/GraphQL endpoint, paginated, watermark-driven | Vendor/internal app exposes an API; moderate volume; delta by `modified_at` |
| **Flat-file / object drop** | Source lands files (CSV/JSON/Parquet) in a bucket; event-triggered load | Batch exports, SFTP-style handoffs, vendor file feeds |
| **CDC / replication** | Database change-data-capture streamed from a source DB | Source is a transactional DB; need low-latency or row-level deletes captured |
| **Streaming ingest** | Continuous event stream consumed to raw | True real-time events; high volume; append-mostly |
| **Push / webhook** | Source pushes events to an endpoint you expose | Source controls cadence; bursty; you can't poll |

Every ingestion pattern shares a **common load block**: landing zone → managed
ingest into the raw/warehouse layer (e.g. a pipe), with archiving, failed-row
routing, and a data contract check. Capture per-source delta cadence, delete
semantics, and replay/backfill behaviour here (see skill Step 3).

## Stage 2 — Transformation (raw → modelled)

| Pattern | Shape | Use when |
|---|---|---|
| **ELT in-warehouse (modular SQL)** | Layered models (staging → intermediate → marts) in the warehouse | Default. Transformation logic lives in version-controlled SQL models |
| **WAP (write-audit-publish)** | Write to a staging table, run audits, publish only on pass | Correctness-critical data; you must never expose a bad batch |
| **SCD2 historization** | New row per change, validity interval, current flag | Consumers need point-in-time / "as it was when…" answers |
| **Snapshot / accumulating** | Periodic full snapshots or accumulating fact | History from a source that only gives current state |

## Stage 3 — Delivery (modelled → consumer)

| Pattern | Shape | Use when |
|---|---|---|
| **Direct query / view** | Consumers read curated views/marts directly | Analysts on SQL; BI tools |
| **Extract / export** | Generate a file or push to a downstream system | Downstream app, vendor, or regulator needs a feed |
| **Notification / event** | Emit an event/notification on completion or condition | Trigger downstream jobs; alert on landing |
| **Reverse ETL** | Push curated data back into an operational system | Operational consumers (CRM, marketing) need the modelled result |

---

## Sequencing into day-sized work

Group the recipe's tasks into themed **1-5 day stories**, never longer. Typical
shape for an ingestion-led pipeline (adjust to the recipe and engineer level):

* **Day 1 · Environment & Access Setup** — IAM/roles, secrets, landing zone.
* **Day 2 · Ingest Build & Test Run** — the chosen ingestion pattern end to end.
* **Day 3 · Transformation & Data Quality** — models + WAP/DQ checks.
* **Day 4 · Delivery & Notification** — the chosen delivery pattern + alerts.
* **Day 5 (heavier patterns) · Hardening & Prod Cadence** — replication/CDC
  setup or prod deployment with wait-for-batch constraints.

A senior engineer may compress days 1–2; a newer one may split further. Heavier
ingestion (CDC/replication) genuinely needs extra setup time — say so in the
estimate rather than hiding it.
