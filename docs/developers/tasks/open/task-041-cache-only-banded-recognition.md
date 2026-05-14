---
id: TASK-041
title: Cache-only recognition with tight / tight_ambiguous / medium / miss bands
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: visual-recognition
order: 3
prerequisites: [TASK-040]
---

## Description

IDEA-007 Stage 2 — wrap the embed + cache primitives in a read-only
classifier: *given an image, return (band, top-1 candidate,
neighbour-labels)*. No VLM, no MD writes. Pure recognition that the
pipeline glue (TASK-043) calls into.

New module `src/partsledger/recognition/pipeline.py` (slim initial
version) exposes `classify(image) -> Verdict(band, top1_candidate,
neighbour_labels)`. Bands per IDEA-007 § Confidence bands:

- **tight** — nearest distance `< 0.10`, single distinct label in the
  tight neighbourhood. Single-match commit signal.
- **tight_ambiguous** — nearest distance `< 0.10`, but `nearest(vec, k=3)`
  returns *multiple distinct labels* within the tight threshold (the
  LM358N-vs-LM358P collision case from IDEA-007 § Three pipeline
  microdecisions). VLM disambiguation is required downstream.
- **medium** — `0.10 ≤ distance < 0.25`. VLM is mandatory; pipeline will
  surface a retry-or-abort prompt rather than auto-pick.
- **miss** — `distance ≥ 0.25` or empty cache. VLM is mandatory (or the
  maker rescans).

Thresholds are read from the `[recognition]` section of
`~/.config/partsledger/config.toml` with the placeholder defaults
above per IDEA-007 closed-Q *Confidence-band thresholds*. The values are
documented in code and overridable per-maker.

## Acceptance Criteria

- [ ] `classify()` returns the correct band at each threshold boundary (parametric tests at 0.05, 0.10, 0.20, 0.25, 0.30).
- [ ] Tight-band ambiguity: a cache pre-populated with two distinct labels within the tight threshold returns `tight_ambiguous`, not `tight`.
- [ ] Empty cache returns `miss` unconditionally.
- [ ] Thresholds load from `~/.config/partsledger/config.toml` `[recognition]` when present; otherwise fall back to documented defaults.
- [ ] Each band is exercised by at least one fixture in the test corpus.

## Test Plan

**Host tests** (pytest):

- Add `tests/recognition/test_pipeline_classify.py`.
- Cover: each band routed correctly (tight, tight_ambiguous, medium,
  miss); empty cache; config-file override of thresholds; defaults when
  no config file exists.
- Use a mock cache prepopulated with synthetic 768-D vectors at known
  distances — no real images, no real backbone. The end-to-end fixture
  pass against a real image set lives in TASK-043's manual-integration
  test, not here.

## Prerequisites

- **TASK-040** — provides `cache.nearest()`, which this task consumes for
  the band decision.
