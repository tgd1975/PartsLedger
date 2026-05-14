---
id: TASK-022
title: Adopt src/partsledger/ layout in pyproject
status: closed
closed: 2026-05-14
opened: 2026-05-14
effort: Medium (2-8h)
effort_actual: Small (<2h)
complexity: Senior
human-in-loop: No
epic: project-setup
order: 1
---

## Description

Land the canonical `src/partsledger/` package layout that every Phase 1+
camera-path module hangs off of. This is the keystone task of EPIC-004 —
no other Python module in PartsLedger is importable as `partsledger.*`
until this lands.

Per IDEA-014 § What to port — first bullet: flip
[`pyproject.toml`](../../../../pyproject.toml) from the current
`[tool.setuptools] py-modules = []` opt-out to a proper src-layout
discovery block (`[tool.setuptools.packages.find] where = ["src"]`),
create `src/partsledger/__init__.py` with the package version constant,
and audit the repo for any stray under-root Python that needs to move
into the package. The current pyproject explicitly opts out of package
discovery with the comment "No importable Python package yet" — that
comment goes.

Audit step before editing: walk the repo root for any `*.py` outside
`scripts/`, `tests/`, `.claude/`, and `src/`; classify each finding as
either *moves into `src/partsledger/`* or *stays where it is* (e.g.
top-level `conftest.py`). Anything moved must keep working from its
new import path — adjust callers in the same commit.

## Acceptance Criteria

- [x] `pyproject.toml` declares `[tool.setuptools.packages.find] where = ["src"]`
      and no longer carries `py-modules = []`.
- [x] `src/partsledger/__init__.py` exists with a `__version__` constant.
- [x] `pip install -e .` succeeds in a clean venv.
- [x] `python -c "import partsledger; print(partsledger.__version__)"` prints
      the declared version.
- [x] `pytest` from the repo root still collects and passes (zero tests is
      acceptable; collection errors are not).
- [x] Any under-root `*.py` that moved into the package has its callers
      updated in the same commit.

Verification notes: `pip install -e . --no-deps` in a fresh
`python -m venv` (no torch/transformers download) succeeds and
`import partsledger` resolves to `0.1.0.dev0`. Pytest collects 141
existing tests with no collection errors. Root-level audit found no
`*.py` outside `scripts/`, `tests/`, `.claude/`, `src/` — nothing to
move.

## Test Plan

Host tests (pytest):

- In a fresh venv: `uv venv && source .venv/bin/activate && uv pip install -e .[dev]`.
- Run `python -c "import partsledger; print(partsledger.__version__)"`.
- Run `pytest` from the repo root and confirm collection is clean.
- Confirm `pip install -e .` (no extras) also succeeds.

## Notes

This task ships an empty (or near-empty) `partsledger` package. That is
intentional: it carves the namespace so EPIC-005 (camera capture),
EPIC-006 (visual recognition), EPIC-007 (metadata enrichment), and
EPIC-008 (resistor reader) can land their modules immediately on top
without each one re-litigating layout.

Cross-reference: CircuitSmith ADR-0012 (sibling repo, at
`docs/developers/adr/0012-library-as-installable-package.md`) is the
model decision. TASK-030 captures the PartsLedger-side ADR.
