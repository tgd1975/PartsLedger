---
id: ADR-0002
title: Hedge-lint pattern set is the four literals from IDEA-005
status: Accepted
date: 2026-05-14
dossier-section: ../ideas/archived/idea-005-skill-path-today.md
---

## Context

TASK-019 lands IDEA-005 § Stage 1 — a mechanical backstop for the
sincere-language convention enforced today by prompt examples inside
`/inventory-add` and `/inventory-page`. The lint walks
`inventory/parts/*.md` and flags absolute-claim phrasing. The task
body lists the patterns as *"e.g. rhetorical uses of `is the`,
`must`, `always`, `never`"* — the `e.g.` made the list illustrative,
not exhaustive, and forced a calibration call between **narrow**
(only catch identity claims with MPN-shaped tokens — minimises false
positives but misses temporal and modal absolutes) and **broad**
(flag all four literals — catches more drift but produces real
finds on legitimate datasheet language).

## Decision

The lint pattern set is the **four literals** from the task body —
`is the`, `must`, `always`, `never` — matched as bare words outside
fenced code blocks, block quotes, and the `<!-- lint: ok -->`
suppression marker. Datasheet-derived absolutes (industry-standard
pinouts, hardware constraints, ELI5 figurative language) are
annotated with `<!-- lint: ok -->` rather than reworded.

## Consequences

**Easier:**

- The lint catches the full set of camera-path-drift patterns the
  convention is designed to surface, not just identity claims.
- Test coverage maps 1:1 to the patterns: one positive + one
  negative test per literal, matching the existing
  `test_lint_inventory.py` shape.
- Existing parts pages already use the marker only where
  datasheet-derived absolutes are intentional, so the marker
  density is itself signal — a page covered in markers is one to
  audit, not one the lint is harassing.

**Harder:**

- Every new parts page needs hedging review even when the
  authoring LLM is well-behaved. The marker is cheap (one HTML
  comment at end of line), but it does add visual noise to the
  six existing pages (14 markers across 5 files).
- A narrower future pattern set (e.g. MPN-token-shape gating) is
  blocked behind a superseding ADR — the precedent for
  legitimate-but-flagged absolutes is the marker, not the regex.

## See also

- [`docs/developers/ideas/archived/idea-005-skill-path-today.md`](../ideas/archived/idea-005-skill-path-today.md) — § Stage 1 prose for the hedge convention.
- [`docs/developers/tasks/active/task-019-hedge-language-lint.md`](../tasks/active/task-019-hedge-language-lint.md) — the activating task.
