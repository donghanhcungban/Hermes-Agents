# Engineering Steps per Pipeline

The concrete DE tasks per stage, with what "done" looks like. Use these to fill
the **Tasks & steps** section of the design, grouped into 1-5 day stories. Not
every task applies to every recipe — delete what the pattern doesn't need.

A task is **done** when it's deployed via code (not hand-built), tested, and
hands cleanly to the next stage. Each story should name an explicit handover /
pick-up point.

---

## Stage 1 — Ingestion → Raw

* **Access & identity** — service roles/IAM, scoped least-privilege, secrets in a
  managed store (not in code). *Done:* pipeline can authenticate to source and
  target with no static credentials in the repo.
* **Landing zone** — bucket/stage for raw arrivals, with archive and failed-row
  paths. *Done:* a test file/payload lands, archives, and a bad payload routes to
  failed.
* **Source connection** — implement the chosen ingestion pattern (API/file/CDC/
  stream/webhook). Capture watermark column, cadence, pagination. *Done:* a real
  extract pulls the expected rows for a known window.
* **Delta & delete handling** — confirm soft vs hard delete behaviour; ensure
  deletes are captured or explicitly accepted as out-of-scope. *Done:* a deleted
  source record produces the agreed result downstream.
* **Data contract** — schema/type/null expectations validated on ingest. *Done:*
  a schema drift triggers the agreed action (fail/quarantine/alert).
* **Managed load to raw** — pipe/loader into the raw layer. *Done:* landed data
  appears in raw with lineage/load metadata.
* **Backfill / replay** — initial day-zero load and a documented replay path for
  missed days. *Done:* you can re-run a past window and get identical results.

## Stage 2 — Transformation → Modelled

* **Staging models** — type-cast, rename, dedupe to source grain. *Done:* one row
  per declared grain, tested.
* **Intermediate/business logic** — joins, metric definitions per the agreed
  ubiquitous language. *Done:* metrics match the documented definitions exactly.
* **Historization** — SCD2 / snapshot if point-in-time is required. *Done:*
  point-in-time query returns the value as-of a past date.
* **Data quality** — relationship/uniqueness/not-null/accepted-values tests; WAP
  if correctness-critical. *Done:* tests run in CI and block publish on failure.
* **Marts** — consumer-facing models at the consumption grain and filter columns.
  *Done:* common consumer queries run within the latency SLA.

## Stage 3 — Delivery → Consumer

* **Delivery mechanism** — view/extract/event/reverse-ETL per the recipe. *Done:*
  consumer accesses data in their stated form (SQL/dashboard/file).
* **Notification & monitoring** — completion/late/failure alerts to the named
  owner. *Done:* a forced failure pages the right person.
* **Freshness check** — verify the freshness SLA holds end to end. *Done:* data is
  available by the committed time.

## Cross-cutting (every story)

* **CI/CD** — everything deployed from version control, not the console.
* **Security** — bucket policies, network controls, permission boundaries.
* **Documentation** — model docs + the decisions register kept current.
* **Hypercare** — a defined window of heightened monitoring post-go-live with a
  named owner and exit criteria.
