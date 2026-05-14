---
id: TASK-029
title: Configure [project.optional-dependencies] for partsledger[resistor-reader] extra
status: open
opened: 2026-05-14
effort: Small (<2h)
complexity: Medium
human-in-loop: No
epic: project-setup
order: 8
prerequisites: [TASK-022]
---

## Description

Wire the `[project.optional-dependencies]` table in `pyproject.toml`
so EPIC-008's resistor reader ships as the
`partsledger[resistor-reader]` PEP 517 extra rather than a separately
named distribution.

Per IDEA-014 § Open questions (closed 2026-05-14) and IDEA-011 §
closed Q (sub-package vs sibling package): the resistor reader lives
as a sub-package inside PartsLedger, shipped as an optional extra.
That decision means three things must align here:

1. `[project.optional-dependencies]` declares the `resistor-reader`
   extra-key with the dependency set EPIC-008 needs. `opencv-python`
   is already a runtime dependency declared in TASK-002's
   `pyproject.toml`, so it does **not** repeat in the extra — only
   deps that are *only* needed by the resistor reader land here.
   Candidate set: `scikit-image`, `scipy` (confirm against EPIC-008's
   actual import surface once it lands).
2. `src/partsledger/resistor_reader/__init__.py` raises a clear
   `ImportError` when its dependencies are missing — *not* the
   default `ModuleNotFoundError` traceback, which is opaque. Message
   shape: `"partsledger.resistor_reader requires the [resistor-reader]
   extra: pip install 'partsledger[resistor-reader]'"`.
3. `.github/workflows/release.yml` (TASK-024) builds **one**
   distribution that carries the extra's metadata, not two
   distributions.

## Acceptance Criteria

- [ ] `pyproject.toml` declares `[project.optional-dependencies]` with
      a `resistor-reader` key listing the resistor-reader-only deps.
- [ ] `pip install partsledger[resistor-reader]` succeeds in a clean
      venv and the extras' packages are importable.
- [ ] Importing `partsledger.resistor_reader` without the extra
      installed raises an `ImportError` with the install-hint message.
- [ ] Importing `partsledger.resistor_reader` with the extra installed
      succeeds.
- [ ] The release workflow publishes one distribution; `pip install partsledger`
      and `pip install partsledger[resistor-reader]` both resolve
      against it.

## Test Plan

Host tests (pytest):

- `tests/test_extras.py::test_resistor_reader_missing_extra_raises_helpful_error`
  — patches `sys.modules` to simulate the extras dep being absent and
  asserts the import raises an `ImportError` carrying the install
  hint.
- `tests/test_extras.py::test_resistor_reader_imports_with_extra` —
  skipped unless the extras dep is actually installed; asserts the
  import succeeds.

## Prerequisites

- **TASK-022** — delivers the package layout that
  `src/partsledger/resistor_reader/` hangs off of.

## Notes

EPIC-008 itself ships the resistor-reader implementation; this task
only configures the *packaging* shape ahead of time so EPIC-008 can
focus on the algorithm. The actual extras dependency list may need a
follow-up commit once EPIC-008 surfaces what it truly needs — that
follow-up is in scope for EPIC-008, not this task.
