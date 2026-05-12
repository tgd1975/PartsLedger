# Changelog

All notable changes to the `awesome-task-system` package are documented here.

## [0.2.0] — 2026-04-26

### Source-of-truth consolidation

- `awesome-task-system/` is now the canonical source for the task-system
  scripts, skills, config, and tests. Edits land here once; a sync script
  propagates them to live copies under `scripts/` and `.claude/skills/`.
- Added `scripts/sync_task_system.py` — one-way sync (package → live),
  idempotent, refuses to clobber a dirty live copy without `--force`.
  `--check` mode powers a pre-commit divergence guard that fails any
  commit where the two sides drift.
- Added `awesome-task-system/scripts/tests/` — host tests now live in
  the package and are mirrored to `scripts/tests/`.
- Added `awesome-task-system/skills/tasks/SKILL.md` — the `tasks` skill
  is now part of the package set.

### Housekeeping

- `housekeep.py` validates `order:` fields per epic (no blanks, no
  duplicates, no `?` placeholders). `--fix-order` renumbers contiguously
  from 1 within each epic.

## [0.1.0]

Initial extraction. See `LAYOUT.md` for the directory layout and
distribution mapping.
