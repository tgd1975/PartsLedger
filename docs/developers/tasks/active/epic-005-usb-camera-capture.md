---
id: EPIC-005
name: usb-camera-capture
title: USB camera capture
status: open
opened: 2026-05-14
closed:
assigned:
branch: feature/usb-camera-capture
---

Seeded by IDEA-006 (USB camera capture).

The hand-eye loop — camera-selection wizard, viewfinder + capture
overlays, capture trigger, recognition-status overlay state machine,
secondary key dispatch, CLI wrapper, and the thin `/capture` slash-skill.

Phase placement:

- **Phase 1** — Stages 1–3 (wizard, viewfinder, trigger) + Stage 6
  (CLI wrapper). Useful as fixture source for EPIC-006 development.
- **Phase 2** — Stage 4 overlay state machine (pairs with EPIC-006
  Stage 4 verdict payload — the integration choke-point).
- **Phase 3** — Stage 5 secondary key dispatch (`R` / `X` / `U`;
  depends on EPIC-006 Stage 5 undo journal for `U`).
- **Phase 4** — Stage 7 `/capture` slash-skill subprocess wrapper.

Design is fully honed (10 decisions logged 2026-05-13/14 in IDEA-006).
No code yet.

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
