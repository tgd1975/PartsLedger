---
id: TASK-014
title: Add Source column and maker-choice section taxonomy to INVENTORY.md
status: open
opened: 2026-05-14
effort: Medium (2-8h)
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

- [ ] The pre-edit `INVENTORY.md` re-validates clean against
      `co-inventory-master-index` after the backfill.
- [ ] A test row added via `/inventory-add` carries `Source: manual` and
      lands under an existing section.
- [ ] Renaming a section in `INVENTORY.md` (e.g. `## ICs` →
      `## Linear ICs`) and re-running the guard does not error.
- [ ] Shape violations on `Source` (empty cell, whitespace, mixed-case)
      still error per the lowercase-token rule.
- [ ] `markdownlint` (MD060 in particular) is clean on the updated file.
- [ ] `CHANGELOG.md` carries the schema bullet under `[Unreleased] /
      ### Schema`.

## Test Plan

No automated tests required — markdownlint + existing pre-commit hooks
cover the structural changes; manual validation per Acceptance Criteria.
