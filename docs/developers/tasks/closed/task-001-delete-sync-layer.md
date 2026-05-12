---
id: TASK-001
title: Delete awesome-task-system/ and scripts/sync_task_system.py
status: closed
closed: 2026-05-12
opened: 2026-05-12
effort: Small
effort_actual: XS (<30m)
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 1
---

## Description

PartsLedger currently maintains an `awesome-task-system/` directory as a
canonical source-of-truth for the task-system scripts and skills, with
`scripts/sync_task_system.py --check` enforcing live-vs-package parity
in the pre-commit hook. CircuitSmith does not have this layer — it
treats the live copies under `scripts/`, `.claude/skills/`, and
`docs/developers/task-system.yaml` as the truth, with upstream
consulted by hand when drift matters.

This task aligns PartsLedger with CircuitSmith's installed-copy model.

The pre-commit hook's `sync_task_system.py --check` block is guarded by
`[ -f "${REPO_ROOT}/scripts/sync_task_system.py" ]`, so deleting the
script silently disables the check — no separate hook edit is needed
here (the full pre-commit replacement happens in TASK-003 anyway).

## Acceptance Criteria

- [x] `awesome-task-system/` directory is gone.
- [x] `scripts/sync_task_system.py` is gone.
- [x] `python scripts/housekeep.py --apply` still runs clean (no
      references to the deleted paths from any live script).
- [x] A test commit using the existing `/commit` skill succeeds (the
      pre-commit hook does not error on the missing sync script).

## Test Plan

1. `rm -rf awesome-task-system/ scripts/sync_task_system.py`.
2. `python scripts/housekeep.py --apply` — exit 0, no errors.
3. Stage a trivial unrelated change (e.g. add a comment to this task
      body) and commit via `/commit` — verify the pre-commit hook
      reports the sync-check as skipped (or silent) and the commit
      lands.

## Notes

The `## Task-system source-of-truth` section in `CLAUDE.md` becomes a
dangling reference once this lands. TASK-011 (the `CLAUDE.md` rewrite)
replaces it with CircuitSmith's `## Task-system installation` text.
The dangling-reference window between TASK-001 and TASK-011 landing is
acceptable inside the epic branch.
