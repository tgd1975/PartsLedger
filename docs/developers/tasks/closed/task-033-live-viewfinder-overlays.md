---
id: TASK-033
title: Live viewfinder + capture overlays (framing rect, focus, lighting, trigger hint)
status: closed
closed: 2026-05-14
opened: 2026-05-14
effort: Large (8-24h)
effort_actual: Medium (2-8h)
complexity: Senior
human-in-loop: Support
epic: usb-camera-capture
order: 2
prerequisites: [TASK-032]
---

## Description

Bring up the `cv2.imshow` viewfinder window with the four
capture-time overlays from
[IDEA-006 Stage 2](../../ideas/open/idea-006-usb-camera-capture.md#stage-2--live-viewfinder--capture-overlays).
This is the continuous-feedback surface the maker watches while
positioning a part — *is it in frame, in focus, evenly lit?* —
**before** committing the capture.

New module `partsledger/capture/viewfinder.py` exposes a
`Viewfinder` context manager. It opens
`cv2.VideoCapture(stable_id)` against the camera resolved by
TASK-032, pumps frames into `cv2.imshow`, and on exit calls
`cv2.destroyAllWindows()` + `.release()` — guaranteed by
`try…finally` per
[IDEA-006 § Window lifecycle](../../ideas/open/idea-006-usb-camera-capture.md#window-lifecycle).

Per-frame overlay decorators, all drawn on top of the live
frame:

- **Framing rectangle** at fixed working-distance pixel
  coordinates (configurable in `config.toml`); matches the
  rectangle physically marked on the mat so the maker lines
  the part up against the overlay, not against guesswork.
- **Focus indicator** — `cv2.Laplacian(frame, CV_64F).var()`
  mapped to a numeric reading plus green / amber / red
  traffic light, so a soft frame is visible *before* the
  trigger fires.
- **Lighting check** — mean luminance + max-channel clip count;
  the overlay turns amber when either is out of band (harsh
  shadows or blown highlights).
- **Trigger hint** — static text rendered at the bottom edge
  reminding the maker of the active hotkey (`<Space>`).

Stage 2 also wires the session lifecycle: window opens once at
session start, stays open across captures, and three quit
triggers all route through the same cleanup path —
`q` / `<Esc>` polled via `cv2.waitKey(...)`, WM-close polled
via `cv2.getWindowProperty(name, WND_PROP_VISIBLE) < 1`, and
`SIGINT` / `SIGTERM` via signal handlers. Capture-trigger
binding (`<Space>` → emit a still) is TASK-034's job; this
task wires only the quit paths.

Per-frame overlay crash handling per
[IDEA-006 § Pipeline failure modes](../../ideas/open/idea-006-usb-camera-capture.md#pipeline-failure-modes--what-the-camera-path-does-when-something-breaks):
a crashing overlay disables that overlay for the rest of the
session and renders a small *"focus / lighting / framing
overlay off"* breadcrumb — it does **not** kill the session.

## Acceptance Criteria

- [x] `partsledger/capture/viewfinder.py` exposes a
      `Viewfinder` context manager that opens the camera,
      pumps `cv2.imshow`, and guarantees `release()` +
      `destroyAllWindows()` on exit (any of: normal return,
      exception, signal).
- [x] All four overlay decorators render correctly on top of
      the live feed: framing rectangle at the configured
      coordinates, Laplacian-variance focus traffic light,
      mean-luminance / clipping lighting indicator,
      trigger-hint text.
- [x] Window opens once at session start, stays open across
      multiple frame-grab iterations, closes cleanly on
      `q` / `<Esc>` / WM-close / `SIGINT` / `SIGTERM` — same
      cleanup path for all five.
- [x] Overlay decorators sustain >= 30 fps on the dev hardware.
- [x] A crashing per-frame overlay disables that overlay
      and surfaces a corner *"overlay off"* breadcrumb —
      session keeps running.

## Test Plan

**Host tests (pytest)** — `tests/capture/test_viewfinder.py`:

- Unit-test the overlay decorators against fixture frames:
  Laplacian variance maps to the expected traffic-light band,
  mean luminance triggers the lighting warning at the right
  threshold, framing-rectangle pixel coordinates are read
  correctly from a fixture `config.toml`.
- Verify the overlay-crash isolation: an injected exception in
  one decorator disables only that overlay and the others keep
  rendering.
- Mock `cv2.VideoCapture` to verify the `try…finally` cleanup
  path runs on all five exit triggers.

**Manual hardware test** — required because real `cv2.imshow`
needs a display backend and the 2K USB webcam:

- Run the viewfinder; verify the framing rectangle, focus
  traffic light, lighting indicator, and trigger hint all
  render and update in real time.
- Verify each quit path independently: `q`, `Esc`, WM-close
  button, `Ctrl-C` in the parent terminal, `kill <pid>`.
- Measure overlay-decoration frame rate on dev hardware
  (Ubuntu host + Windows 11 host).

## Prerequisites

- **TASK-032** — supplies `resolve_camera()` so the viewfinder
  knows which stable device id to open.

## Sizing rationale

Overlay system shares one OpenCV render pipeline across four
indicators; splitting would create coordination overhead between
separate draw passes.

## Notes

The viewfinder also has to double as the recognition-status
surface (Idle / Analyzing / Retry-or-abort / Confirmation
flash) — but that state machine is TASK-036's job. This task
delivers only the Idle-state overlays.
