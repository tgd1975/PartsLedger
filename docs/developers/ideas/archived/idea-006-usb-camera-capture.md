---
id: IDEA-006
title: USB camera capture — the camera-path front door
description: How the 2K USB webcam sees a part. Camera-selection wizard, live viewfinder (capture overlays + recognition-status overlays), key dispatch (Space / R / X / U / q), session lifecycle. The first toolchain stage that has to be reliable before anything downstream is worth tuning.
category: camera-path
---

## Archive Reason

2026-05-14 — Promoted to EPIC-005 (usb-camera-capture), tasks TASK-032..TASK-038.

> *Replaces the camera-path "USB camera capture" stage from the retired
> IDEA-001 dossier.* The cheap, well-understood part of the camera
> pipeline — but only **after** the capture ergonomics are nailed. A
> downstream VLM cannot recover from a blurry, off-axis, badly lit photo.

## Status

⏳ **Planned.** No code yet. The 2K USB webcam is already on the desk.
A first-run wizard (see [Camera selection](#camera-selection--pick-once-re-prompt-on-failure))
picks which capture device is used; `$PL_CAMERA` survives as an
optional override for headless or scripted use.

## What this stage owns

The pipeline edge between the physical part on the bench and the first
in-memory image tensor:

```text
hardware → OpenCV → numpy image
                       │
                       ▼
              downstream stages (IDEA-007)
```

Concretely: opening the camera device, framing/cropping the part,
triggering capture, handing a clean image to the recognition stage. **No
identification work happens here** — that's [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md).

## Runtime flow — what happens when the maker triggers a capture

End-to-end sequence for one invocation. The sections after this one
describe *how each step works* in isolation; this is what knits them
together.

**One invocation = one session = many captures.** The flow has three
phases: a *session init* that runs once at startup, a *per-capture
loop* that repeats for every part the maker holds under the camera,
and a *session cleanup* that runs once on exit.

### Session init (once per invocation)

1. **Entry-point.** Maker starts the camera path. Exact form (CLI,
   slash-skill, Python module) is still open — see
   [Open questions](#open-questions-to-hone).
2. **Camera resolve.** Read the persisted choice from the
   `[camera]` section of `~/.config/partsledger/config.toml` (see
   [IDEA-007 § Configuration files](idea-007-visual-recognition-dinov2-vlm.md#configuration-files)
   for the file convention). If it resolves to a real, openable
   device, continue silently. Otherwise enter the
   [first-run wizard](#camera-selection--pick-once-re-prompt-on-failure)
   and re-pick. Failure here is loud — never silently fall through
   to "the first available camera".
3. **Device open.** `cv2.VideoCapture(<stable_id>)` against the
   resolved camera; pre-flight `.isOpened()`. On open failure, treat
   it as an unresolved persisted choice and loop back to step 2.
4. **Viewfinder up.** Open the [`cv2.imshow` window](#live-viewfinder--required)
   once (see [Window lifecycle](#window-lifecycle) for the
   open-stays-closes contract). Start streaming frames; each one is
   decorated with the framing rectangle, focus traffic-light
   (Laplacian variance), lighting check, and trigger-hint overlay.

### Per-capture loop (repeats for every part)

1. **Wait for trigger.** Maker positions the part against the
   framing overlay, watches the focus / lighting indicators, taps
   `<Space>` — either directly on the keyboard or via the BLE-HID
   [AwesomeStudioPedal](../../../../../AwesomeStudioPedal/README.md)
   foot pedal. The stage sees only the keypress; the input source
   is invisible to it.
2. **Single still.** Freeze the current frame. It is already a
   `numpy.ndarray (H, W, 3), BGR uint8` — OpenCV's native emit, no
   conversion needed. Package with the metadata block from
   [Output contract](#output-contract-to-downstream). Downstream
   consumers do their own format adaptation (PyTorch
   `torch.from_numpy(...)` for DINOv2 — shared-memory view; PNG
   encode for the VLM).
3. **Hand off to IDEA-007.** Return the image + metadata to the
   recognition stage. One iteration of this loop = exactly one
   still. The stage does **not** know whether the still was good
   enough; that's IDEA-007's call.
4. **Loop back, maybe.** If IDEA-007 returns a re-frame hint, the
   viewfinder surfaces it as an extra overlay and the maker triggers
   again. The loop itself is owned by
   [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md#the-re-frame-loop--looping-around-idea-006);
   from IDEA-006's perspective, it is simply another iteration of
   the same loop.

### Session cleanup (once on exit)

1. **Session end.** Triggered by any one of: maker presses `q` /
   `Esc` on the focused viewfinder, the viewfinder window is closed
   from the WM (X button / Alt-F4), a signal interrupt arrives
   (`SIGINT`, `SIGTERM`), or the camera path's caller returns
   normally. A `try…finally` around the whole session guarantees
   the cleanup steps below run regardless of how the end arrived:
   - In-flight recognition (a VLM call in IDEA-007) is allowed to
     finish, bounded by a hard timeout (~30 s), but its result is
     **discarded** — never written to inventory. Consistent with
     [Image retention](#decisions-2026-05-13-hone): nothing
     unconfirmed lives past session end.
   - All captured frames from this session are discarded.
   - `cv2.destroyAllWindows()` releases the viewfinder window.
   - `cv2.VideoCapture.release()` releases the camera device.

## Hardware assumptions

- **Camera**: 2K USB webcam already in use (the maker's own; brand-
  agnostic). Connected via USB-A. The host typically exposes other
  capture devices alongside it (a built-in laptop webcam is the
  canonical case); the
  [Camera selection wizard](#camera-selection--pick-once-re-prompt-on-failure)
  is how the maker tells PartsLedger which one to use.
- **Lighting**: ring light around the lens or a desk lamp at a fixed
  angle. Lighting consistency matters more than absolute brightness —
  DINOv2 embeddings are sensitive to harsh shadows.
- **Surface**: matte mat, ideally a single contrasting colour (white or
  black). Reflective surfaces (a steel desk) confuse both DINOv2 and
  the VLM.
- **No microscope.** SMD micro-marking codes (`A6`, `T4`) are
  deliberately out of scope; this is a webcam for through-hole / DIP /
  module-sized parts.

## Software stack

| Job | Library |
|---|---|
| Device open / frame grab | `cv2.VideoCapture` (OpenCV) |
| Frame format | `np.ndarray (H, W, 3), BGR uint8` — OpenCV's native emit, no conversion at this stage |
| Camera selection | First-run wizard with friendly-name picker (see [Camera selection](#camera-selection--pick-once-re-prompt-on-failure)) |
| Live viewfinder | `cv2.imshow` window with overlays (see [Live viewfinder](#live-viewfinder--required)) |
| Trigger UI | keyboard hotkey on the viewfinder window (`<Space>`); pedal / auto-detect as polish |
| Pre-flight check | Open the persisted device; on failure, re-enter the wizard |

Heavy dep: OpenCV is one of the bigger Python packages PartsLedger pulls
in (see [CLAUDE.md § Missing executables](../../../../CLAUDE.md#missing-executables)).
Worth gating with `/check-tool cv2` at runtime.

## Capture trigger UX

The hand-eye loop is the user-facing core of the camera path. PartsLedger
only ever sees **one trigger primitive** — a keypress delivered to the
focused viewfinder window — with two ways the maker can produce it and
one explicit non-goal.

### Primary — keyboard hotkey

Maker holds the part under the camera with one hand, taps `<Space>` (or
similar) with the other. Familiar, zero extra hardware, two-handed pose
acceptable for the single-part-at-a-time workflow this stage is built for.

### Polish — foot pedal via [AwesomeStudioPedal](../../../../../AwesomeStudioPedal/README.md)

For hands-free batch sessions, the maker uses the sibling
**AwesomeStudioPedal** project: a BLE-HID foot controller that pairs as
a standard keyboard. One pedal button is mapped to the same `<Space>`
keystroke, no PartsLedger code change required. Cross-platform
"compatibility" comes for free because the OS treats it as a keyboard
on every host. This collapses the historical *"pick a generic HID
pedal and write driver glue"* concern into a config exercise on the
pedal side.

### Non-goal — auto-detect "part placed"

OpenCV background-subtraction watching the mat for motion-stop sounds
ergonomic, but the failure modes (shadows count as motion, two parts
in frame both trigger, hand still in frame at the moment of capture)
make it a far-fetched goal for a one-maker workshop. Documented here
as a deliberate non-goal so it doesn't reappear as scope creep.

## Camera selection — pick once, re-prompt on failure

The maker's machine often exposes more than one capture device — a
weak built-in webcam plus a good external one is the canonical case.
The capture stage must let the maker pick which one is used, but
must never push V4L2 / DirectShow / device-path plumbing into the
maker's face.

**Decision** (was an unaddressed gap, honed 2026-05-13):

The flow is a first-run wizard, not a manual env-var edit.

1. On capture-path startup, resolve the persisted camera choice. If
   it resolves to a real, openable device, use it silently and
   continue. The maker sees nothing.
2. If no choice is persisted, the persisted choice no longer resolves
   (device unplugged, name changed, config deleted), or the maker
   explicitly asks for a re-pick (a `--pick-camera` flag, say), enter
   the wizard.
3. The wizard discovers available cameras and prints a short list
   with **maker-friendly names** — *"Integrated Camera"*, *"Logitech
   HD Pro Webcam C920"*. The maker picks one by number. The choice
   is persisted; the captured-image stream then uses it.

**Persistence target.** The `[camera]` section of
`~/.config/partsledger/config.toml` (see
[IDEA-007 § Configuration files](idea-007-visual-recognition-dinov2-vlm.md#configuration-files)
for the file convention — one shared TOML, domain-split into
sections). Hand-editable, deletable (deleting it just retriggers
the wizard on next start), but not something the maker needs to
touch under normal use. The repo's `.envrc` keeps an *optional*
`$PL_CAMERA` override for headless or scripted runs; if set, it
bypasses the wizard, but is not the human entry point.

**Fail-loud, not fail-soft.** When the persisted choice does not
resolve, the capture stage **does not** quietly fall back to the
first available camera. It re-enters the wizard. Silently using the
bad built-in webcam when the maker thought the good external one was
being used is the failure mode this guards against.

**Under the hood — deliberately invisible to the maker:**

- Linux: enumerate `/dev/v4l/by-id/usb-…` symlinks, read each
  device's friendly name from the underlying `v4l2` capability.
- Windows: enumerate DirectShow devices, read each device's
  friendly name from the device-properties API.
- The persisted record stores the platform-appropriate stable
  identifier *plus* the friendly name (the latter only for
  human-readable error messages when the device disappears).

The maker never types a `/dev/...` path, a DirectShow GUID, or an
integer index. None of that vocabulary appears in any prompt the
wizard shows.

## Live viewfinder — required

The maker needs continuous visual feedback while positioning a part —
*is it in frame, in focus, evenly lit?* — **before** committing the
capture. Downstream stages cannot recover from a blurry or off-axis
photo (see [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md)), so
blind-capture mode is not a viable default.

**Decision** (was an open question, honed 2026-05-13):

- A live preview window is **always** shown when the capture path is
  active. OpenCV's `cv2.imshow` is the minimum viable surface; a
  richer Qt / Tk / web overlay is a polish target, not a precondition.
- Overlays drawn on top of the live frame:
  - **Framing rectangle** at the fixed working distance — the same
    rectangle that is physically marked on the mat. The maker lines
    the part up against the overlay, not against guesswork.
  - **Focus indicator** — a numeric Laplacian variance plus a
    green/amber/red traffic light, so a soft frame is visible
    *before* the trigger fires.
  - **Lighting check** — a simple mean-luminance / clipping warning
    so harsh shadows or blown highlights are caught at the source.
  - **Trigger hint** — on-screen reminder of the active hotkey
    (`<Space>` or whatever the trigger UX in the section above
    settles on).
- The viewfinder also doubles as the **recognition-status surface**
  for [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md). The
  captured frame freezes in the main area while identification runs;
  the four verdict outcomes (silent qty++ flash, *via VLM* flash,
  retry-or-abort prompt, manual escalation) all render on the same
  window the maker is already looking at. Full state machine in
  [§ Overlays during recognition](#overlays-during-recognition)
  below; key dispatch in [§ Key dispatch](#key-dispatch).
- **Headless caveat.** PartsLedger's camera path assumes a workstation
  with a display anyway (the webcam is on the bench, the maker is at
  the keyboard). Headless mode is not a goal of this stage. A
  `--no-preview` flag stays available for scripted regression runs
  against pre-recorded frames, but is not the human entry point.

### Window lifecycle

The viewfinder opens **once** at session start
([Runtime flow § Session init](#runtime-flow--what-happens-when-the-maker-triggers-a-capture)
step 4) and stays open for the whole session — across re-frame
retries *and* across multiple distinct parts the maker swaps under
the camera. Opening / closing per capture would flicker, lose window
position, and pointlessly thrash the WM.

Three quit triggers, all routed through the same `try…finally`
cleanup so the camera and window are always released:

- **`q` or `Esc`** on the focused viewfinder. The OpenCV canonical
  pattern, polled with `cv2.waitKey(...)`.
- **Window close from the WM** (X button, Alt-F4, etc.). Polled with
  `cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1`. Treated
  as a deliberate *"I'm done"* signal — the viewfinder is **not**
  re-opened, and the camera path **does not** keep running headless.
- **Signal interrupt** — `SIGINT` (Ctrl-C in the parent terminal),
  `SIGTERM`, or normal program exit. Caught by the runtime; same
  cleanup path.

If the maker closes the window *while*
[IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) is
mid-recognition (e.g. waiting on a VLM HTTP call), the in-flight
call is allowed to finish — bounded by a hard timeout of about
30 seconds — but its result is **discarded**. No half-confirmed
identification gets written to inventory. The matching cleanup
sequence is in
[Runtime flow § Session cleanup](#runtime-flow--what-happens-when-the-maker-triggers-a-capture).

### Key dispatch

The viewfinder is the focused window, so OpenCV's `cv2.waitKey(...)`
loop is where every keypress the maker makes arrives. IDEA-006 owns
the **dispatch** itself; the **handler** belongs to whichever stage
owns the action:

| Key | Context | Action | Handler |
|---|---|---|---|
| `<Space>` | Idle / positioning | Trigger capture | IDEA-006 (this stage) |
| `R` | Retry-or-abort prompt | Re-take a fresh single still on the same part | IDEA-006 (resets state and re-enters the per-capture loop) |
| `X` | Retry-or-abort prompt | Escalate to manual entry | IDEA-006 dispatches → [IDEA-005 `/inventory-add`](idea-005-skill-path-today.md) |
| `U` | Confirmation flash + ~5 s after | Undo the last write | IDEA-006 dispatches → [IDEA-007 § Stage 5 `undo_last()`](idea-007-visual-recognition-dinov2-vlm.md#stage-5--undo-journal) |
| `q` / `<Esc>` | Anytime | Quit session | IDEA-006 ([§ Window lifecycle](#window-lifecycle)) |

Unknown keys are ignored silently — no error overlay fires for a
random keypress, so the maker can fat-finger the keyboard without
visual noise. Numeric digits in particular are reserved for a future
top-N picker if one ever lands; ignoring them today is forward-
compatible.

### Overlays during recognition

The viewfinder doubles as the recognition-status surface. The maker
never has to look at a separate terminal / TUI / window to see what
[IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) made of a
capture — every state of the recognition flow is rendered on the
same window the maker is already looking at.

Four display states the viewfinder cycles through, mapped to the
unified pipeline in
[IDEA-007 § The recognition pipeline](idea-007-visual-recognition-dinov2-vlm.md#the-recognition-pipeline):

| State | What is shown | Transition out |
| --- | --- | --- |
| **Idle / positioning** | The capture overlays above (framing rectangle, focus traffic-light, lighting check, trigger hint). Optionally a small *"last result"* breadcrumb in a corner so the maker can still see what the previous part was identified as while positioning the next one. | Maker presses `<Space>`. |
| **Analyzing** | Captured frame **frozen** in the main area + small **live thumbnail** of the camera feed in a corner (so the bench is still visible). *"Identifying…"* status text with a simple spinner. | IDEA-007 returns a pipeline verdict. |
| **Retry-or-abort prompt** | Captured frame stays frozen. Reached on *medium DINOv2 distance* or *VLM needs-re-frame* verdict. When the VLM produced the verdict, its hint string overlays the frame — see [§ Recognition-state hints](#recognition-state-hints) for the families the maker may see (*"rotate 90°"*, *"glare on the marking"*, *"too dark"*, *"image too blurry"*, …). Small confidence-band breadcrumb (*medium cache* vs *VLM uncertain*). Action prompt: ***R*** retry · ***X*** abort. | Maker presses **R** (loop back to capture) or **X** (escalate to `/inventory-add`). |
| **Confirmation flash** | Brief confirmation — *"Saved as LM358N — qty 5 → 6"* — for ~1 s, annotated *"via VLM"* when the pipeline reached the *VLM hedged ID* branch (subtle indicator only; not a request to re-check). ***U** to undo* stays visible as a corner hint for a few seconds after the flash itself fades, so the maker has time to reverse a wrong write before the next capture. | Auto-timeout back to *Idle*. |

The maker never sees a `Y accept` prompt or a numbered top-3 picker —
those were assumptions of an older pipeline and are intentionally
gone. The four states cover every pipeline outcome:

- *Confirmation flash* covers tight cache hit AND VLM hedged ID
  (silent writes, differing only in the *via VLM* annotation).
- *Retry-or-abort prompt* covers medium DINOv2 AND VLM needs-re-frame.
- The *no-idea* VLM verdict triggers a brief Retry-or-abort prompt
  with the *X abort* path pre-selected — the maker can override
  with *R*, but the default is to escalate.

### Recognition-state hints

When the *Retry-or-abort prompt* state is reached via a VLM
*needs-re-frame* verdict, the hint string from
[IDEA-007 § Stage 2](idea-007-visual-recognition-dinov2-vlm.md#stage-2--vlm-identification)
overlays the frozen frame. Realistic families the maker may see
(non-exhaustive, IDEA-007 owns the prompt rules that elicit them):

| Family | Examples |
|---|---|
| Angle / orientation | *"rotate 90°"*, *"show more from the left"*, *"tilt up so the marking is visible"* |
| Lighting | *"too dark"*, *"too bright"*, *"glare on the marking"*, *"shadow on the body"* |
| Sharpness | *"image too blurry"*, *"out of focus"* |
| Framing | *"part is off-centre"*, *"part is cut off"*, *"two parts in shot — show one"* |
| Surface / background | *"reflective surface — try a matte mat"* |
| Distance | *"too close"*, *"too far away"* |
| Marking state | *"marking worn — try a different side"*, *"marking unreadable from this angle"* |

Hints the parser can't tokenise into a known family fall back to a
generic *"image unclear — recompose and retry"* per
[IDEA-007 § The re-frame loop](idea-007-visual-recognition-dinov2-vlm.md#the-re-frame-loop--looping-around-idea-006).

**Where the schema lives.** The pipeline verdict payload (verdict
enum, top-1 candidate with hedge phrasing, optional hint string,
confidence band, *via VLM* source flag) is **owned by**
[IDEA-007 § The recognition pipeline](idea-007-visual-recognition-dinov2-vlm.md#the-recognition-pipeline).
IDEA-006 renders whatever IDEA-007 returns according to that schema;
this stage does not invent verdict data.

**Resolves a prior open question.** *"Viewfinder state during
recognition: freeze or keep streaming?"* — answered as
**freeze + live thumbnail**. Logged in
[Decisions](#decisions-2026-05-13-hone). Freeze alone would lose the
bench's live feedback; streaming alone would lose the *"this is what
was analyzed"* clarity. The combination gives both at the cost of
slightly busier overlay real estate.

## Capture workflow — single still

**Decision** (was *Multi-angle workflow*, honed 2026-05-13):

Each invocation of this stage produces **exactly one still** —
showing **exactly one part** — and returns. No burst mode, no
contact-sheet stitching, no DINOv2 embedding averaging across
angles, no multi-object frames. For the through-hole / DIP /
module-sized parts in scope, a single top-down frame is usually
enough to carry either the marking or the pin pattern.

The contract is owned by [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md)
in two halves, both deliberately *not* IDEA-006's concern:

- **What's in the frame** — *one part per still*. Rationale and
  multi-object sub-scenarios in
  [IDEA-007 § Capture contract](idea-007-visual-recognition-dinov2-vlm.md#capture-contract--one-object-per-photo).
- **What happens after the capture** — the re-frame loop
  (medium DINOv2 distance, or VLM *needs-re-frame* verdict) and its
  hard escalation cap at two retries then fall back to
  [`/inventory-add`](idea-005-skill-path-today.md). Lives in
  [IDEA-007 § The re-frame loop](idea-007-visual-recognition-dinov2-vlm.md#the-re-frame-loop--looping-around-idea-006).

From IDEA-006's perspective: when the maker triggers, exactly one
part should be under the framing overlay, and the stage stays
loop-less. The viewfinder surfaces re-frame hints as overlays when
IDEA-007 asks for them (see
[§ Recognition-state hints](#recognition-state-hints)), but the
looping itself is IDEA-007's concern.

## Framing & quality requirements

Driven by downstream needs from [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md):

- **Resolution**: the 2K sensor is generous. Downstream DINOv2 wants
  ≥ 224×224 of the *part* (not the frame); the VLM reads marking text,
  so at least ~10 px per character is the operational minimum.
- **Focal distance**: fixed working distance (a marked rectangle on the
  mat) avoids re-focus latency and makes embedding-space neighbours
  comparable across sessions.
- **Autofocus**: let the camera handle it. KISS — no manual focus
  jig, no "lock when stable" heuristic, no custom focus controller.
  If embedding-distance consistency suffers in practice, that's a
  later calibration problem, not an upfront capture-stage one.
- **Background**: single colour, no clutter. The DINOv2 backbone will
  pick up *anything* in frame as feature signal.

## Output contract to downstream

A successful capture yields:

```text
image: np.ndarray  (H, W, 3), BGR uint8 (OpenCV native)
metadata: {
  timestamp: ISO 8601,
  camera: {
    name: str,           # friendly name, e.g. "Logitech HD Pro Webcam C920"
    stable_id: str,      # /dev/v4l/by-id/... on Linux, DirectShow id on Windows
  },
  resolution: (W, H),
  trigger: "keyboard",   # pedal is just a BLE-HID keyboard
}
```

The metadata block accompanies the image only during per-capture
processing — it isn't persisted anywhere. The cache row that
[IDEA-007 § Stage 1](idea-007-visual-recognition-dinov2-vlm.md#stage-1--dinov2-as-similarity-cache)
writes stores only `(embedding, label, marking_text)`; the camera
identity, timestamp, and trigger source don't ride into the cache.
The metadata exists as a *debugging surface* — log lines, viewfinder
error breadcrumbs, hand-off correlation when the pipeline is being
profiled — not as a downstream data contract.

**Transport: in-memory.** The image is handed to
[IDEA-007 § Stage 4 `pipeline.run(image)`](idea-007-visual-recognition-dinov2-vlm.md#stage-4--pipeline-glue--branching)
as a `numpy.ndarray` Python reference. Zero copy, zero I/O latency,
both stages share a Python process. Honed 2026-05-14 — see the
*Hand-off transport* entry in
[§ Decisions](#decisions-2026-05-13-hone) for the rationale and
the future-proofing note about refactoring `pipeline.run` to take
a path argument if a process-boundary hand-off is ever needed.

**Debug surface.** The CLI's optional `--dump-captures-to <path>`
flag (see
[Execution plan § Stage 6](#stage-6--cli-wrapper)) *additionally*
writes each captured frame as a PNG into the named directory —
filename is the `timestamp` field above. Default off. When the
flag is set, files are **not** cleaned up at session-end; the
whole point is post-session inspection. Not a replacement for the
in-memory hand-off; an addition.

## Pipeline failure modes — what the camera-path does when something breaks

A handful of failure modes are specific to this stage (display
backend, USB device, frame grab). Spelled out so the failure
behaviour doesn't drift over time, and so the implementer doesn't
have to invent a policy under pressure:

- **Camera disappears mid-session** (USB unplugged, daughter-board
  reset, driver fault). Fail-loud: cleanup runs
  ([§ Window lifecycle](#window-lifecycle) `try…finally` path),
  the maker sees a *"camera lost — `<friendly name>`"* error
  overlay before the window closes, the camera-path exits non-zero.
  **Does not** silently swap to a different connected device — that
  would defeat the [Camera selection wizard](#camera-selection--pick-once-re-prompt-on-failure)'s
  whole point.
- **Repeated frame-grab failures** (camera busy by another app,
  transient driver glitch). After ~5 consecutive `read()` failures,
  treat as *camera disappeared*; same exit path. A handful of
  isolated failures (one or two missed frames) is swallowed —
  webcams are flaky and we don't punish the maker for it.
- **`cv2.imshow` cannot create a window** (no display, Wayland
  without `xwayland`, broken `$DISPLAY`). Hard fail at session
  init with a clear error message naming the
  [Headless caveat](#live-viewfinder--required) and pointing at the
  `--no-preview` flag for scripted regression runs. No silent
  fall-through to a headless capture mode.
- **`config.toml` becomes unreadable mid-session** (the maker
  hand-edits it and breaks the TOML). No effect: the camera choice
  was loaded once at *Session init* and the running session uses
  the in-memory copy. The next session start will surface the
  parse error and re-enter the wizard.
- **Per-frame overlay rendering crashes** (numpy / `cv2` internal
  error during the focus-traffic-light or lighting-check
  decorator). Catch and **disable the failing overlay** for the
  rest of the session; render a small *"focus / lighting / framing
  overlay off"* notice in its corner so the maker knows what's
  gone, keep the underlying live feed visible. A crashing overlay is a UX bug, not a
  session-killing bug — the maker can still capture.
- **Configuration loaded from `config.toml` doesn't match a
  connected device at session start** (cable swapped between
  sessions). Handled by the
  [Camera selection wizard](#camera-selection--pick-once-re-prompt-on-failure)'s
  fail-loud re-prompt — not a runtime failure, just first-session
  friction.

The unifying principle: the camera path **never silently degrades**.
A failure either drops cleanly through to the
[§ Camera selection wizard](#camera-selection--pick-once-re-prompt-on-failure)
or surfaces an error and exits. Silent fallback to the wrong camera
/ a degraded mode / a non-overlayed capture is the failure mode
this dossier guards against above all others.

## Execution plan

Five stages, each implementable in isolation with explicit
validation gates. Forward-only dependencies; the rollout can stop
at Stage 3 and the camera path is already useful as a fixture
generator for [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md).
Stages 4-5 are the integration into the recognition pipeline.

### Stage 1 — Camera selection wizard

**Goal.** First-run wizard with maker-friendly names, persisted
choice, fail-loud re-prompt. No streaming, no preview window yet —
just *"which device do I open?"*.

**Changes:**

1. New module `partsledger/capture/camera_select.py` — platform-
   specific enumeration (Linux: `/dev/v4l/by-id/usb-…` symlinks +
   `v4l2` capability query; Windows: DirectShow device-properties
   API). Exposes `list_cameras() -> [(stable_id, friendly_name)]`.
2. Wizard CLI: prints the list, reads a numeric pick on stdin,
   writes the chosen `(stable_id, name)` pair into the `[camera]`
   section of `~/.config/partsledger/config.toml`.
3. Resolver: `resolve_camera() -> stable_id` reads the config,
   verifies the device opens, returns the stable id or raises a
   *"choice no longer resolves"* error that triggers re-entry into
   the wizard.
4. `$PL_CAMERA` env-var override bypasses the wizard entirely (for
   headless / scripted runs).

**Validation:**

- Two cameras connected, wizard lists both with sensible friendly
  names, picking either persists to `config.toml`.
- Deleting the `[camera]` section retriggers the wizard on next
  invocation.
- Unplugging the chosen camera surfaces the wizard, never falls
  through to a different device silently.
- Linux `/dev/v4l/by-id` symlink and Windows DirectShow id both
  produce stable, replug-survivable choices.

**Dependencies.** None.

### Stage 2 — Live viewfinder + capture overlays

**Goal.** Bring up the `cv2.imshow` window with the four capture-
time overlays (framing rectangle, focus traffic light, lighting
check, trigger hint). Implements the session lifecycle contract —
one open, stays-across-captures, three quit triggers, `try…finally`
cleanup.

**Changes:**

1. New module `partsledger/capture/viewfinder.py` — `Viewfinder`
   context manager. Opens `cv2.VideoCapture(stable_id)`, pumps
   frames into `cv2.imshow`, calls `cv2.destroyAllWindows()` and
   `.release()` on exit.
2. Per-frame overlay decorators:
   - Framing rectangle at fixed working-distance pixel coordinates
     (configurable in `config.toml [recognition]` or a sibling
     section).
   - Focus indicator — `cv2.Laplacian(...).var()` mapped to a
     three-band traffic light.
   - Lighting check — mean luminance + max-channel clip count,
     overlay turns amber when either is out of band.
   - Trigger hint — static text rendered at the bottom edge.
3. Key dispatch loop polls `cv2.waitKey(...)` plus
   `cv2.getWindowProperty(name, WND_PROP_VISIBLE) < 1` and the
   signal handlers. Dispatch table from
   [§ Key dispatch](#key-dispatch) — Stage 2 wires only `<Space>`
   and `q` / `<Esc>` (and the WM-close / signal paths); the other
   keys land in Stages 4-5.

**Validation:**

- Window opens at session start, stays open across multiple
  triggers, closes on `q` / `Esc` / WM-close / SIGINT — same
  cleanup path for all four.
- Overlay decorators render at ≥ 30 fps on the dev hardware (CPU
  is plenty; cv2 work is the bottleneck, not the overlays).
- Killing the parent process with `SIGTERM` leaves no orphan
  X11 / Win32 window behind.

**Dependencies.** Stage 1 (resolved camera).

### Stage 3 — Capture trigger + single still

**Goal.** Bind `<Space>` to capture; on press, freeze the current
frame as an `np.ndarray (H, W, 3), BGR uint8` and emit the
[Output contract](#output-contract-to-downstream) packet.

**Changes:**

1. `Viewfinder` gains a `capture() -> (image, metadata)` method
   that returns the most recent frame plus the metadata dict.
2. `<Space>` dispatch in the key loop calls `capture()` and
   yields the result via a callback or async channel so the caller
   (eventually IDEA-007's pipeline) can consume it.
3. Camera-identity fields in the metadata dict are populated from
   Stage 1's resolver (`name`, `stable_id`). `trigger: "keyboard"`
   hardcoded; pedal looks like a keyboard so this is honest.

**Validation:**

- `<Space>` press yields exactly one `ndarray` with the right
  shape and dtype.
- Metadata dict carries the camera's friendly name and stable id
  byte-identically to what Stage 1 persisted.
- A captured frame fed into a separately-implemented embedding
  call (or a no-op stub) produces a non-zero deterministic vector
  — i.e. the array isn't a stale buffer.

**Dependencies.** Stages 1 + 2.

### Stage 4 — Recognition-status overlay state machine

**Goal.** Drive the four-state overlay machine (Idle / Analyzing /
Retry-or-abort / Confirmation flash) from
[IDEA-007](idea-007-visual-recognition-dinov2-vlm.md)'s verdict
payload. Stage 4 is where IDEA-006 becomes a real partner to the
recognition pipeline, not just a capture device.

**Changes:**

1. `Viewfinder` gains `set_state(state, payload)` — transitions
   between the four display states defined in
   [§ Overlays during recognition](#overlays-during-recognition).
2. Per-state overlay renderers — frozen-frame + live-thumbnail
   compositing for *Analyzing*, verdict label + hint string +
   *R / X* prompt for *Retry-or-abort prompt*, confirmation-flash
   text + *via VLM* annotation + corner *U to undo* hint for
   *Confirmation flash*.
3. Hint-family tokeniser per
   [§ Recognition-state hints](#recognition-state-hints) — short
   string in, one of seven family-shapes out, fall-through to
   *"image unclear — recompose and retry"*.
4. State-transition contract with IDEA-007: the viewfinder exposes
   a small API (`begin_analyzing(captured_frame)`,
   `show_retry_or_abort(hint)`, `flash_confirmation(text, via_vlm)`,
   `return_to_idle()`) that the pipeline calls; the viewfinder
   never inspects the verdict payload itself, just renders what
   it's told.

**Validation:**

- A mocked pipeline driving the four `set_state` calls in sequence
  shows each overlay correctly.
- Hint-family tokeniser correctly classifies sample strings into
  the seven families; unknown strings collapse to the generic.
- *Confirmation flash* auto-times-out back to *Idle* after ~1 s.
- The *Analyzing*-state live thumbnail keeps updating even though
  the main frame is frozen.

**Dependencies.** Stage 3 (a working per-capture loop). IDEA-007
contract for the verdict shape — can be developed against a mock.

### Stage 5 — Secondary key dispatch (R / X / U)

**Goal.** Wire the contextual keys — `R`, `X`, `U` — to their
handlers. With this stage landed, the dispatch table from
[§ Key dispatch](#key-dispatch) is fully realised.

**Changes:**

1. `R` handler: legal only in the *Retry-or-abort prompt* state;
   resets the viewfinder to *Idle* and re-enters the per-capture
   loop (effectively a silent re-trigger).
2. `X` handler: legal only in *Retry-or-abort prompt*; calls
   into [IDEA-005 `/inventory-add`](idea-005-skill-path-today.md)
   with the captured image as context — the maker types the
   part-ID manually from there.
3. `U` handler: legal during *Confirmation flash* and for ~5 s
   after; calls
   [IDEA-007 § Stage 5 `undo_last()`](idea-007-visual-recognition-dinov2-vlm.md#stage-5--undo-journal)
   and surfaces *"reverted"* on the viewfinder, or *"undo failed"*
   if the journal couldn't unwind cleanly.
4. Unknown keys (and `R` / `X` / `U` pressed in the wrong state)
   are ignored silently — no error overlay, no beep. Forward-
   compatible with future top-N picker numeric keys.

**Validation:**

- `R` during *Retry-or-abort* re-enters capture without an
  intervening `<Space>` press.
- `X` during *Retry-or-abort* invokes `/inventory-add` and the
  resulting MD write lands in the part MD just as if the maker
  had typed the command directly.
- `U` after a tight cache hit reverses both the qty++ and the
  cache row, and the viewfinder shows *"reverted"*.
- `U` more than ~5 s after the confirmation flash is ignored
  (depth: 1; the next write moved the journal pointer).
- Pressing `R` or `X` in *Idle* does nothing visible.

**Dependencies.** Stage 4 (the state machine knows when each key
is legal). IDEA-005 `/inventory-add` for the `X` handler.
IDEA-007 Stage 5 for the `U` handler.

### Stage 6 — CLI wrapper

**Goal.** Give the maker a single command they can type in any
terminal: `python -m partsledger.capture` (later `partsledger
capture` once packaging is firmed up). The CLI is the thinnest
possible wrapper around the library — argument parsing, signal
handling, exit codes.

**Changes:**

1. New module `partsledger/capture/__main__.py` — argparse with
   the flags PartsLedger needs: `--no-preview` (scripted
   regression against pre-recorded frames per
   [§ Live viewfinder Headless caveat](#live-viewfinder--required)),
   `--pick-camera` (force the wizard even if a persisted choice
   resolves), `--dump-captures-to <path>` (debug-dump per the
   *Hand-off transport* decision).
2. Wires SIGINT / SIGTERM into the `Viewfinder` context manager's
   cleanup path from Stage 2.
3. Exit codes: `0` clean exit, `1` camera not resolvable, `2`
   display backend unusable, `130` interrupted (SIGINT). Lets
   shell scripts react sensibly.

**Validation:**

- `python -m partsledger.capture` opens the viewfinder and behaves
  identically to invoking the library directly from a Python REPL.
- `--no-preview --dump-captures-to /tmp/test` runs against a fixed
  test image and emits the expected dump file without ever opening
  a window.
- `Ctrl-C` at any state exits cleanly with code 130, no orphan
  X11 / Win32 window.

**Dependencies.** Stages 1, 2, and 3 (library is callable). Stages 4
and 5 must land before this is *useful* end-to-end, but the CLI itself
only needs the foundation.

### Stage 7 — Thin `/capture` slash-skill

**Goal.** Let the maker invoke the same camera-path from inside a
Claude Code session by typing `/capture`. The slash-skill is a
subprocess wrapper around Stage 6's CLI — no business logic, no
state of its own.

**Changes:**

1. New `.claude/skills/capture/SKILL.md` — declares the skill,
   describes the contract: spawn the CLI as a subprocess, stream
   its stdout/stderr to the Claude session, return the subprocess
   exit code as the skill outcome.
2. Skill body: invokes `python -m partsledger.capture` via the
   wrapper script (`scripts/skills/capture-cli.sh` or similar)
   that passes through the `$PL_*` env vars from the surrounding
   session.
3. Skill registration: `enabled_skills` entry in
   [.vibe/config.toml](../../../../.vibe/config.toml) per the
   CLAUDE.md skill-registration rule.

**Validation:**

- `/capture` in a Claude Code session opens the viewfinder window
  exactly as the bare CLI invocation does.
- Closing the viewfinder returns control to the Claude session
  with the right exit code surfaced.
- `/capture` while another Claude action is mid-flight: the skill
  blocks the conversation for the camera-path's duration, which
  is the expected behaviour (the maker chose to start a long-
  running interactive surface from inside Claude).

**Dependencies.** Stage 6 (the CLI being wrapped).

### Out of scope for this rollout

- The recognition pipeline itself
  ([IDEA-007 Stages 1-5](idea-007-visual-recognition-dinov2-vlm.md#execution-plan))
  — Stage 4's contract here is the only IDEA-006 surface that
  touches it.
- [IDEA-008](idea-008-metadata-enrichment.md) metadata enrichment.
- A Qt / Tk / web-overlay viewfinder — `cv2.imshow` is the MVP,
  richer surfaces are explicit polish.
- BLE-pedal pairing UX — the pedal pairs at the OS level (see
  [AwesomeStudioPedal](../../../../../AwesomeStudioPedal/README.md)),
  PartsLedger never sees the BLE side.
- Multi-camera concurrent capture — the dossier targets one camera
  at a time per
  [IDEA-007 § Capture contract](idea-007-visual-recognition-dinov2-vlm.md#capture-contract--one-object-per-photo).

### Implementation order suggestion

Stages 1 → 2 → 3 are the foundation and sequence forward. Stage 4
can be designed in parallel against a mocked verdict payload but
lands after Stage 3. Stage 5 lands after Stage 4 and after
IDEA-007 Stage 5 (the `U` handler target). Stages 6 and 7 (CLI
wrapper and slash-skill wrapper) ride alongside — Stage 6 needs
only the foundation, Stage 7 needs Stage 6.

A four-PR rollout is the natural shape:

- **PR-A bundles Stages 1, 2, 3, plus Stage 6** — camera path
  emits captures, CLI is the thinnest possible entry-point, no
  recognition overlays yet. Already useful for IDEA-007 development
  as a fixture source.
- **PR-B lands Stage 4** — overlay state machine, integrates with
  whatever IDEA-007 has at that point.
- **PR-C lands Stage 5** — contextual keys, after IDEA-007 Stage
  5 exists.
- **PR-D lands Stage 7** — the `/capture` slash-skill wrapper.
  Lands last because it's the thinnest layer of all and depends
  on a stable CLI + state machine. Bundling earlier would mean
  re-spinning the slash-skill every time the CLI's flag set
  changes during PR-A through PR-C.

## Open questions to hone

Both gaps closed on 2026-05-14. Logged here with strikethrough so
the trail to the decisions in the block below is visible:

- ~~**Entry-point form.**~~ *Closed 2026-05-14.* **All three,
  layered — library underneath, CLI on top, thin slash-skill
  wrapping the CLI.** Library (Python module) is the implementation
  surface that the execution-plan stages 1-5 build out anyway; CLI
  (`python -m partsledger.capture` → `partsledger capture` once
  packaging is firmed up) is the primary maker entry-point;
  `/capture` slash-skill is a thin subprocess wrapper so the maker
  can invoke the same camera-path from inside a Claude Code
  session. None is exclusive; each lands as its own thin layer.
  See Stages 6 + 7 of the [Execution plan](#execution-plan).
- ~~**Hand-off transport.**~~ *Closed 2026-05-14.* **In-memory
  `numpy.ndarray` via function call**, with an optional
  `--dump-captures-to <path>` debug flag. Alignment: IDEA-007
  Stage 4 already defines `pipeline.run(image) -> Outcome` as a
  library function, so in-memory hand-off is what the contract
  already implies. Zero copy, zero I/O latency, no temp-dir or
  retention pflege. The dump-flag is *additive* (writes after the
  hand-off has already happened); files dumped this way are **not**
  cleaned up at session-end — the whole point is post-session
  debug visibility. If a future maker wants a fully decoupled
  process-boundary hand-off (headless / remote-recognition / batch
  pipeline), refactoring `pipeline.run` to accept an image path
  alongside the array is a Stage-4-extension, not an
  architecture-break.

## Decisions (2026-05-13 hone)

Ten decisions logged here so they don't resurface as scope creep.
The first eight landed on 2026-05-13; the bottom two on 2026-05-14
(flagged inline). Anchor kept stable so existing cross-links don't
rot:

- **Camera selection.** First-run wizard with friendly names, persisted
  to the `[camera]` section of `~/.config/partsledger/config.toml`,
  fail-loud re-prompt when the device disappears. V4L2 / DirectShow
  vocabulary never reaches the maker. See
  [Camera selection — pick once, re-prompt on failure](#camera-selection--pick-once-re-prompt-on-failure).
- **Viewfinder state during recognition.** Captured frame is **frozen**
  in the main viewfinder area while IDEA-007 is identifying; a small
  **live thumbnail** of the camera feed sits in a corner so the maker
  still has visual feedback about the bench. See
  [Overlays during recognition](#overlays-during-recognition).
- **Trigger choice.** Keypress is the only trigger primitive
  PartsLedger sees. Foot pedal collapses into the same keypress via
  the sibling AwesomeStudioPedal project (BLE-HID keyboard); auto-detect
  ruled out as a non-goal. See [Capture trigger UX](#capture-trigger-ux).
- **Multi-angle workflow.** This stage is now loop-less: one capture
  per invocation. The retry-or-escalate loop lives in
  [IDEA-007 § The re-frame loop](idea-007-visual-recognition-dinov2-vlm.md#the-re-frame-loop--looping-around-idea-006),
  which calls back into this stage with a one-line viewfinder hint.
  See [Capture workflow — single still](#capture-workflow--single-still).
- **Calibration ritual.** No reference-part-on-the-mat ritual at
  session start. If lighting drift bites the embedding cache, it
  gets handled downstream — not via a per-session setup chore.
- **Autofocus policy.** Camera's built-in autofocus. KISS. See
  [Framing & quality requirements](#framing--quality-requirements).
- **Image retention.** Captures are discarded at end of session. No
  long-term corpus, no embedding-cache re-training data, no quiet
  growth of an image folder no one prunes.
- **Pedal hardware choice.** AwesomeStudioPedal (sibling project).
  Because it pairs as a BLE-HID keyboard, PartsLedger never needs to
  know it exists — no vendor-specific HID glue lands in this repo.
- **Entry-point form** *(honed 2026-05-14).* **Library + CLI +
  thin slash-skill**, layered. Python module under
  `partsledger/capture/` is the implementation surface (Execution
  plan stages 1-5). `python -m partsledger.capture` (later
  `partsledger capture`) is the primary maker entry-point.
  `/capture` slash-skill is a thin subprocess wrapper. No one is
  exclusive; all three land. See
  [Execution plan § Stages 6 + 7](#stage-6--cli-wrapper).
- **Hand-off transport** *(honed 2026-05-14).* **In-memory
  `numpy.ndarray` via function call**, with an optional
  `--dump-captures-to <path>` debug flag that *also* writes the
  frame to disk (not a replacement for the in-memory path; files
  dumped this way are not cleaned up at session-end, the whole
  point is post-session inspection). Aligns with IDEA-007 Stage 4
  which already takes `pipeline.run(image)` as a library call.

New open questions, if any arise, go in a new `## Open questions to hone`
section above this one.

## Related

- [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) — the immediate
  downstream consumer of the image; also the source of the VLM
  re-frame hints used by [Capture workflow](#capture-workflow--single-still).
- [IDEA-008](idea-008-metadata-enrichment.md) — also reads images, but
  only for the optional resistor-band OCR fork.
- [IDEA-005](idea-005-skill-path-today.md) — the already-working
  manual-entry path. Also the **escalation target** when the camera
  path gives up after a couple of failed retries.
- [AwesomeStudioPedal](../../../../../AwesomeStudioPedal/README.md) —
  sibling project that supplies the optional foot-pedal hardware as a
  BLE-HID keyboard, transparent to PartsLedger.
