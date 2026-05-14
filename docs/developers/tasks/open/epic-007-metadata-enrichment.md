---
id: EPIC-007
name: metadata-enrichment
title: Metadata enrichment — Nexar
status: open
opened: 2026-05-14
closed:
assigned:
branch: feature/metadata-enrichment
---

Seeded by IDEA-008 (Metadata enrichment — Nexar).

Optional plumbing for the Datasheet / Description / Notes cells. Never
gates a write — enrichment is best-effort and runs out-of-band on the
camera path, synchronously on the skill path.

Phase placement:

- **Phase 1** — Stages 1–4 (Nexar OAuth + GraphQL adapter, per-MPN
  response cache, family-datasheet fallback table, orchestrator with
  writer-integration that never clobbers non-empty cells).
- **Phase 2** — Stage 5 camera-path async dispatch (single-worker
  thread + `enrichment.log`; depends on EPIC-006 Stage 4 hook).
- **Phase 3** — Stage 6 skill-path sync chain + page-gen trigger
  (paired with EPIC-003 page-gen auto-trigger task).

Design is fully honed (8 closed open-Qs in IDEA-008). Auth env-vars
(`PL_NEXAR_CLIENT_ID`, `PL_NEXAR_CLIENT_SECRET`) reserved. No code yet.

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
