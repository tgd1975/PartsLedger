---
id: TASK-032
title: Camera-selection wizard (V4L2 / DirectShow enumeration, friendly names)
status: open
opened: 2026-05-14
effort: Large (8-24h)
complexity: Senior
human-in-loop: Support
epic: usb-camera-capture
order: 1
prerequisites: [TASK-022]
---

## Description

Implement the first-run camera-selection wizard described in
[IDEA-006 Stage 1](../../ideas/open/idea-006-usb-camera-capture.md#stage-1--camera-selection-wizard).
This is the front door of the camera path: before any viewfinder
opens or any frame is grabbed, the maker has to be able to pick
*which* USB capture device PartsLedger uses, on a host that
typically exposes several (a built-in laptop webcam plus the 2K
USB webcam being the canonical case).

The wizard lives in a new module
`partsledger/capture/camera_select.py` and exposes three
entry-points:

- `list_cameras() -> [(stable_id, friendly_name)]` — platform-
  specific enumeration. On Linux, walk
  `/dev/v4l/by-id/usb-…` symlinks and read each device's
  friendly name via the `v4l2` capability query. On Windows,
  enumerate DirectShow devices via the device-properties API
  and read the friendly name from there.
- Wizard CLI — prints the list as a numbered menu of
  **friendly names only** (*"Integrated Camera"*, *"Logitech HD
  Pro Webcam C920"*), reads a numeric pick on stdin, writes the
  chosen `(stable_id, name)` pair into the `[camera]` section
  of `~/.config/partsledger/config.toml`.
- `resolve_camera() -> stable_id` — reads the persisted choice,
  verifies the device opens with `cv2.VideoCapture`, returns
  the stable id or raises a *"choice no longer resolves"* error
  that triggers re-entry into the wizard.

Per the maker-UX rule (memory: `feedback_maker_ux_no_tech_internals`):
V4L2 / DirectShow vocabulary, `/dev/...` paths, DirectShow GUIDs,
and integer camera indices **must never** appear in any prompt
the wizard shows the maker. The persisted record stores the
platform-appropriate stable identifier plus the friendly name;
the friendly name is what the maker ever sees in error messages
when a device disappears.

Re-prompt is fail-loud per
[IDEA-006 § Camera selection](../../ideas/open/idea-006-usb-camera-capture.md#camera-selection--pick-once-re-prompt-on-failure):
when the persisted choice no longer resolves (device unplugged,
name changed, config deleted), the wizard re-enters — the
camera path **does not** silently fall through to the first
available device. The `$PL_CAMERA` env-var override from
`.envrc` bypasses the wizard for headless / scripted use only.

## Acceptance Criteria

- [ ] `partsledger/capture/camera_select.py` exists with
      `list_cameras()`, `resolve_camera()`, and a wizard CLI entry-point.
- [ ] On Linux, enumeration uses `/dev/v4l/by-id/usb-…` symlinks
      plus `v4l2` capability queries; on Windows, DirectShow
      device-properties API. Stable IDs survive a USB replug.
- [ ] The wizard prompt shows **only** friendly names — no
      `/dev/...` paths, no DirectShow GUIDs, no integer indices.
- [ ] The chosen `(stable_id, friendly_name)` pair is persisted
      to the `[camera]` section of
      `~/.config/partsledger/config.toml`.
- [ ] Deleting the `[camera]` section retriggers the wizard on
      next invocation; persisted choice that no longer resolves
      also retriggers (fail-loud, never silent fall-through).
- [ ] `$PL_CAMERA` env-var override bypasses the wizard.

## Test Plan

**Host tests (pytest)** — `tests/capture/test_camera_select.py`:

- Mock the platform enumeration layer; verify `list_cameras()`
  returns the expected `(stable_id, friendly_name)` tuples for
  fixture inputs on both Linux and Windows code paths.
- Verify `resolve_camera()` reads `config.toml` correctly,
  surfaces a typed *"choice no longer resolves"* error when the
  device-open mock fails, and honours the `$PL_CAMERA` override.
- Verify the wizard never emits any string matching
  `/dev/`, DirectShow GUID patterns, or bare integers as
  device identifiers.

**Manual hardware test** — required because real enumeration
needs the actual USB stack:

- With two cameras connected (the 2K USB webcam + the built-in
  laptop webcam), run the wizard; both appear with sensible
  friendly names; picking either persists correctly.
- Unplug the chosen camera between sessions; next session
  surfaces the wizard, does not silently fall through.
- Repeat on Windows (DirectShow path) once the Linux path is
  green.

## Prerequisites

- **TASK-022** — Python package skeleton under `partsledger/`
  with module-import paths wired up; the wizard module lands as
  `partsledger/capture/camera_select.py`.

## Sizing rationale

Wizard is a coherent UX flow spanning enumeration, naming,
persistence, and re-prompt. Splitting would create partial
states where the persisted config and the runtime enumeration
disagree.

## Notes

The `[camera]` section of `~/.config/partsledger/config.toml`
is shared with the recognition stage's config (see
[IDEA-007 § Configuration files](../../ideas/open/idea-007-visual-recognition-dinov2-vlm.md#configuration-files)).
This task only writes the `[camera]` section; other sections
land in their own epics.
