---
id: TASK-036
title: Recognition-status overlay state machine + hint-family tokeniser
status: open
opened: 2026-05-14
effort: Large (8-24h)
complexity: Senior
human-in-loop: Support
epic: usb-camera-capture
order: 5
prerequisites: [TASK-035, TASK-043]
---

## Description

Drive the four-state recognition-status overlay machine from
[IDEA-006 Stage 4](../../ideas/open/idea-006-usb-camera-capture.md#stage-4--recognition-status-overlay-state-machine).
This is where the camera path becomes a real partner to the
recognition pipeline: the viewfinder doubles as the
recognition-status surface, and every state of the recognition
flow renders on the same window the maker is already looking
at — no separate terminal, TUI, or window.

Four display states per
[IDEA-006 § Overlays during recognition](../../ideas/open/idea-006-usb-camera-capture.md#overlays-during-recognition):

- **Idle / positioning** — capture overlays from TASK-033, plus
  an optional *"last result"* breadcrumb in a corner.
- **Analyzing** — captured frame **frozen** in the main area +
  small **live thumbnail** of the camera feed in a corner;
  *"Identifying…"* status text with a spinner.
- **Retry-or-abort prompt** — frozen frame stays; if the
  verdict was *VLM needs-re-frame*, the VLM's hint string
  overlays the frame (tokenised — see below); small confidence-
  band breadcrumb; *R retry · X abort* action prompt.
- **Confirmation flash** — *"Saved as LM358N — qty 5 → 6"* for
  ~1 s, annotated *"via VLM"* when the pipeline reached the
  *VLM hedged ID* branch; *U to undo* stays as a corner hint
  for a few seconds after the flash fades.

Changes:

- `Viewfinder` gains `set_state(state, payload)` — clean
  transitions between the four states. Each state has its own
  per-state overlay renderer.
- Frozen-frame + live-thumbnail compositing for *Analyzing*;
  verdict-label + hint-string + R/X prompt for *Retry-or-abort*;
  flash text + *via VLM* annotation + corner *U-to-undo* hint
  for *Confirmation flash*.
- **Hint-family tokeniser** per
  [IDEA-006 § Recognition-state hints](../../ideas/open/idea-006-usb-camera-capture.md#recognition-state-hints):
  short hint string in, one of seven family-shapes out
  (angle/orientation, lighting, sharpness, framing,
  surface/background, distance, marking state). Unknown
  strings fall through to the generic *"image unclear —
  recompose and retry"*.
- **State-transition contract** with EPIC-006's pipeline: the
  viewfinder exposes `begin_analyzing(captured_frame)`,
  `show_retry_or_abort(hint)`, `flash_confirmation(text,
  via_vlm)`, and `return_to_idle()`. The pipeline (TASK-043 in
  EPIC-006) calls these; the viewfinder never inspects the
  verdict payload itself, just renders what it is told.

The verdict-payload **schema** is owned by EPIC-006 / TASK-043;
this task implements the renderer side of the contract. The
tokeniser is the only place IDEA-006 inspects a string the VLM
produced, and it does so via fixed family rules — no
LLM-side parsing.

## Acceptance Criteria

- [ ] `Viewfinder.set_state(state, payload)` exists and cleanly
      transitions between Idle / Analyzing / Retry-or-abort /
      Confirmation flash; transitions are idempotent (re-entering
      the same state is a no-op).
- [ ] Each state has a correct per-state overlay renderer:
      frozen-frame + live thumbnail for Analyzing; verdict
      label + hint + R/X prompt for Retry-or-abort; flash text
      + *via VLM* annotation + U-to-undo for Confirmation flash.
- [ ] Hint-family tokeniser classifies sample strings into the
      seven families correctly; unknown strings collapse to the
      generic *"image unclear — recompose and retry"*.
- [ ] *Confirmation flash* auto-times-out back to *Idle* after
      ~1 s; the corner *U-to-undo* hint persists for ~5 s
      after the flash itself fades.
- [ ] The *Analyzing*-state live thumbnail keeps updating even
      though the main frame is frozen.
- [ ] The state-transition API (`begin_analyzing`,
      `show_retry_or_abort`, `flash_confirmation`,
      `return_to_idle`) matches what TASK-043 expects.

## Test Plan

**Host tests (pytest)** — `tests/capture/test_state_machine.py`:

- Drive `set_state` through every legal transition with mocked
  payloads; verify each overlay renderer is called.
- Hint-family tokeniser: table-driven test with sample strings
  for each of the seven families plus several unknown strings;
  verify correct family classification and the generic
  fall-through.
- Verify the *Confirmation flash* auto-timeout fires at the
  configured interval and the corner *U-to-undo* hint persists
  the configured extra time.
- Verify the live-thumbnail composer keeps grabbing fresh
  frames while the main frame is frozen (mock frame source).

**Manual hardware test** — required because rendering quality
and timing only show up on the real viewfinder:

- Drive a mocked pipeline through all four state transitions
  in sequence; eyeball each overlay against the spec.
- Verify the live thumbnail in *Analyzing* updates in real
  time while the main image stays frozen.
- Verify the confirmation flash duration and the U-to-undo
  fade timing look right (i.e. the maker has time to react).

## Prerequisites

- **TASK-035** — supplies the CLI entry-point that hosts the
  Viewfinder; integration tests for the state machine run
  through it.
- **TASK-043** — EPIC-006's pipeline orchestrator that emits
  the verdict payload this state machine renders. The
  contract is the integration choke-point.

## Sizing rationale

State machine + token mapping are one coherent contract with
EPIC-006's pipeline verdict; splitting would create dead-code
states that can't be exercised until the integration partner
exists.

## Notes

The maker never sees a `Y accept` prompt or a numbered top-3
picker — those were assumptions of an older pipeline. Numeric
keys remain reserved for a future top-N picker; the secondary
key dispatch (TASK-037) ignores them silently for
forward-compatibility.
