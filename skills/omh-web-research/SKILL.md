---
name: "omh-web-research"
description: "[omh] Web lookup lane - settle a current-facts question in one cited retrieval round with retrieval dates and source-quality notes; for pre-spec grounding across reference implementations use `research`. Use when the user says: web-research, web research, web search, search the web, internet search, look up, look up sources, latest sources."
metadata:
 hermes:
 tags: [workflow, oh-my-hermes, research]
 category: research
 phase: web-evidence
 role: researcher
 quality_tier: source-gated
---

# Web Research

This is an OMH `web-research` workflow skill, projected for Agent Skills hosts (Claude Code, Codex, Cursor, opencode, OpenClaw, pi).

## Why This Exists

`web-research` exists so a current-facts question returns a cited answer in one retrieval round, without the declared depth budget, reference-implementation study, and dossier that `research` requires.

## Do Not Use When

- The decision needs reference-implementation study, a declared depth budget, or a decision-grounding dossier; use `research`.
- Correctness turns on one technology's versioned official or upstream guidance; use `best-practice-research`.
- The output is a typed candidate inventory and acquisition status rather than an answer; use `source-finder`.
- The ask is a market, competitor, pricing, or customer decision brief; use `research-brief`.
- The user wants recurring monitoring, a source inbox, or Scout/Analyst/Briefer operations; use `research-department`.
- The user wants to configure or cheapen web search itself, such as a scraper API key or an auxiliary extract model; use `websearch-setup`.
- The study target is this repository rather than the open web; use `codebase-onboarding`.

## Examples

Good example:

- Prompt: ì´ë² ì£¼ ê¸°ì¤ì¼ë¡ ê·¸ API ìê¸ì  ì´ë»ê² ë°ëìëì§ ì¹ìì¹í´ì ìë ¤ì¤.
- Expected behavior: Retrieve current pricing from the vendor's own page, cite it with the retrieval date, and name what the page does not state.
- Why: A current-facts question that one cited retrieval round settles.

Bad example:

- Prompt: ì¤í ì¡ê¸° ì ì ì¤íìì¤ êµ¬íë¤ ê¹ê² ë³´ê³  ê·¼ê±° ë§ë¤ì´ì¤.
- Expected behavior: Route to `research`, which declares a depth budget and studies reference implementations with pinned refs.
- Why: Pre-spec grounding needs the engine's dossier rather than a single lookup.

## Completion Checklist

- The research question, source boundaries, recency assumptions, and confidence level are named.
- Observed sources, inference, synthesis, and unresolved retrieval gaps are separated.
- Follow-up planning or handoff uses the research summary without calling it execution evidence.

## Recovery Notes

- If the web is unreachable, name the retrieval gap and stop rather than substituting recalled facts.
- If no archive access exists or the capture provider's paid authority is exhausted, record a temporal retrieval gap with no network action and keep the as-of claim in the annex; never substitute the current page for it.
- If sources conflict, present both with their retrieval d
