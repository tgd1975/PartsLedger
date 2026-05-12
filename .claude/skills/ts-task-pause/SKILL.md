---
name: ts-task-pause
description: Pause an active task that is blocked — moves it to paused/, sets status: paused, records the blocker as a prerequisite
---

# ts-task-pause

The user invokes this as `/ts-task-pause TASK-NNN` (or a partial ID
like `47`), typically because executing the task surfaced a defect (or
some other blocker) that must be resolved before the task can finish.

A paused task has `status: paused` and lives in
`docs/developers/tasks/paused/`. The blocking task(s) are listed in
`prerequisites:` so the dependency graph in EPICS.md picks up the link.
A `## Paused` body section is optional documentation only — the
`status:` field is the single authoritative signal.

Steps:

0. Run `/check-branch` to verify the current branch is not `main`.
1. Find the matching file in `docs/developers/tasks/active/` whose
   name contains the given ID. If not found (not currently active),
   report the error and stop — only an active task can be paused.
2. Ask the user (in a single message) for:
   - The blocking task ID(s), e.g. `TASK-250` (comma-separated if
     multiple). May be `none` if pausing for a non-task reason.
   - A one-line reason describing what we are waiting for (will be
     added to the task body).
3. Update the file in place:
   - Change `status:` from `active` to `paused`.
   - Add or extend the `prerequisites:` frontmatter field with the
     blocking task IDs (e.g. `prerequisites: [TASK-250]`). If the
     field already exists, merge in the new IDs without duplicating.
   - Optionally append a `## Paused` section at the bottom of the body
     with the date and the user's reason, e.g.

     ```markdown
     ## Paused

     - 2026-04-26: Waiting on TASK-250 — BLE permissions defect blocks
       SC-01..SC-09 verification.
     ```

4. Run `python scripts/housekeep.py --apply` — this moves the file to
   `paused/` (via `git mv`) and regenerates OVERVIEW / EPICS / KANBAN.
5. Report: "TASK-NNN paused — blocked by `<list>`."

Do not commit — the user commits when they have processed the pause.

**When that commit happens, the OVERVIEW/EPICS/KANBAN regen this
skill triggered is part of it.** Housekeep regenerates those three
files as a side-effect of the status change, so under the "commit
only your own work" rule in `CLAUDE.md` they count as the user/agent's
own output for this transition. Stage them alongside the renamed task
file. Other in-flight sessions' regen lines may be intermixed — that
is fine; the index reflects current on-disk state.

**Rename pathspec — both sides.** Housekeep does
`git mv active/task-NNN.md → paused/task-NNN.md`. The pathspec list
passed to `/commit` must include **both** the old (`active/`) and
new (`paused/`) paths; naming only the destination commits the
addition but leaves the source-side deletion orphaned in the working
tree as a `D` entry. This is the bug TASK-347 fixed end-to-end. The
wrapper now accepts rename sources, but it can only commit the
deletion side if you name it.

**Config note:** when `tasks.paused.enabled: false` (or
`tasks.active.enabled: false` — paused depends on active), this skill
should not be invoked. The config system will handle registration; if
the skill is still invoked, fall back to the pre-paused behavior of
keeping the file in `active/` and adding a `## Paused` section without
changing `status:`, and warn the user.

## Resuming

When the blocker closes, use `/ts-task-active TASK-NNN` to resume —
that skill will move the file from `paused/` back to `active/` and
clean up the now-stale `prerequisites:` entries.
