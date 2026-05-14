---
id: TASK-023
title: Port RELEASING.md and /release skill; rewrite semver for three public surfaces
status: closed
opened: 2026-05-14
closed: 2026-05-14
effort: Medium (2-8h)
effort_actual: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: project-setup
order: 2
prerequisites: [TASK-022]
---

## Description

Port CircuitSmith's release pipeline — [`RELEASING.md`](../../../../../CircuitSmith/RELEASING.md)
and the [`/release` skill](../../../../../CircuitSmith/.claude/skills/release/SKILL.md)
— into PartsLedger, and rewrite the semver policy to cover **three**
public surfaces instead of CircuitSmith's two.

Per IDEA-014 § What to port — second bullet and § Open questions —
public-surface definition: CircuitSmith's semver policy keys on the
Python API (`from circuitsmith import …`) plus its documented CLI
entry points. PartsLedger has a third public surface that CircuitSmith
lacks: the inventory-MD schema defined in [IDEA-004](../ideas/open/idea-004-markdown-inventory-schema.md),
which CircuitSmith itself consumes via `--prefer-inventory`. Schema-
breaking changes (renaming a frontmatter key, dropping a column,
changing the row format in `INVENTORY.md`) must bump MAJOR even if the
Python API is byte-identical.

The three surfaces, in the order `RELEASING.md` must list them:

1. **Python API** — `from partsledger import …`. New exports under
   `partsledger.*` bump MINOR; removed or renamed exports bump MAJOR.
2. **CLI** — every command registered via `[project.scripts]` in
   `pyproject.toml`. New flags MINOR; removed flags or changed defaults
   MAJOR.
3. **Inventory-MD schema** — the frontmatter schema in
   `inventory/parts/<part>.md` plus the row format in
   `inventory/INVENTORY.md`. Additive keys MINOR; renamed or removed
   keys MAJOR.

## Acceptance Criteria

- [x] `RELEASING.md` exists at the repo root, documents all three
      public surfaces with the MAJOR / MINOR / PATCH rules above.
- [x] `.claude/skills/release/SKILL.md` exists, parallels CircuitSmith's
      shape, and references PartsLedger's three surfaces (not
      CircuitSmith's two).
- [x] `enabled_skills` in `.vibe/config.toml` includes `release`.
- [x] A dry-run release (`/release --dry-run` or equivalent) walks
      through version-bump, changelog roll, and tag creation without
      errors and without publishing.
- [x] CHANGELOG bullet under `[Unreleased] / ### Tooling` records the
      port in the same squash.

## Test Plan

No automated tests required — change is non-functional plumbing.
Validation: read through the ported `RELEASING.md` with EPIC-004's
overall acceptance criteria in mind; dry-run the `/release` skill on
a throwaway branch.

## Prerequisites

- **TASK-022** — delivers the `src/partsledger/` layout that the
  Python-API public surface is defined against; `RELEASING.md` cannot
  enumerate exports until the package exists.

## Notes

Cross-reference CircuitSmith's [`RELEASING.md`](../../../../../CircuitSmith/RELEASING.md)
and [`release` skill](../../../../../CircuitSmith/.claude/skills/release/SKILL.md)
verbatim before rewriting — most of the mechanics (version-bump,
changelog roll, tag, push) transfer unchanged. The only material
divergence is the public-surface count.
