# Value Discovery — Pains, Gains, Profiles, Use Cases

Used in **Step 1** of the skill. The goal: understand *why* this data matters to
a real person, so every later decision (grain, SLAs, historization) is argued
from their actual stakes — not abstractly. Adapted from the Value Proposition
Canvas: profile the consumer, then map their pains and gains to what the
pipeline delivers.

Ask one question at a time, each with a recommended default to react to.

---

## Customer profile

* **Who is the consumer, in role terms?** (Analyst, finance controller, ops lead,
  external customer, a downstream system.) There may be more than one — profile
  each, because their needs can conflict.
* **What is their job-to-be-done?** The outcome they're trying to achieve, of
  which this data is one input. ("Close the month accurately by day 3.")
* **How do they work today?** The current process this data plugs into or replaces.

## Pains (what hurts today)

* What's broken, slow, manual, or untrustworthy now? (Manual reconciliation,
  stale numbers, no audit trail, can't answer a question fast enough, conflicting
  numbers from two systems.)
* What's the cost of the pain? (Hours lost, decisions delayed, compliance risk,
  customer impact.) This quantifies the value and justifies the build.
* What's the *worst* failure mode they fear from this data? (Wrong numbers in
  front of an executive; a regulator query they can't answer.)

## Gains (what success looks like)

* Beyond "I get a table" — what outcome do they actually want? (Trustworthy
  numbers they don't re-check; self-serve answers without a ticket; a faster
  close.)
* What would make this *delightful* vs merely adequate? (Point-in-time history;
  freshness they can rely on; clear definitions everyone agrees on.)

## Use cases (how they'll actually use it)

* The concrete questions they'll ask of the data, or actions they'll take.
* These reveal the **filter columns**, the **grain**, and the **query latency**
  that matter — feed them directly into Steps 1 (consumption), 2 (grain), and 5
  (SLAs).

## Importance / stakes (the rigour budget)

* How critical is this — regulatory must-have, revenue driver, or nice-to-have?
* This calibrates how much rigour the rest of the design warrants. A
  compliance-critical asset earns WAP, SCD2, and tight reliability SLAs; an
  exploratory dashboard does not.

---

## Capturing it

Summarise as a short **value statement** at the top of the design doc:

> For *[profile]* who *[job-to-be-done]*, this *[pipeline/report]* relieves
> *[pain]* and delivers *[gain]*. It is *[importance level]* because *[stakes]*.

If you can't fill that sentence in, you don't yet understand the value — keep
asking before moving to grain.
