---
id: TASK-051
title: V1 — resistor localisation (HSV thresholding + contour finding) on still images
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: Support
epic: resistor-reader
order: 1
prerequisites: [TASK-022, TASK-029]
---

## Description

First half of the V1 still-image pipeline from
[IDEA-011 § Rough approach #1](../../ideas/open/idea-011-resistor-color-band-detector.md#rough-approach).
Given a single off-bench photo of one or more through-hole axial
resistors, locate each resistor body and return a bounding box per
body. V1 stays dependency-light: classical CV only (OpenCV HSV
thresholding on the typical beige / blue body colours, followed by
contour finding and minimum-area-rectangle fitting). No PyTorch on
this path — that is reserved for V2 ([TASK-055](task-055-resistor-trained-detector-v2.md)).

Lives at `src/partsledger/resistor_reader/localise.py` under the
`src/` layout that [TASK-022](task-022-adopt-src-layout.md)
establishes. The module exposes a single function returning a
ranked list of candidate bounding boxes with per-candidate
confidence — callers downstream
([TASK-052](task-052-resistor-band-reading-eia.md)) consume the
top candidates and reject low-confidence ones.

OpenCV HSV ranges, morphology kernel sizes, and contour-area
thresholds are implementation detail and stay inside this module —
they must never surface in CLI flags or error messages the maker
sees. The maker-facing surface is the
`partsledger-resistor-reader` CLI added in
[TASK-054](task-054-resistor-extra-packaging.md); this task is
strictly the localisation primitive that CLI calls into.

## Acceptance Criteria

- [ ] `src/partsledger/resistor_reader/localise.py` exposes
      `locate_resistors(image) -> list[Candidate]` where each
      `Candidate` carries a bounding box (or rotated rect),
      orientation hint (body axis), and a confidence score.
- [ ] Localisation succeeds (≥1 candidate above a sensible
      confidence floor) on the standard well-lit single-resistor
      test image fixture.
- [ ] Multi-resistor frames return one candidate per visible body
      on the canonical multi-resistor fixture.
- [ ] Ambiguous frames (low contrast, cluttered background) return
      a ranked list of candidates rather than a single guess; the
      ranking is by confidence descending.
- [ ] No OpenCV detail (HSV ranges, kernel sizes, contour
      thresholds) appears in the module's public API surface.

## Test Plan

Host tests (pytest) against the fixture image set checked into
`tests/fixtures/resistor-reader/`:

- `tests/resistor_reader/test_localise.py` — load each fixture,
  call `locate_resistors`, assert on candidate count and bbox
  geometry (centre roughly matches the ground-truth annotation
  shipped alongside each fixture as a small JSON sidecar).
- Cover at minimum: single well-lit resistor, three resistors in
  a row, one resistor on a busy background, one resistor
  partially out of frame (expect rejected or low confidence).

## Prerequisites

- **TASK-022** — establishes the `src/partsledger/` layout that
  `resistor_reader/` lives inside.
- **TASK-029** — registers the optional-extras mechanism so the
  CV dependencies introduced here can live behind
  `partsledger[resistor-reader]` rather than core install.

## Notes

The fixture set is the same one [TASK-052](task-052-resistor-band-reading-eia.md)
will consume — establishing it here costs nothing extra and gives
the next task a working baseline to test against.
