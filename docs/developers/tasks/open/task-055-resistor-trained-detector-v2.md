---
id: TASK-055
title: V2 — small trained detector (YOLO-nano / MobileNet-SSD) for live-view localisation
status: open
opened: 2026-05-14
effort: Large (8-24h)
complexity: Senior
human-in-loop: Support
epic: resistor-reader
order: 5
prerequisites: [TASK-054]
---

## Description

V2 of the localisation half from
[IDEA-011 § Two modes](../../ideas/open/idea-011-resistor-color-band-detector.md#two-modes).
The V1 HSV-thresholding approach
([TASK-051](task-051-resistor-localisation-v1.md)) is fine for
still photos but too brittle for the live-view case — motion blur,
cluttered bench backgrounds, varying focus distance, and the
≥10 fps realtime budget all break the classical pipeline. V2
replaces the localiser with a small trained object detector while
keeping the band-reading / EIA-classifier stage from
[TASK-052](task-052-resistor-band-reading-eia.md) intact.

Four moving parts inside this task:

1. **Dataset curation.** Assemble a labelled training set:
   bench photos, viewfinder grabs, off-bench phone shots,
   varied lighting tiers per
   [IDEA-013 § Setup tiers](../../ideas/open/idea-013-capture-setup-and-color-calibration.md#setup-tiers).
   Initial target ~500-1000 labelled frames. Labels are
   resistor-body bounding boxes; orientation is left to the
   downstream band reader.
2. **Architecture choice.** Run a one-day bake-off between
   YOLO-nano and MobileNet-SSD on the maker's target hardware
   (the bench laptop, not a server GPU). The decision criterion
   is inference latency at ≥10 fps with mAP no worse than V1 on
   the V1 fixture set. The losing architecture stays
   unmentioned in the final code; an ADR captures the bake-off
   numbers.
3. **Training pipeline + ONNX export.** Reproducible training
   script under `src/partsledger/resistor_reader/training/` plus
   an ONNX export step so the runtime side does not pull in the
   training framework at inference time. The trained ONNX
   weights ship alongside the package (or download on first
   use — decide based on file size).
4. **Runtime integration.** Replace `localise.py`'s
   `locate_resistors` with a version that calls the ONNX model
   via `onnxruntime`. The function signature stays identical so
   [TASK-052](task-052-resistor-band-reading-eia.md)'s decoder
   and [TASK-053](task-053-resistor-uniformity-check.md)'s
   uniformity check are unaffected. A `--v1` CLI flag on the
   `partsledger-resistor-reader` entry point lets the maker
   force the classical path for debugging.

PyTorch becomes a hard dependency of the `resistor-reader`
extra for training; `onnxruntime` for inference. Per
[IDEA-011's packaging closure](../../ideas/open/idea-011-resistor-color-band-detector.md#open-questions)
this is acceptable — the heavy CV deps live behind the extra
and the bare `pip install partsledger` is unaffected.

## Acceptance Criteria

- [ ] Labelled training set of ≥500 frames lives under
      `tests/fixtures/resistor-reader/training/` (or a separate
      git-LFS / external store if size warrants — capture the
      decision in an ADR).
- [ ] Training script under
      `src/partsledger/resistor_reader/training/train.py`
      reproduces the published weights from the dataset in a
      single command.
- [ ] ONNX export step produces weights consumed by
      `onnxruntime` with no PyTorch import at inference.
- [ ] Trained model achieves ≥10 fps localisation on the
      maker's target hardware (measured wall-clock, single
      thread) and mAP comparable to V1 on the V1 fixture set.
- [ ] `locate_resistors`'s public signature is unchanged from
      V1; existing TASK-052 and TASK-053 tests pass unmodified
      with the V2 localiser plugged in.
- [ ] A `--v1` CLI flag forces the classical localiser, useful
      for A/B comparisons and for debugging when the ML
      pipeline misbehaves.
- [ ] Architecture choice (YOLO-nano vs MobileNet-SSD) is
      documented in an ADR with the bake-off numbers.

## Test Plan

Host tests (pytest) against fixtures in
`tests/fixtures/resistor-reader/`:

- `tests/resistor_reader/test_localise_v2.py` — same fixture
  set as `test_localise.py` from TASK-051, asserting V2 matches
  or beats V1's candidate counts and bbox geometry.
- `tests/resistor_reader/test_fps.py` — synthetic timing test
  running the V2 localiser on N frames and asserting the
  per-frame latency budget. Skipped on CI runners that don't
  match the target-hardware profile (gate via an env-var or a
  pytest marker).
- Manual hardware test: run the `--v1` and default CLI back-to-
  back on the bench, eyeball the bbox outputs on the canonical
  fixtures, confirm parity.

## Prerequisites

- **TASK-054** — wires the CLI entry-point and the calibration-
  profile load. V2 plugs into the same CLI surface and the same
  profile-loading code path.

## Sizing rationale

V2 detector spans dataset curation, training, ONNX export, and
runtime integration — splitting would create partial states where
the training pipeline produces a model the runtime can't load.

## Notes

The bake-off ADR also needs to record whether the trained
weights ship with the wheel (simpler install, larger
distribution) or download on first use (smaller wheel, requires
network on first invocation). The decision is the user's;
default lean is "ship in wheel" if the weights are under ~10 MB.
