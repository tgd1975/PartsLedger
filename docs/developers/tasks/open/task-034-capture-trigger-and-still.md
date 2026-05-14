---
id: TASK-034
title: Capture trigger + single-still emit per Output contract
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Medium
human-in-loop: Support
epic: usb-camera-capture
order: 3
prerequisites: [TASK-033]
---

## Description

Wire the `<Space>` capture trigger to a single-still emit per
[IDEA-006 Stage 3](../../ideas/open/idea-006-usb-camera-capture.md#stage-3--capture-trigger--single-still).
With this task landed, the camera path becomes useful — each
`<Space>` press freezes the current frame and yields a clean
`(image, metadata)` packet that downstream stages
([IDEA-007 § Stage 4 `pipeline.run(image)`](../../ideas/open/idea-007-visual-recognition-dinov2-vlm.md#stage-4--pipeline-glue--branching))
can consume.

Changes:

- `Viewfinder` gains a `capture() -> (image, metadata)` method.
  `image` is the most recent frame as `np.ndarray (H, W, 3)`,
  BGR uint8 — OpenCV's native emit, **no conversion** (per the
  Output contract).
- The key-dispatch loop binds `<Space>` to `capture()` and
  yields the result via a callback or async channel so the
  caller (TASK-035's CLI; eventually IDEA-007's pipeline) can
  consume it. The viewfinder itself stays loop-less — exactly
  one still per `<Space>` press.
- The metadata dict is populated per
  [IDEA-006 § Output contract](../../ideas/open/idea-006-usb-camera-capture.md#output-contract-to-downstream):

```text
metadata: {
  timestamp: ISO 8601,
  camera: {
    name: str,           # friendly name from TASK-032's resolver
    stable_id: str,      # /dev/v4l/by-id/... on Linux, DirectShow id on Windows
  },
  resolution: (W, H),
  trigger: "keyboard",   # pedal is just a BLE-HID keyboard
}
```

- Filename convention for the optional `--dump-captures-to`
  debug surface (added by TASK-035) is the `timestamp` field
  above, suffix `.png`.

Per [IDEA-006 § Pipeline failure modes](../../ideas/open/idea-006-usb-camera-capture.md#pipeline-failure-modes--what-the-camera-path-does-when-something-breaks):
~5 consecutive frame-grab failures is treated as
*camera disappeared* — cleanup runs, the maker sees a
*"camera lost — `<friendly name>`"* error overlay, and the
camera path exits non-zero. Isolated single-frame failures are
swallowed.

## Acceptance Criteria

- [ ] `<Space>` press yields exactly one `np.ndarray` with shape
      `(H, W, 3)` and dtype `uint8`, BGR.
- [ ] Metadata dict carries the camera's friendly name and
      stable id byte-identically to what TASK-032 persisted;
      timestamp is ISO 8601; resolution matches the open device;
      `trigger` is the literal string `"keyboard"`.
- [ ] The same captured frame fed into a no-op downstream stub
      produces a deterministic non-zero hash — i.e. the array
      isn't a stale buffer.
- [ ] 5 consecutive frame-grab failures trigger the
      *"camera lost"* exit path with non-zero exit code.

## Test Plan

**Host tests (pytest)** — `tests/capture/test_capture.py`:

- Mock `cv2.VideoCapture.read()` with a fixture frame; verify
  `capture()` returns the expected ndarray shape, dtype, and
  bytes-identical content; verify the metadata dict fields
  match the fixture inputs.
- Inject 5 consecutive failing `read()` calls and assert the
  *camera disappeared* exit path fires; assert isolated single
  failures don't fire it.

**Manual hardware test** — required because the trigger UX is
the user-facing core of the camera path:

- Tap `<Space>` with a part under the camera; verify one
  capture lands, no double-fire, no swallowed trigger.
- Tap multiple times in succession; each press yields a fresh
  still (no stale buffer).
- Unplug the camera mid-session; verify the
  *"camera lost — `<friendly name>`"* overlay appears and the
  process exits cleanly.

## Prerequisites

- **TASK-033** — supplies the `Viewfinder` context manager and
  the per-frame overlay pipeline that the trigger binds into.

## Notes

The pedal (AwesomeStudioPedal, sibling project) collapses
into the same `<Space>` keypress at the OS level — no
PartsLedger code change is needed for pedal support. `trigger`
is hardcoded to `"keyboard"` because that's all PartsLedger
ever sees.
