---
name: ts-task-active
description: Set a task to active — updates status, moves to active/, runs housekeep. Also resumes paused tasks (paused/ → active/ or active/ with closed prerequisites).
---

# ts-task-active

Invoked as `/ts-task-active TASK-NNN` (or a partial ID like `47`).

**Who triggers this.** Either the user explicitly, or — per the project's
"Auto-activate tasks when work begins" rule in `CLAUDE.md` — the agent itself
the moment it begins making repo-state-changing edits for `TASK-NNN`. The
agent triggers ahead of the first edit, not after. Pure reading / planning
does not count as "starting work".

This skill has three modes depending on where the task currently lives:

- **Activating an open task** (file is in `open/`): standard
  open → active transition.
- **Resuming a paused task** (file is in `paused/`, `status: paused`):
  flip `status:` back to `active`, clean up any closed `prerequisites:`,
  and let housekeep move the file to `active/`.
- **Legacy resume of a pseudo-paused task** (file is in `active/` with
  one or more closed `prerequisites:` — pre-paused-folder model): no
  move needed; just clean up the stale prerequisite entries and the
  `## Paused` body section.

Steps:

0. Run `/check-branch` to verify the current branch is not `main`.
1. Find the matching file in `docs/developers/tasks/open/`,
   `docs/developers/tasks/paused/`, or `docs/developers/tasks/active/`
   whose name contains the given ID. If not found, report the error
   and stop.
2. **Branch-mismatch nag (soft).** If the task's frontmatter has an
   `epic:` field, locate the matching epic file under
   `docs/developers/tasks/{open,active,closed}/` (filename
   `epic-NNN-<name>.md`, frontmatter `name: <epic-name>`) and read its
   `branch:` field. Compare to the current git branch.

   - If the task has no `epic:`, or the epic has no `branch:`, or the
     epic's `branch:` matches the current branch — silently proceed
     to step 3. Make no diff to the epic file.
   - On mismatch, prompt the user (one message, two options):

     ```
     This task's epic (<epic-name>) suggests branch `<epic-branch>`,
     but the current branch is `<current-branch>`.
       [s]witch    — git checkout <epic-branch>
       [c]ontinue  — keep <current-branch> and rewrite the epic's
                     `branch:` to <current-branch>
     ```

     - **[s]witch** — run `git checkout <epic-branch>`. If the branch
       does not exist locally, ask once whether to create it with
       `git checkout -b <epic-branch>`; on yes, create and switch; on
       no, abort the activation. After a successful switch, continue
       with step 3 on the new branch.
     - **[c]ontinue** — use `Edit` to rewrite the epic file's
       `branch:` line to the current branch. Leave the change
       unstaged — housekeep in step 3 picks up the new value, and the
       user commits it together with the task activation.

   This check composes with `/check-branch` — do not suppress either.
   On `main` with a mismatched epic, both warnings fire in order.
3. Branch by current folder:
   - **In `open/`**: update `status:` from `open` to `active`. Do not
     add a `closed:` line. Run `python scripts/housekeep.py --apply`
     — this moves the file to `active/` (via `git mv`) and regenerates
     OVERVIEW / EPICS / KANBAN. Report: "TASK-NNN is now active."
   - **In `paused/`**: update `status:` from `paused` to `active`.
     For each ID in `prerequisites:`, check whether the corresponding
     task is in `closed/`. Remove every closed ID from
     `prerequisites:` (drop the field entirely if the list becomes
     empty). Optionally shorten the `## Paused` section in the body
     to a one-line history note, or delete it. Run
     `python scripts/housekeep.py --apply` — this moves the file from
     `paused/` to `active/`. Report:
     "TASK-NNN resumed — cleared prerequisites: `<list>`."
   - **In `active/` with closed prerequisites** (legacy pre-paused-folder
     model): clean up closed `prerequisites:` and the `## Paused` body
     section as above, but no folder move is needed. Run
     `python scripts/housekeep.py --apply`. Report:
     "TASK-NNN resumed — cleared prerequisites: `<list>`."
   - **In `active/` with no closed prerequisites**: report "already
     active" and stop. (Either the task was never paused, or its
     blockers are still open.)

Do not commit. The status change rides along with the first real
commit for the task — whether that commit is made by the user or by
the agent doing the work.

**When that first commit happens, the OVERVIEW/EPICS/KANBAN regen
this skill triggered is part of it.** Housekeep regenerates those
three files as a side-effect of the status change, so under the
"commit only your own work" rule in `CLAUDE.md` they count as the
agent's own output for this transition. Stage them alongside the
renamed task file (and the task's source-code changes) in that first
commit. Other in-flight sessions' regen lines may be intermixed —
that is fine; the index reflects current on-disk state.

**Rename pathspec — both sides.** Housekeep does `git mv old → new`
(e.g. `open/task-NNN.md → active/task-NNN.md`). The pathspec list
passed to `/commit` must include **both** the old and new paths;
naming only the destination commits the addition but leaves the
source-side deletion orphaned in the working tree as a `D` entry.
This is the bug TASK-347 fixed end-to-end. The wrapper now accepts
rename sources, but it can only commit the deletion side if you name
it.

**Config note:** when `tasks.active.enabled: false` (TASK-217), this
skill should not be invoked. The config system will handle
registration; if the skill is still invoked, treat `active` as `open`
and warn the user. When `tasks.paused.enabled: false`, the
paused-folder branch is unreachable (no files live there); the legacy
active-with-prerequisites branch still applies.

## Escape hatch (rare)

Active or paused → open is **manual** — there is no `--to-open` flag.
If you genuinely need to revert (e.g. "I activated this by mistake"),
edit `status:` back to `open`, `git mv` the file to `open/`, and run
`python scripts/housekeep.py --apply`. Document the reason in the body.
