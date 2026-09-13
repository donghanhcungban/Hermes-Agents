# Common Data Project Risks

A reference library to pull from when filling the **Dependencies & Risks**
section of the design. Don't reinvent these per project — cite the relevant ones,
note likelihood/impact, and add a mitigation and owner. Add project-specific
risks beneath. Score each *Likelihood × Impact* (Low/Med/High).

---

## Source & ingestion

* **Unclear source of truth** — two systems hold the "same" data and disagree.
  *Mitigate:* name the authoritative system in the decisions register up front.
* **Vendor schema drift** — a vendor changes the feed without notice.
  *Mitigate:* data contract on ingest; alert on drift; vendor change-notice SLA.
* **Silent deletes in delta feeds** — deleted rows just stop arriving, so stale
  records linger. *Mitigate:* confirm delete semantics; reconcile against full
  snapshot periodically.
* **Missed-day gaps** — a skipped run leaves a permanent hole.
  *Mitigate:* idempotent, replayable loads; monitor for gaps; backfill path.
* **Real-time read consistency** — records change between paginated/API calls,
  causing torn reads or missed updates. *Mitigate:* watermark with overlap;
  reconcile; prefer CDC where consistency is critical.
* **No full history available** — source only gives current state, blocking any
  rebuildable/SCD2 design. *Mitigate:* start capturing snapshots now; set
  expectations that history begins at go-live.
* **Late-arriving / backdated data** — rows arrive for a past period after it's
  closed. *Mitigate:* reprocessing window; as-of logic.

## Modelling & quality

* **Fuzzy grain** — the most common modelling failure; row meaning is ambiguous.
  *Mitigate:* declare grain in one sentence and test uniqueness on it.
* **Definition drift** — the same metric computed two ways by two people.
  *Mitigate:* ubiquitous-language definitions captured and referenced.
* **Bad batch reaches consumers** — an error surfaces in a dashboard before
  anyone catches it. *Mitigate:* WAP; DQ tests blocking publish.
* **Untested transformations** — logic changes silently shift data.
  *Mitigate:* CI tests; data-diffing on PRs.

## Delivery & operations

* **"Real-time" that's really faster batch** — over-engineered freshness inflates
  cost and complexity. *Mitigate:* pin the true freshness need in the SLA.
* **No ownership on failure** — pipeline breaks and no one is told.
  *Mitigate:* named owner; alerting tested by forcing a failure.
* **Latency SLA missed under load** — consumer queries slow as volume grows.
  *Mitigate:* model to filter columns; test at projected volume.
* **Cost runaway** — volume growth or inefficient compute blows the budget.
  *Mitigate:* volume estimates up front; monitor cost; attribute by pipeline.

## Delivery management

* **Scope creep mid-slice** — ad-hoc additions derail an in-flight slice.
  *Mitigate:* thin vertical slices; route changes through the decisions register.
* **Assumed-no-strategy meetings** — work proceeds as if testing/standards don't
  exist. *Mitigate:* bring the playbook/standards into the room early.
* **Key-person dependency** — only one person understands the pipeline.
  *Mitigate:* documentation; defined handover/pick-up points per story.
* **Unmanaged dependencies** — an upstream team/source/access isn't ready in time.
  *Mitigate:* list dependencies explicitly with owners and dates.
