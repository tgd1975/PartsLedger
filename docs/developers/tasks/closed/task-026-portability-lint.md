---
id: TASK-026
title: Add src/partsledger/_dev/portability_lint.py with scripts/ shim
status: closed
opened: 2026-05-14
closed: 2026-05-14
effort: Medium (2-8h)
effort_actual: Medium (2-8h)
complexity: Medium
human-in-loop: No
epic: project-setup
order: 5
prerequisites: [TASK-022]
---

## Description

Enforce the no-host-imports invariant on `src/partsledger/` so the
package stays publishable as a standalone wheel.

Per IDEA-014 § What to port — fifth bullet: CircuitSmith enforces
this via [`scripts/portability_lint.py`](../../../../../CircuitSmith/scripts/portability_lint.py).
PartsLedger needs the same lint, applied to `src/partsledger/`, with
two adaptations:

1. The lint logic lives at `src/partsledger/_dev/portability_lint.py`
   (per the shim convention TASK-027 documents — Python in the
   package, not flat under `scripts/`).
2. `scripts/portability_lint.py` is a thin shim: argparse +
   `from partsledger._dev.portability_lint import main; main()`.

What the lint forbids inside `src/partsledger/`:

- `from scripts.<anything>` — `scripts/` is host-side, not packaged.
- `from .claude.<anything>` or any path under `.claude/`.
- Relative paths that escape `src/partsledger/` (e.g.
  `Path(__file__).parent.parent.parent / "scripts"`).
- Hard-coded references to repo-root files (`inventory/`, `docs/`)
  unless the path comes through a configurable interface.

The lint is wired into the pre-commit hook (per CircuitSmith's setup)
and into `.github/workflows/ci.yml` as a standalone step.

## Acceptance Criteria

- [x] `src/partsledger/_dev/portability_lint.py` exists and implements
      the import-graph walk.
- [x] `scripts/portability_lint.py` is a thin shim (≤ 15 lines of
      executable code) calling into the package.
- [x] A deliberate test case (e.g. `src/partsledger/_dev/_test_import.py`
      with `from scripts.housekeep import …`) is flagged by the lint.
- [x] The clean tree passes the lint with exit code 0.
- [x] The pre-commit hook runs the lint and rejects offending diffs.
- [x] CI runs `python scripts/portability_lint.py` as a dedicated step.

## Test Plan

Host tests (pytest):

- `tests/test_portability_lint.py` — fixture sets up a temp tree with
  one offending import and one clean import, asserts the lint catches
  the offender and passes the clean one.
- Also assert the shim at `scripts/portability_lint.py` exits with the
  same code as the in-package entry point.

## Prerequisites

- **TASK-022** — delivers `src/partsledger/` for the lint to walk.

## Notes

Reference: CircuitSmith's [`scripts/portability_lint.py`](../../../../../CircuitSmith/scripts/portability_lint.py).
The logic transfers near-verbatim; only the package name and the set
of forbidden host paths change.
