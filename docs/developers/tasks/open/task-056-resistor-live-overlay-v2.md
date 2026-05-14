---
id: TASK-056
title: V2 — live overlay + per-frame stable decoding at ≥10 fps
status: open
opened: 2026-05-14
effort: Large (8-24h)
complexity: Senior
human-in-loop: Support
epic: resistor-reader
order: 6
prerequisites: [TASK-055]
---

## Description

V2 live-view mode from
[IDEA-011 § Scope (rough)](../../ideas/open/idea-011-resistor-color-band-detector.md#scope-rough).
Couples the trained detector from
[TASK-055](task-055-resistor-trained-detector-v2.md) with the
band-reading decoder from
[TASK-052](task-052-resistor-band-reading-eia.md) and renders a
live OpenCV viewfinder overlay: a bounding box plus the decoded
value labelled next to each visible resistor, updated per-frame at
≥10 fps with no visible flicker.

Three pieces:

1. **Camera loop**. Open the USB webcam (or any
   `cv2.VideoCapture`-compatible source — phone-as-webcam,
   PiCam) and iterate frames. Camera selection reuses
   [TASK-032](task-032-camera-selection-wizard.md)'s wizard
   friendly-name path; the user picks a camera, never a V4L2
   device index.
2. **Temporal smoothing**. Per-frame raw decoded values flicker
   when one band is on a focal-plane boundary or motion-blurred
   between frames. Smooth with a short rolling window per
   tracked resistor — Hungarian-algorithm matching across
   frames to keep the same resistor's identity, then a
   modal-value vote over the last K frames (K ~5-10). The
   overlay displays the smoothed value; if smoothing cannot
   stabilise (votes are evenly split across two candidates),
   display the candidate value with a "?" suffix.
3. **Overlay rendering**. OpenCV `cv2.rectangle` + `cv2.putText`
   per tracked resistor. Label text in PartsLedger schema format
   (`4k7`, `100R`). A small status line in the corner shows fps
   and a calibration indicator (calibrated / uncalibrated, per
   [IDEA-013](../../ideas/open/idea-013-capture-setup-and-color-calibration.md)
   loaded by TASK-054). Press `q` to quit; press `s` to dump
   the current frame plus its decoded report to disk for offline
   inspection.

Lives at `src/partsledger/resistor_reader/live.py`. Invoked via
the CLI added in TASK-054 with a `--live` flag:
`partsledger-resistor-reader --live`. No image path argument —
the camera is the input.

OpenCV viewfinder details (frame buffers, codec choice,
double-buffering) stay internal. The maker-facing surface is one
flag and two keystrokes.

## Acceptance Criteria

- [ ] `partsledger-resistor-reader --live` opens the maker's
      USB webcam (selected via the
      [TASK-032](task-032-camera-selection-wizard.md) wizard
      output) and displays a live OpenCV window.
- [ ] Decoded resistor values render next to each detected
      resistor on every frame.
- [ ] The displayed value is **stable** — no per-frame flicker
      on a stationary resistor over the standard test board.
- [ ] Frame rate is ≥10 fps on the maker's target hardware,
      measured against the same hardware profile as
      [TASK-055](task-055-resistor-trained-detector-v2.md)'s
      fps test.
- [ ] Calibration indicator in the overlay corner reflects
      whether [IDEA-013](../../ideas/open/idea-013-capture-setup-and-color-calibration.md)'s
      colour profile loaded successfully.
- [ ] `q` quits cleanly; `s` writes a snapshot + report pair to
      a configurable location (defaults under
      `$PL_INVENTORY_PATH/.snapshots/` with user-config fallback).
- [ ] No OpenCV / V4L2 detail surfaces in `--help` or error
      messages; the camera-selection wizard's friendly-name
      contract holds.

## Test Plan

Host tests (pytest) against fixture **video files** in
`tests/fixtures/resistor-reader/video/`:

- `tests/resistor_reader/test_live.py` — feed pre-recorded short
  clips through the live pipeline with a mocked
  `cv2.VideoCapture` and assert on the stream of decoded values
  per frame (stability across the clip, correctness on the
  ground-truth-labelled clip).
- Cover: a stationary single-resistor clip (assert zero
  flicker across all frames), a panning multi-resistor clip
  (assert each resistor keeps its identity through the pan), a
  motion-blurred clip (assert smoothing kicks in — output goes
  to "?" rather than wrong value).

Manual hardware test (required for sign-off):

- Run `partsledger-resistor-reader --live` on the maker's bench
  with the USB webcam pointed at the standard test board (mix
  of 1k, 4k7, 220 resistors).
- Observe: every resistor labelled correctly, no flicker, fps
  indicator ≥10, calibration indicator reflects whether the
  IDEA-013 profile is present.
- Press `s`, confirm the snapshot + report land at the expected
  location.
- Press `q`, confirm clean shutdown (window closed, camera
  released, no zombie process).

## Prerequisites

- **TASK-055** — supplies the trained detector / ONNX runtime
  this task wraps in a camera loop. Without V2's frame rate,
  the ≥10 fps target is unachievable.

## Sizing rationale

Live overlay couples the V2 detector with temporal smoothing
and OpenCV viewfinder rendering — splitting would create
partial wiring that can't be exercised until both halves exist.

## Notes

Tracker / matching choice (Hungarian vs IoU-greedy vs a
proper SORT-style tracker) is an implementation detail; pick
the simplest one that meets the stability acceptance criterion
and document the choice in a code comment. If a SORT-style
tracker turns out to be needed, file an ADR — the dependency
footprint deserves a record.
