---
id: TASK-017
title: Implement src/partsledger/inventory/lint.py + scripts/lint_inventory.py shim
status: closed
closed: 2026-05-14
opened: 2026-05-14
effort: Medium (2-8h)
effort_actual: Medium (2-8h)
complexity: Medium
human-in-loop: No
epic: markdown-inventory-schema
order: 4
prerequisites: [TASK-014, TASK-022]
---

## Description

Implement the mechanical enforcement layer for `INVENTORY.md` schema
invariants, per IDEA-004 § Open questions to hone — *"Schema-invariant
enforcement against code-driven writers"*. The two existing codeowner
skills (`co-inventory-master-index`, `co-inventory-schema`) fire only
when Claude is the editor; the camera-path Python writer has no Claude
in the loop, so the schema invariants need a mechanical lint that runs
independent of the editor.

Two invocation contexts, **one implementation**:

1. **Pre-flush hook inside `writer.upsert_row()`** (TASK-016) — called
   before atomic-rename; raises with the diagnostic on violation so the
   writer never produces a malformed file.
2. **`scripts/lint_inventory.py` pre-commit shim** — same gate shape as
   `scripts/housekeep.py` and the IDEA-005 hedge-language lint. Fires
   on every commit touching `inventory/INVENTORY.md`.

The lint enforces the schema-shape invariants enumerated in IDEA-004:

- table padding (markdownlint MD060 stays clean);
- alphabetical row order within each section;
- hedge language requirement in Notes for camera-path doubt one-liners
  (Notes-cell free-text otherwise is intentionally underspecified);
- Source-column shape (non-empty lowercase token, no allow-list);
- link-into-parts/ correctness (the Part cell's optional Markdown link
  resolves to an existing `inventory/parts/<id>.md`).

Out of scope: anything free-text in Notes the schema deliberately doesn't
constrain.

Module location: `src/partsledger/inventory/lint.py`; shim:
`scripts/lint_inventory.py` (imports from the package). Pre-commit hook
wired in `scripts/pre-commit` with the same stanza shape as the existing
markdownlint stanza.

## Acceptance Criteria

- [x] `src/partsledger/inventory/lint.py` exists with a callable entry
      point that returns a list of diagnostics (or raises) per invariant
      violation.
- [x] `scripts/lint_inventory.py` exists as a thin shim that imports
      from the package and exits non-zero on diagnostics.
- [x] Each invariant (alphabetical row order, hedge
      language in Notes, Source-column shape, link-into-parts/
      correctness) is caught by a positive test (violation rejected)
      and passes a negative test (clean tree accepted).
- [x] `scripts/pre-commit` is wired to fire the lint on every commit
      touching `inventory/INVENTORY.md`.
- [x] The current `inventory/INVENTORY.md` (post-TASK-014) passes the
      lint clean.

Verification notes:

- `lint_text()` returns a list of `Diagnostic` records; the writer's
  pre-flush check (TASK-016) wraps the list in `InventoryLintError`
  on non-empty result.
- `lint_path()` is the file-path convenience wrapper used by both
  the pre-commit shim and the test suite.
- `tests/unit/test_lint_inventory.py` — 16 tests covering: Source
  shape (empty / mixed-case / whitespace / unknown-but-lowercase),
  alphabetical order (positive + linked-Part-sort-by-visible-text +
  negative), hedge language (camera+hedge / camera+no-hedge /
  manual+no-hedge / camera+empty-notes), parts-link (existing +
  missing target), `InventoryLintError` integration, and a smoke
  test confirming the checked-in `inventory/INVENTORY.md` lints
  clean.
- **Scoping note on "table padding":** the task body lists table
  padding as an invariant, but MD060 is enforced by the
  markdownlint-cli2 stanza already in `scripts/pre-commit` (and the
  full repo gate runs over the same file). The inventory lint
  module deliberately does **not** duplicate that check — its job
  is the schema-level invariants markdownlint cannot see (column
  shape, row order, hedge language, link resolution). This is
  noted explicitly in `lint.py`'s module docstring.
- The `scripts/pre-commit` stanza fires only when
  `inventory/INVENTORY.md` is in the staged-paths set (`git diff
  --cached --diff-filter=ACM`), mirroring the existing
  markdownlint / ruff gates' shape.
- Activates a permission allowlist entry
  `Bash(python scripts/lint_inventory.py:*)` in
  `.claude/settings.json` so the agent can run the linter without a
  prompt (riding alongside this commit per the "commit only your
  own work" rule).

## Test Plan

**Host tests (pytest):** `tests/unit/test_lint_inventory.py` — one test
per invariant (positive + negative). Pre-commit hook activation verified
manually.

## Prerequisites

- **TASK-014** — delivers the `Source` column and section-flex schema
  the lint validates against.
- **TASK-022** — delivers the `src/partsledger/` package layout the
  lint module lives in.
