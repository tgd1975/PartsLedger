---
id: EPIC-006
name: visual-recognition
title: Visual recognition — DINOv2 + VLM
status: open
opened: 2026-05-14
closed:
assigned:
branch: feature/visual-recognition
---

Seeded by IDEA-007 (Visual recognition — DINOv2 + VLM).

The brain of the camera path — DINOv2 embeddings, sqlite-vec cache,
banded recognition (tight / tight_ambiguous / medium / miss), VLM
adapter with structured verdicts, the pipeline glue that wires
everything together, and the undo journal.

Phase placement:

- **Phase 1** — Stages 1–3 (embed module, cache, VLM adapter). Unit-
  testable primitives; no inventory writes yet.
- **Phase 2** — Stage 4 pipeline glue. **Integration choke-point** —
  first runtime exercise of the EPIC-002 writer contract and first
  end-to-end wiring of EPIC-005 + EPIC-006 + EPIC-007.
- **Phase 3** — Stage 5 undo journal (`U` key reverses qty++ AND
  cache row in one transaction).

Design is fully honed (11 closed open-Qs in IDEA-007). No code yet.

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
