# Upstream provenance — UI/UX Pro Max

- Source: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- Upstream commit reviewed: `dcc40ff5133ef78276117db0cc34e7b83cc8aeba`
- Upstream skill version reviewed: `2.13.0`
- License: MIT
- Copyright: Copyright (c) 2024 Next Level Builder
- Full license notice: `LICENSE` in this directory
- Integrated for Hermes-Agents: 2026-09-23

## Vendored scope

The sync manifest mirrors only runtime/search assets required by the Hermes skill:

- search/reasoning scripts (`core.py`, `design_system.py`, `reasoning_contract.py`, `search.py`)
- searchable design data and 22 stack catalogs
- upstream `quick-reference.md` and `pro-rules.md`

Upstream CLI installers, platform templates, screenshots, gallery, preview app, and upstream
test fixtures are intentionally not vendored into Hermes.

## Trust model

Upstream data is treated as design intelligence, not executable authority. Hermes-specific
precedence, routing, persistence, privacy, and verification rules live in `SKILL.md`.
