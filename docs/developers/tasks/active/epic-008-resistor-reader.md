---
id: EPIC-008
name: resistor-reader
title: Resistor color-band reader
status: open
opened: 2026-05-14
closed:
assigned:
branch: feature/resistor-reader
---

Seeded by IDEA-011 (Resistor color-band detector) and IDEA-013
(Capture setup + color calibration).

Standalone sibling tool for off-bench / no-VLM use, shipped as
`pip install partsledger[resistor-reader]` extra. Reads resistor color
bands from still images (V1) or live viewfinder frames (V2); the value
copies into Workflow A (skill path) via `/inventory-add`.

Phase placement:

- **Phase 6** — V1 (HSV thresholding, contour finding, EIA classifier,
  uniformity check, packaging as extra) then V2 (trained detector,
  live overlay, per-frame stable decoding ≥10 fps).

Gated on EPIC-004 Phase 0b for the package layout and the
`[project.optional-dependencies]` extra. Design is done.

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
