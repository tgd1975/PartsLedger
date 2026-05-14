---
id: TASK-035
title: CLI wrapper python -m partsledger.capture
status: closed
closed: 2026-05-14
opened: 2026-05-14
effort: Small (<2h)
effort_actual: Small (<2h)
complexity: Medium
human-in-loop: No
epic: usb-camera-capture
order: 4
prerequisites: [TASK-034]
---

## Description

Give the maker a single command they can type in any terminal:
`python -m partsledger.capture` (later `partsledger capture`
once packaging is firmed up). Per
[IDEA-006 Stage 6](../../ideas/open/idea-006-usb-camera-capture.md#stage-6--cli-wrapper),
the CLI is the thinnest possible wrapper around the library —
argument parsing, signal handling, exit codes — no business
logic.

New module `partsledger/capture/__main__.py`:

- `argparse` surface with three flags:
  - `--no-preview` — for scripted regression runs against
    pre-recorded frames per
    [IDEA-006 § Headless caveat](../../ideas/open/idea-006-usb-camera-capture.md#live-viewfinder--required).
    Not the human entry point.
  - `--pick-camera` — force the wizard (TASK-032) to re-enter
    even when a persisted choice still resolves.
  - `--dump-captures-to <path>` — debug surface per the
    *Hand-off transport* decision; writes each captured frame
    as a PNG into `<path>`, filename = the metadata
    `timestamp` field. Default off. Files dumped this way are
    **not** cleaned up at session-end; the point is
    post-session inspection.
- `SIGINT` / `SIGTERM` are wired into the `Viewfinder` context
  manager's cleanup path from TASK-033.
- Exit codes: `0` clean exit, `1` camera not resolvable, `2`
  display backend unusable, `130` interrupted (SIGINT). Lets
  shell scripts and the slash-skill wrapper (TASK-038) react
  sensibly.

This is the entry-point used as a fixture source during
EPIC-006 (recognition pipeline) development — `--no-preview
--dump-captures-to /tmp/fixtures` produces the kind of frame
corpus the recognition stage needs.

## Acceptance Criteria

- [x] `python -m partsledger.capture` opens the viewfinder and
      behaves identically to invoking the `Viewfinder` library
      directly from a Python REPL.
- [x] `--no-preview --dump-captures-to /tmp/test` runs against
      a fixture image source, emits PNGs with the right
      timestamp filenames, never opens a window.
- [x] `--pick-camera` re-enters the wizard even when a
      persisted `[camera]` choice still resolves.
- [x] `Ctrl-C` at any state exits cleanly with code 130; no
      orphan X11 / Win32 window left behind.
- [x] Camera-resolve failure exits with code 1; display-backend
      failure (e.g. `cv2.imshow` cannot create a window) exits
      with code 2.

## Test Plan

**Host tests (pytest)** — `tests/capture/test_cli.py`:

- Invoke `partsledger.capture.__main__:main` with each flag
  combination against mocked `Viewfinder`; assert the
  arguments propagate to the right hooks.
- Mock the camera-resolve and display-backend failure paths;
  assert exit codes 1 and 2 respectively.
- Send `SIGINT` to a subprocess running the CLI; assert exit
  code 130 and that cleanup ran.

**Manual hardware test** — light, since the CLI is a thin
wrapper:

- Run `python -m partsledger.capture` with the 2K USB webcam
  plugged in; verify it behaves like the library does.
- Verify `--dump-captures-to /tmp/fixtures` produces real PNG
  files post-session.

## Prerequisites

- **TASK-034** — supplies the trigger + single-still emit that
  the CLI wraps; the `--dump-captures-to` debug surface writes
  exactly the frames TASK-034 emits.
