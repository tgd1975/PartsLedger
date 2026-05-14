---
id: EPIC-002
name: markdown-inventory-schema
title: Markdown inventory schema
status: open
opened: 2026-05-14
closed:
assigned:
branch: feature/markdown-inventory-schema
---

Seeded by IDEA-004 (Markdown inventory schema) and IDEA-012 (Integration
pass — Gap 7 on schema-invariant enforcement).

The on-disk schema invariants that every other writer has to match —
`Source` column, maker-choice section taxonomy, parts-page template
adaptivity, multi-file split support, and the shared
`upsert_row()` writer contract three callers (`/inventory-add`,
camera-path Stage 4, enrichment Stage 4) all import.

Phase placement per the implementation plan:

- **Phase 0** — Stages 1 + 2 (Source column, parts-page template).
- **Phase 0b** — `src/partsledger/inventory/writer.py` and
  `src/partsledger/inventory/lint.py` land alongside the EPIC-004
  package layout. Both must exist before EPIC-006 Stage 4 wires the
  camera path to the writer.
- **Phase 5 (paused)** — Stage 3 multi-file split support; activates
  only when a real bin grows past the comfortable single-file
  threshold.

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
