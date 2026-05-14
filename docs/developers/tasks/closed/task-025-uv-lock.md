---
id: TASK-025
title: Adopt uv.lock for reproducible installs
status: closed
opened: 2026-05-14
closed: 2026-05-14
effort: Small (<2h)
effort_actual: Small (<2h)
complexity: Junior
human-in-loop: No
epic: project-setup
order: 4
prerequisites: [TASK-022]
---

## Description

Adopt uv's lockfile workflow so every contributor and every CI run
resolves the same dependency tree.

Per IDEA-014 § What to port — sixth bullet: CircuitSmith pins dev
dependencies via uv's lockfile; PartsLedger does not. TASK-002
deliberately matched CircuitSmith's then-current "pip-replacement
mode of uv" (no `uv.lock`); CircuitSmith has since moved on.

Steps:

1. Run `uv lock` at the repo root to generate `uv.lock`.
2. Commit `uv.lock` (it's a lockfile — checked in, never gitignored).
3. Document the workflow: `uv sync` (instead of `uv pip install -e .[dev]`)
   for reproducible env; `uv lock --upgrade` when bumping deps; the
   lockfile rides into the same commit as the `pyproject.toml` change
   that prompted it.
4. CI step that fails the build if `uv.lock` is stale relative to
   `pyproject.toml` — `uv lock --check` (or whatever uv exposes for
   freshness validation).

## Acceptance Criteria

- [x] `uv.lock` is present at the repo root and committed.
- [x] `uv sync` in a clean checkout produces a working env (`python -c "import partsledger"` succeeds).
- [x] CI fails when `pyproject.toml` is changed without re-running `uv lock`.
- [x] CONTRIBUTING (or RELEASING.md, whichever covers the dev loop)
      documents the lockfile workflow.

## Test Plan

Host tests (pytest) — indirect via CI. Local validation: bump a dep
version in `pyproject.toml` without running `uv lock`, confirm the
freshness check fails; run `uv lock`, confirm it passes.

## Prerequisites

- **TASK-022** — delivers the src-layout pyproject.toml that `uv lock`
  resolves against. Locking before TASK-022 would lock the obsolete
  `py-modules = []` shape.

## Notes

`uv.lock` is a generated artefact, but unlike the task-system index
files it is **not** rolled by `/housekeep` — uv owns it. Updates ride
with any `pyproject.toml` change in the same commit.
