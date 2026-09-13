---
name: solution-design
description: "Elicit pipeline/model requirements; produce a solution doc."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [solution-design, pipeline, requirements, data-engineering, planning]
    related_skills: [data-modelling, profile-data, test-data]
---

# Solution Design

"No-one knows exactly what they want." Your job is to make them precise.
Interview the user **one question at a time**, waiting for each answer. For
every question, give your recommended default so they can react, not invent.
Work through the steps in order. Don't skip ahead — each step feeds the next.

When you have enough to act on, produce the design using
`SOLUTION-DESIGN-TEMPLATE.md`. The four reference files below carry
the reusable knowledge so this file stays a process, not an encyclopaedia:

* `PIPELINE-PATTERNS.md` — the patterns we assemble pipelines from
* `ENGINEERING-STEPS.md` — the DE tasks/steps per pipeline stage
* `VALUE-DISCOVERY.md` — pains, gains, customer profiles, use cases
* `COMMON-RISKS.md` — a risk library to reference, not reinvent

---

## Step 1 — Value & consumers

Anchor everything in why this exists and who it serves. Pull the prompts from
`VALUE-DISCOVERY.md` and leave the session able to state:

* **Customer profile** — who consumes this, in role terms, and their job-to-be-done.
* **Pains** — what hurts today (manual reconciliation, stale numbers, no audit trail).
* **Gains** — what success looks like for them, beyond "I get a table".
* **Use cases** — the actual questions they'll ask or actions they'll take.
* **Importance / stakes** — regulatory must-have vs revenue driver vs nice-to-have.
  This sets the *rigour budget* for every later decision.
* **Consumption** — SQL, dashboard, or extract? Common filter columns? Acceptable
  query latency?

## Step 2 — Grain (the pivotal decision)

Declare what **one row represents** in a single sentence. Everything hangs off
this; the most common modeling failure is a fuzzy grain. Don't move on until
it's nailed.

## Step 3 — Sources & authority

Use `ENGINEERING-STEPS.md` (ingestion stage) for the full checklist.
Leave knowing, per source:

* **Authority** — is this the *agreed source of truth*? If two systems disagree,
  who wins? **Internal or vendor?** (Vendor changes escalation paths, achievable
  SLAs, and schema-change trust.)
* **Delivery & delta mechanics** — full snapshot or delta/incremental? If delta:
  cadence (e.g. daily) and the watermark column driving it.
* **Deletes** — soft or hard? In a delta feed, do deletes appear at all, or do
  rows just silently stop arriving? (The classic delta trap.)
* **Real-time consistency** — if polled via API: latency between calls? Risk of a
  record changing *between* two calls — torn reads, missed mid-flight updates?
* **Gap & recovery** — if you miss a day, is it a permanent hole or does the next
  delta backfill it? Can you replay?
* **Initial load** — day-zero from current state only, or full history backfill?
  (Determines whether rebuildable / SCD2 designs are even possible.)

## Step 4 — Definitions / ubiquitous language

Define every metric and entity precisely. "Active customer" by what rule?
"Revenue" — gross, net, returns within 30 days netted out? Capture these so two
people never compute the same metric two ways.

## Step 5 — SLAs (per pipeline, not repo-wide)

* **Freshness** — by when must it land; how fresh do consumers *truly* need it
  (real-time vs "today not yesterday" vs daily)? Push back on "real-time" that's
  really faster batch.
* **Volume** — rows now, plus daily/monthly growth.
* **Reliability** — what happens, and who's told, when it's late or wrong?

## Step 6 — Historization

Do consumers need point-in-time / "as it was when…" answers? If yes, you need
SCD2 (new row per change, validity interval, current flag). If not, don't pay
for it. Requires full source history (see Step 3 initial load).

## Step 7 — Choose the pattern recipe

Assemble the recipe from `PIPELINE-PATTERNS.md`: one ingestion
pattern + the transformation pattern + one or more delivery patterns. This
becomes the SVG overview in the design doc.

## Step 8 — Produce the solution design

Fill `SOLUTION-DESIGN-TEMPLATE.md`:

1. **Summary** — the reason / value (from Step 1).
2. **Overview (hand-authored inline SVG)** — source → ingestion → transform →
   delivery, focused on high-level tools/patterns, using the zone colours in the
   template. Model the phases on the pattern-bank flow.
3. **Tasks & steps** — broken into **1-5 day** work packages, never longer, each
   a single themed "story" with subtasks (e.g. "Day 1 · Environment & Access
   Setup"). Draw tasks from `ENGINEERING-STEPS.md`. This is how we
   space delivery and estimate time.
4. **Decisions register** — every material decision, why, alternatives, date,
   owner (official format in the template).
5. **Dependencies & risks** — reference `COMMON-RISKS.md`; list only
   the relevant ones plus any project-specific additions.

Deliver in thin vertical slices. Don't accept ad-hoc scope changes mid-slice —
route them through the decisions register instead.
