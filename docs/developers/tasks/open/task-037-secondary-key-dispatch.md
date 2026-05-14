---
id: TASK-037
title: Secondary key dispatch — R / X / U handlers
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: Support
epic: usb-camera-capture
order: 6
prerequisites: [TASK-036, TASK-044]
---

## Description

Wire the contextual keys — `R`, `X`, `U` — to their handlers
per [IDEA-006 Stage 5](../../ideas/open/idea-006-usb-camera-capture.md#stage-5--secondary-key-dispatch-r--x--u).
With this task landed, the full key-dispatch table from
[IDEA-006 § Key dispatch](../../ideas/open/idea-006-usb-camera-capture.md#key-dispatch)
is realised.

Three handlers:

- **`R` (retry)** — legal only in the *Retry-or-abort prompt*
  state from TASK-036. Resets the viewfinder to *Idle* and
  re-enters the per-capture loop (effectively a silent
  re-trigger; the maker does not have to press `<Space>` again).
- **`X` (abort / escalate)** — legal only in *Retry-or-abort*.
  Calls into [IDEA-005 `/inventory-add`](../../ideas/open/idea-005-skill-path-today.md)
  with the captured image as context; the maker types the
  part-ID manually from there. From the camera path's
  perspective, the session continues — `/inventory-add` runs
  to completion and control returns to the *Idle* state ready
  for the next part.
- **`U` (undo)** — legal during *Confirmation flash* and for
  ~5 s after. Calls
  [EPIC-006 Stage 5 `undo_last()`](../../ideas/open/idea-007-visual-recognition-dinov2-vlm.md#stage-5--undo-journal)
  via the undo-journal API delivered in TASK-044. Surfaces
  *"reverted"* on the viewfinder on success, or *"undo
  failed"* if the journal couldn't unwind cleanly. Depth is
  1 — the next write moves the journal pointer and the
  previous one becomes unreachable.

Unknown keys, and `R` / `X` / `U` pressed in the wrong state,
are ignored silently per
[IDEA-006 § Key dispatch](../../ideas/open/idea-006-usb-camera-capture.md#key-dispatch)
— no error overlay, no beep. Numeric digits are reserved for
a future top-N picker and stay ignored today.

## Acceptance Criteria

- [ ] `R` during *Retry-or-abort* re-enters the capture loop
      without an intervening `<Space>` press; the viewfinder
      returns to *Idle* with the framing overlays back on.
- [ ] `X` during *Retry-or-abort* invokes `/inventory-add` with
      the captured image as context; the resulting MD write
      lands in `inventory/parts/<part>.md` just as if the
      maker had typed the command directly.
- [ ] `U` after a confirmation flash invokes
      `pipeline.undo_last()` (from TASK-044); on success the
      viewfinder shows *"reverted"*, on failure *"undo
      failed"*.
- [ ] `U` more than ~5 s after the confirmation flash is
      silently ignored.
- [ ] Pressing `R` or `X` in *Idle* does nothing visible;
      numeric digits are ignored everywhere.

## Test Plan

**Host tests (pytest)** — `tests/capture/test_secondary_keys.py`:

- Drive the state machine into each of the four states; for
  every state, press every key in {R, X, U, 0-9, random} and
  assert the right handler fires or is silently dropped.
- Mock `/inventory-add` and assert `X` invokes it with the
  captured image; mock `pipeline.undo_last()` and assert `U`
  invokes it; assert *"reverted"* / *"undo failed"* render
  appropriately.
- Time-bound the `U` window: keypress at T+0 and at T+4 s
  fires; keypress at T+6 s is dropped.

**Manual hardware test** — required to feel out the timing of
the U-to-undo window in practice:

- After a successful auto-write, press `U` within the flash
  window; verify the write reverses and the viewfinder shows
  *"reverted"*.
- Press `U` after the window closes; verify nothing happens
  (no beep, no visible feedback).
- Trigger `X` from a Retry-or-abort prompt; verify
  `/inventory-add` opens with the captured image visible to
  the maker.

## Prerequisites

- **TASK-036** — supplies the state machine; secondary keys
  are state-gated, so the machine has to exist first.
- **TASK-044** — supplies the `pipeline.undo_last()` API and
  the undo journal in EPIC-006 Stage 5 that `U` calls into.
