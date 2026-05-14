---
name: capture
description: Open the USB camera viewfinder and capture stills. Spawns `python -m partsledger.capture` as a subprocess; streams its stdout/stderr to the Claude session and surfaces the exit code. Blocking — the conversation pauses until the maker exits the viewfinder window.
---

# capture

The user invokes this as `/capture` (sometimes with one of the CLI flags
described below). The skill is a thin subprocess wrapper around the camera
CLI delivered in TASK-035. No business logic lives here — every behaviour
the maker sees comes from the `partsledger.capture` module.

## What it does

Spawn `python -m partsledger.capture` and stream its stdout / stderr into
the Claude session. The viewfinder window opens on the maker's display; the
maker positions parts under the camera, presses `<Space>` to capture, and
exits the session with `q` / `Esc` / WM-close. Control returns to the
Claude session with the subprocess exit code.

The `$PL_*` env vars from the surrounding session (`$PL_CAMERA`,
`$PL_INVENTORY_PATH`, `$PL_NEXAR_CLIENT_ID`, `$PL_NEXAR_CLIENT_SECRET`,
`$PL_PYTHON`) are inherited automatically — the wrapper does not rewrite
the environment.

## Flags (pass-through to the CLI)

- `--no-preview` — scripted regression mode, no viewfinder window.
- `--pick-camera` — force the camera-selection wizard to re-enter.
- `--dump-captures-to <path>` — write each capture as a PNG into `<path>`,
  filename = the metadata timestamp field. Files are not cleaned up at
  session end.

## Exit codes (surface as the skill outcome)

- `0` — clean exit (`q` / `Esc` / WM-close).
- `1` — camera not resolvable.
- `2` — display backend unusable (no display, broken `$DISPLAY`).
- `130` — interrupted by `SIGINT` (Ctrl-C in the parent terminal).

## How to run

Invoke `scripts/skills/capture-cli.sh` (Unix) or
`scripts/skills/capture-cli.cmd` (Windows). The wrapper script picks the
right Python interpreter (`$PL_PYTHON` if set, else `python`) and exec's
`-m partsledger.capture` with the user's flags forwarded verbatim.

The script blocks the Claude session for the camera path's duration —
that is the expected behaviour. Resume when the subprocess returns.

## Skill registration

This skill is registered in `.vibe/config.toml`'s `enabled_skills` list per
the CLAUDE.md skill-registration rule. The corresponding allowlist entry
in `.claude/settings.json` (`Bash(python -m partsledger.capture:*)`) means
running this skill does not require a permission prompt.

## When NOT to use

- Headless / CI runs that don't need a real viewfinder — call
  `python -m partsledger.capture --no-preview` directly with the right
  fixture-frame source.
- Manual part entry without a webcam — use `/inventory-add <part-id> <qty>`.

## Status note (2026-05-14)

Currently the in-session UX only handles the `<Space>` capture trigger,
`q` / `Esc` quit, and the WM-close path. The secondary keys (`R` retry,
`X` escalate-to-`/inventory-add`, `U` undo) land in TASK-037 after EPIC-006's
recognition pipeline exists. See [ADR-0003](../../../docs/developers/adr/0003-capture-skill-lands-before-secondary-keys.md)
for the rationale.
