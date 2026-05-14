---
id: EPIC-009
name: integration-followups
title: IDEA-012 integration-pass follow-ups
status: open
opened: 2026-05-14
closed:
assigned:
branch: feature/integration-followups
---

Seeded by IDEA-012 (Integration pass).

Two paused placeholders absorbing IDEA-012 Section 4's remaining open
gaps so Section 4 stops being a memory dependency. (Gap 5 — bootstrap
docs — is handled directly under EPIC-004 as a concrete
README/QUICKSTART task rather than a paused-evaluation here.)

Each task is filed paused with a prerequisite that gates its activation:

- **Pipeline test-fixture corpus** (Gap 6) — activates when EPIC-006
  Stage 4 pipeline-glue task moves to active.
- **One-line parser test for IDEA-011 V1 output** (Gap 9) — activates
  when EPIC-008 V1 packaging task closes.

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
