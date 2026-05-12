---
name: ts-task-reopen
description: Reopen a closed task — updates status to open, moves from closed/ to open/, runs housekeep
---

# ts-task-reopen

The user invokes this as `/ts-task-reopen TASK-NNN` (or a partial ID
like `47`).

Steps:

0. Run `/check-branch` to verify the current branch is not `main`.
1. Find the matching file in `docs/developers/tasks/closed/` whose
   name contains the given ID. If not found (not currently closed),
   report the error and stop.
2. Update the `status:` field in the frontmatter from `closed` to
   `open`. Remove the `closed: YYYY-MM-DD` line if present.
3. Run `python scripts/housekeep.py --apply` — this moves the file
   back to `open/` (via `git mv`) and regenerates OVERVIEW.md.
4. Report: "TASK-NNN reopened — moved back to open/."

Do not commit — the user commits when they start real work on the
reopened task.

**When that commit happens, the OVERVIEW/EPICS/KANBAN regen this
skill triggered is part of it.** Housekeep regenerates those three
files as a side-effect of the status change, so under the "commit
only your own work" rule in `CLAUDE.md` they count as the user/agent's
own output for this transition. Stage them alongside the renamed task
file. Other in-flight sessions' regen lines may be intermixed — that
is fine; the index reflects current on-disk state.

**Rename pathspec — both sides.** Housekeep does
`git mv closed/task-NNN.md → open/task-NNN.md`. The pathspec list
passed to `/commit` must include **both** the old (`closed/`) and
new (`open/`) paths; naming only the destination commits the
addition but leaves the source-side deletion orphaned in the working
tree as a `D` entry. This is the bug TASK-347 fixed end-to-end.
The wrapper now accepts rename sources, but it can only commit the
deletion side if you name it.
