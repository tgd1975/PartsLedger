---
id: TASK-038
title: /capture thin slash-skill subprocess wrapper
status: closed
closed: 2026-05-14
opened: 2026-05-14
effort: Small (<2h)
effort_actual: Small (<2h)
complexity: Medium
human-in-loop: No
epic: usb-camera-capture
order: 7
prerequisites: [TASK-035, TASK-037]
---

## Description

Let the maker invoke the camera path from inside a Claude Code
session by typing `/capture`. Per
[IDEA-006 Stage 7](../../ideas/open/idea-006-usb-camera-capture.md#stage-7--thin-capture-slash-skill),
the slash-skill is the thinnest possible layer: a subprocess
wrapper around the CLI from TASK-035, with no business logic
and no state of its own.

Changes:

- New `.claude/skills/capture/SKILL.md` — declares the skill,
  describes the contract: spawn `python -m partsledger.capture`
  as a subprocess, stream its stdout / stderr to the Claude
  session, surface the resulting `inventory/parts/<part>.md`
  updates so Claude can see them, and return the subprocess
  exit code as the skill outcome.
- Wrapper script (e.g. `scripts/skills/capture-cli.sh` or
  the platform-appropriate equivalent) — invokes
  `python -m partsledger.capture` with the `$PL_*` env vars
  from the surrounding session passed through (so
  `$PL_INVENTORY_PATH`, `$PL_CAMERA`, etc. behave the same
  inside and outside the slash-skill).
- Skill registration — add `capture` to `enabled_skills` in
  [.vibe/config.toml](../../../../.vibe/config.toml) per the
  CLAUDE.md skill-registration rule.

The slash-skill blocks the conversation for the camera path's
duration — that is the expected behaviour, since the maker
chose to start a long-running interactive surface from inside
Claude. The session resumes once the maker exits the
viewfinder (`q` / `<Esc>` / WM-close / SIGINT) and the
subprocess returns.

This task lands **last** in the rollout because it is the
thinnest layer of all and depends on a stable CLI + state
machine. Bundling earlier would mean re-spinning the
slash-skill every time the CLI's flag surface changes during
TASK-032 through TASK-037.

## Acceptance Criteria

- [x] `.claude/skills/capture/SKILL.md` exists with a clear
      description and the subprocess-wrapper contract.
- [x] `capture` is registered in `enabled_skills` in
      `.vibe/config.toml`.
- [x] `/capture` in a Claude Code session opens the
      viewfinder window exactly as the bare CLI invocation
      does.
- [x] `$PL_*` env vars from the surrounding session are
      passed through to the subprocess.
- [x] Closing the viewfinder returns control to the Claude
      session with the right exit code surfaced (0 clean, 1
      camera not resolvable, 2 display backend unusable, 130
      interrupted).
- [x] Any `inventory/parts/<part>.md` updates the camera-path
      session produces are visible to Claude after the
      subprocess returns.

## Test Plan

**Host tests (pytest)** — `tests/skills/test_capture_skill.py`:

- Invoke the wrapper script with a fixture
  `partsledger.capture` (mocked to exit immediately with a
  known code) and assert exit code, stdout / stderr passthrough,
  and env-var passthrough.
- Assert the SKILL.md frontmatter parses and the skill is
  enabled in `.vibe/config.toml`.

**Manual integration test** — required because the
slash-skill contract is end-to-end Claude-Code-driven:

- In a Claude Code session, type `/capture`; verify the
  viewfinder opens, the maker can capture and identify a
  part, and the resulting MD write is visible to Claude after
  exit.
- Verify exit codes propagate (kill the subprocess; pull the
  camera USB cable to trigger the camera-not-resolvable path).

## Prerequisites

- **TASK-035** — supplies the CLI being wrapped.
- **TASK-037** — supplies the full Stage 5 dispatch so the
  in-session UX is end-to-end useful, not a stub.

## Notes

Per CLAUDE.md, adding a skill requires both the
`.claude/skills/<name>/SKILL.md` file **and** an entry in
`enabled_skills` in `.vibe/config.toml`. Both land in this
task.
