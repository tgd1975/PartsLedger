---
id: EPIC-003
name: skill-path-today
title: Skill path — /inventory-add and /inventory-page
status: open
opened: 2026-05-14
closed:
assigned:
branch: feature/skill-path-today
---

Seeded by IDEA-005 (Skill path today).

Honing work on the two LLM-orchestrated skills already in production —
hedge-language lint backstop, family-page proactive suggestion, and the
page-gen auto-trigger that chains `/inventory-add` → `enrich()` →
`/inventory-page` once the enrichment orchestrator lands.

Phase placement:

- **Phase 0** — hedge-language lint + pre-commit hook.
- **Phase 3** — page-gen auto-trigger (depends on EPIC-007 Stages 1–4
  and Stage 6 sync chain).
- **Phase 5 (schedule-flexible)** — family-page proactive suggestion at
  add-time and page-gen-time.

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
