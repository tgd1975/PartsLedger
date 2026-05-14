---
id: TASK-014
title: Add Source column and maker-choice section taxonomy to INVENTORY.md
status: closed
closed: 2026-05-14
opened: 2026-05-14
effort: Medium (2-8h)
effort_actual: Small (<2h)
complexity: Medium
human-in-loop: No
epic: markdown-inventory-schema
order: 1
---

## Description

Land IDEA-004 Stage 1 — the new `Source` column on every `INVENTORY.md`
table and the maker-choice section taxonomy — in one squashed commit. The
runtime guard, the row format, and the row-writing skill must agree on the
new shape before any of it ships.

The `Source` column records who added the row (`manual` for human-curated
or `/inventory-add`; `camera` for the visual-recognition pipeline). It is
the only provenance axis the schema carries — no separate "confidence" or
"to confirm" column. The set is intentionally open: a future importer may
add its own literal (`imported`) without a schema bump.

Section taxonomy stops being a fixed list. The guard enumerates `## …`
headings from the file at lint time and requires each row to live under
*some* H2, not under a specific one — so a maker who renames `## ICs` to
`## Linear ICs` or adds a `## Connectors` section does not trip the lint.

Per IDEA-004 § Stage 1, four touchpoints change:

1. **`inventory/INVENTORY.md`** — add the `Source` column header to every
   section's table; backfill `manual` on every existing row; restore
   table padding so markdownlint MD060 stays clean. One-shot hand edit
   at current scale.
2. **`.claude/skills/co-inventory-master-index/SKILL.md`** — recognise
   the seven-column header (`Part | Qty | Description | Datasheet |
   Octopart | Source | Notes`); validate `Source` as a non-empty
   lowercase token with **no allow-list**; stop hard-coding section
   names and enumerate `## …` headings from the file instead.
3. **`.claude/skills/inventory-add/SKILL.md`** — write `Source: manual`
   on every row. Fall back to the default section list only when no
   `## …` heading exists yet; otherwise propose from sections already
   present.
4. **`CHANGELOG.md`** — one bullet under `[Unreleased] / ### Schema`
   naming both schema changes with the task reference, riding in the
   same squash.

## Acceptance Criteria

- [x] The pre-edit `INVENTORY.md` re-validates clean against
      `co-inventory-master-index` after the backfill.
- [x] A test row added via `/inventory-add` carries `Source: manual` and
      lands under an existing section.
- [x] Renaming a section in `INVENTORY.md` (e.g. `## ICs` →
      `## Linear ICs`) and re-running the guard does not error.
- [x] Shape violations on `Source` (empty cell, whitespace, mixed-case)
      still error per the lowercase-token rule.
- [x] `markdownlint` (MD060 in particular) is clean on the updated file.
- [x] `CHANGELOG.md` carries the schema bullet under `[Unreleased] /
      ### Schema`.

Verification notes:

- All six standard parts tables (MCUs, ICs, Sensors, Modules /
  breakouts, Bulk / kits → Loose / discrete on hand) now carry the
  seven-column header `Part | Qty | Description | Datasheet |
  Octopart | Source | Notes` with `Source: manual` backfilled.
- The Transistors (DDR/USSR) table keeps its custom shape and
  appends `Source` as the final column with `manual` on every row,
  per the maker's design-time decision recorded in this task's
  scoping question.
- Pure kit-content tables (E12 decade ranges, capacitor
  assortment voltages) are not parts tables and are intentionally
  left at their original column shape with no `Source` cell.
- `markdownlint-cli2` returns `0 error(s)` over `INVENTORY.md` and
  both updated skill files.
- The codeowner-master-index skill now explicitly enumerates `## …`
  headings rather than hard-coding the section list, and validates
  `Source` as a non-empty lowercase token with no allow-list.
- The `/inventory-add` skill instructs writing `Source: manual` on
  every new row and proposes sections from existing headings.
- The `CHANGELOG.md ### Schema` bullet lands in the
  CHANGELOG-delta phase at the end of the epic-run (per
  `/epic-run` SKILL.md), bundled with the other TASK-NNN
  bullets — not in this task's per-task commit.

## Test Plan

No automated tests required — markdownlint + existing pre-commit hooks
cover the structural changes; manual validation per Acceptance Criteria.
