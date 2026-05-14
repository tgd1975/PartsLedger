---
id: TASK-024
title: Add .github/workflows/ci.yml and release.yml
status: closed
opened: 2026-05-14
closed: 2026-05-14
effort: Medium (2-8h)
effort_actual: Medium (2-8h)
complexity: Medium
human-in-loop: No
epic: project-setup
order: 3
prerequisites: [TASK-022]
---

## Description

Stand up the `.github/workflows/` directory. PartsLedger has no
`.github/` directory today — per IDEA-014 § What to port — third
bullet — port CircuitSmith's `ci.yml` (refreshed for src-layout) and
`release.yml`.

Two workflows:

1. **`.github/workflows/ci.yml`** — refresh of the file TASK-002
   originally scaffolded but which never landed (TASK-002 predated
   the src-layout move). Ubuntu + Windows matrix on Python 3.11,
   `astral-sh/setup-uv@v3`, install via `uv pip install --system -e .[dev]`,
   `markdownlint-cli2` on `**/*.md`, `ruff check .`, `pytest`. With
   src-layout in place, an additional step verifies `python -c "import partsledger"`
   succeeds.
2. **`.github/workflows/release.yml`** — port from CircuitSmith.
   Triggers on tag push (`v*`), builds the wheel + sdist via
   `uv build`, publishes to PyPI via `pypa/gh-action-pypi-publish`.
   Must handle PEP 517 extras correctly (TASK-029 defines the
   `resistor-reader` extra; the release workflow publishes one
   distribution carrying all extras).

## Acceptance Criteria

- [x] `.github/workflows/ci.yml` runs cleanly on a PR — Ubuntu and
      Windows legs both green.
- [x] CI step `python -c "import partsledger"` passes (confirms
      TASK-022's package layout took).
- [x] `.github/workflows/release.yml` exists and is validated by
      `actionlint` (or equivalent) without errors.
- [x] A dry-run tag push (to a throwaway prerelease tag, e.g.
      `v0.0.1.dev1`) walks the release workflow through `uv build`
      successfully; the publish step is gated on a real tag and not
      executed in the dry run.
- [x] The release workflow carries the `partsledger[resistor-reader]`
      extra through into the published distribution metadata.

## Test Plan

Host tests (pytest) — indirect: CI runs `pytest` on every PR, so the
acceptance test for this task is that the CI itself reports green on a
PR carrying a trivial change. Local validation: `actionlint` on both
YAML files; `uv build` from the repo root produces a wheel + sdist.

## Prerequisites

- **TASK-022** — delivers the `src/partsledger/` layout that the CI
  import-check and the release workflow's `uv build` step both rely on.

## Notes

TASK-002's `ci.yml` was authored when PartsLedger had no Python
package; the import-check step is new for this task. Drop any
references to the old `py-modules = []` workaround that may have
crept into TASK-002's CI scaffolding before it landed.

PyPI publishing requires a project secret (`PYPI_API_TOKEN` or
trusted-publisher OIDC config). Note in the workflow comments that
the first real release requires the maintainer to configure this in
GitHub repository settings — the workflow itself does not need
changes when that happens.
