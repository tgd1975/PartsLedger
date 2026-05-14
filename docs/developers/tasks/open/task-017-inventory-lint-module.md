---
id: TASK-017
title: Implement src/partsledger/inventory/lint.py + scripts/lint_inventory.py shim
status: open
opened: 2026-05-14
effort: Medium (2-8h)
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

- [ ] `src/partsledger/inventory/lint.py` exists with a callable entry
      point that returns a list of diagnostics (or raises) per invariant
      violation.
- [ ] `scripts/lint_inventory.py` exists as a thin shim that imports
      from the package and exits non-zero on diagnostics.
- [ ] Each invariant (table padding, alphabetical row order, hedge
      language in Notes, Source-column shape, link-into-parts/
      correctness) is caught by a positive test (violation rejected)
      and passes a negative test (clean tree accepted).
- [ ] `scripts/pre-commit` is wired to fire the lint on every commit
      touching `inventory/INVENTORY.md`.
- [ ] The current `inventory/INVENTORY.md` (post-TASK-014) passes the
      lint clean.

## Test Plan

**Host tests (pytest):** `tests/unit/test_lint_inventory.py` — one test
per invariant (positive + negative). Pre-commit hook activation verified
manually.

## Prerequisites

- **TASK-014** — delivers the `Source` column and section-flex schema
  the lint validates against.
- **TASK-022** — delivers the `src/partsledger/` package layout the
  lint module lives in.
