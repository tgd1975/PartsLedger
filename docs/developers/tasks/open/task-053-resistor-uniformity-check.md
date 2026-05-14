---
id: TASK-053
title: V1 — uniformity check (strict, every deviation flagged)
status: open
opened: 2026-05-14
effort: Small (<2h)
complexity: Medium
human-in-loop: No
epic: resistor-reader
order: 3
prerequisites: [TASK-051]
---

## Description

Bench-side batch sanity check from
[IDEA-011 § Motivation #2](../../ideas/open/idea-011-resistor-color-band-detector.md#motivation):
given a photo of N resistors the maker believes are all the same
value, report whether the batch is uniform or mixed, and if mixed
list every deviation with its position in the frame.

Per the
[IDEA-011 open-Q closure on uniformity](../../ideas/open/idea-011-resistor-color-band-detector.md#open-questions)
the check is **strict** — cluster on the raw decoded value with no
confidence weighting, report the modal value, and surface every
single resistor whose decoded value differs from the mode,
regardless of its individual confidence score. Low confidence on
an outlier is itself a reason to show it (re-shoot, inspect by
hand), not a reason to discount it.

Lives at `src/partsledger/resistor_reader/uniformity.py`. Public
surface: one function taking the list of `DecodedResistor` outputs
from [TASK-052](task-052-resistor-band-reading-eia.md) and
returning a `UniformityReport` with `modal_value`, `uniform: bool`,
and `deviations: list[Deviation]` where each `Deviation` carries
the decoded value, the position (bbox centre), and the per-band
confidence breakdown.

## Acceptance Criteria

- [ ] `src/partsledger/resistor_reader/uniformity.py` exposes
      `check_uniformity(decoded: list[DecodedResistor])
      -> UniformityReport`.
- [ ] A strip of identical 1k resistors (fixture) returns
      `uniform=True` with an empty deviations list.
- [ ] A mixed-value strip (fixture: four 1k + one 4k7) returns
      `uniform=False` with exactly one deviation listed at the
      correct position.
- [ ] Per-resistor confidence appears in each `Deviation` record
      for inspection — the check does not discard it.
- [ ] No averaging, no confidence-weighted smoothing — the
      clustering is on raw decoded values.

## Test Plan

Host tests (pytest) against fixtures in
`tests/fixtures/resistor-reader/`:

- `tests/resistor_reader/test_uniformity.py` — feed synthetic
  lists of `DecodedResistor` values (no image needed for these
  unit tests) plus one end-to-end fixture (the mixed-strip
  photo) through the full localise → decode → uniformity chain.
- Cover: all-same case, one-outlier case, multi-mode case
  (three 1k + two 4k7 — modal value is 1k, both 4k7s appear as
  deviations), low-confidence outlier (still listed).

## Prerequisites

- **TASK-051** — supplies the bbox positions used as "position
  in the frame" in deviation records. The decoded values
  themselves come from [TASK-052](task-052-resistor-band-reading-eia.md),
  which is not a strict prerequisite for this module (it consumes
  `DecodedResistor` instances that can be constructed directly in
  tests) but is needed for end-to-end runs.

## Notes

The module is small and self-contained — the heart of it is a
collections.Counter call on the decoded values plus a list
comprehension for the deviations. The work is in the test
fixtures and in keeping the report format aligned with what
[TASK-054](task-054-resistor-extra-packaging.md)'s CLI will
print.
