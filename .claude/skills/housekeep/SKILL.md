---
name: housekeep
description: Run scripts/housekeep.py --apply and stage the regenerated task-system index files (OVERVIEW.md, EPICS.md, KANBAN.md, ideas OVERVIEW). Use this after any task-system file change instead of running the script directly.
---

# housekeep

Invoked as `/housekeep` whenever you would otherwise run
`python scripts/housekeep.py --apply` by hand — i.e. after any of:

- a task `status:` change you didn't make via `/ts-task-active` /
  `/ts-task-done` / `/ts-task-pause` / `/ts-task-reopen` (those skills
  already invoke housekeep internally),
- a manual idea move under `docs/developers/ideas/`,
- an epic edit (rename, owner change, frontmatter tweak),
- any other ad-hoc OVERVIEW regen.

The skill is a thin wrapper that owns the canonical invocation, prints
the move summary housekeep emits, and stages the regenerated index
files so they ride along with whatever change triggered the regen.

## Steps

1. Run housekeep:

   ```bash
   python scripts/housekeep.py --apply
   ```

   The script prints a summary of file moves and which index files it
   regenerated. Pass that summary through to the user verbatim — do
   not paraphrase, the move list is the receipt.

2. Stage the regenerated index files. Per the project's "OVERVIEW/
   EPICS/KANBAN regen belongs in the status-change commit" rule, these
   are *your* output for the change that triggered this skill:

   ```bash
   git add docs/developers/tasks/OVERVIEW.md \
           docs/developers/tasks/EPICS.md \
           docs/developers/tasks/KANBAN.md \
           docs/developers/ideas/OVERVIEW.md
   ```

   If any of those files is unchanged, `git add` is a no-op for it —
   safe.

3. If housekeep performed file moves (the summary lists `MOVE …`
   lines), also stage the moved task files. Each line has the form
   `MOVE <old-path> -> <new-path>`; stage both paths so git records
   the rename.

4. Do **not** stage anything housekeep did not touch. Per the project's
   "commit only your own work" rule, foreign working-tree changes from
   parallel sessions stay where they are.

5. Do **not** create a commit. The staged regen rides along with the
   change that triggered it — the caller commits.

## When NOT to use

- Inside `/ts-task-active`, `/ts-task-done`, `/ts-task-pause`,
  `/ts-task-reopen` — those skills already run housekeep themselves.
- For a `--check` (read-only) audit. Run `python scripts/housekeep.py`
  without `--apply` directly; this skill is the apply-side wrapper.

## Skill registration

Registered in [.vibe/config.toml](../../../.vibe/config.toml)'s
`enabled_skills` list per the project's CLAUDE.md skill-registration
rule.
