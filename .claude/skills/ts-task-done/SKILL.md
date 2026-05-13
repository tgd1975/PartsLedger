---
name: ts-task-done
description: Mark a task as closed — writes effort_actual, moves the file to closed/, runs housekeep, and commits
---

# ts-task-done

The user invokes this as `/ts-task-done TASK-NNN` (or with a partial ID
like `47`), optionally with `--effort-actual SIZE` where `SIZE` is one
of the canonical six t-shirt labels (see step 2a).

Steps:

0. Run `/check-branch` to verify the current branch is not `main` before proceeding.
1. Find the matching file in `docs/developers/tasks/open/`,
   `docs/developers/tasks/active/`, or `docs/developers/tasks/paused/`
   whose name contains the given task ID (case-insensitive, e.g.
   `task-047`). If not found, report the error and stop. A paused task
   may close directly to `closed/` without an intermediate transition.

2. Update the `status:` field in the file's frontmatter to `closed`.
   Add `closed: <today's date as YYYY-MM-DD>` on the line immediately after `status: closed`.

2a. **Determine `effort_actual` and write it to frontmatter immediately
    after `effort:`.** This is a post-hoc t-shirt-size estimate of how
    big the work *actually* turned out to be. Both `effort:` (original
    estimate) and `effort_actual` stay forever; the comparison is the
    point.

    | Size | Label |
    |---|---|
    | XS  | `XS (<30m)` |
    | S   | `Small (<2h)` |
    | M   | `Medium (2-8h)` |
    | L   | `Large (8-24h)` |
    | XL  | `Extra Large (24-40h)` |
    | XXL | `XXL (>40h)` |

    - If the user passed `--effort-actual SIZE`, use that label
      directly. Reject anything outside the canonical six.
    - Otherwise pick a t-shirt size from the work product: diff size
      since `opened:`, files touched, commits between `opened:` and
      today, pause/blocker history.

    **No-peek rule.** When judging from the work product, **do not
    read the original `effort:` value first.** Read only the body and
    the diff, pick the actual, write `effort_actual:`, *then* read the
    rest of the frontmatter. The same agent estimating both ends has a
    regression-toward-"about right" bias; the chart in TASK-271 only
    earns its keep if the gap is honest.

    The no-peek rule is a behavioral nudge sequenced into this step;
    it is not enforced by tooling. Honour it deliberately.

    Insert the field immediately after `effort:` so the two sit
    adjacent in the frontmatter:

    ```yaml
    effort: Medium (2-8h)
    effort_actual: Large (8-24h)
    ```

    Once `effort_actual` is written it stays. Do not rewrite it on
    later passes; do not retroactively backfill on already-closed
    tasks.

3. Run `python scripts/housekeep.py --apply` — this moves the file to `closed/` and
   regenerates `OVERVIEW.md`, `EPICS.md`, and `KANBAN.md`.

1. Stage and commit. The closing this skill performs **owns the
   resulting OVERVIEW/EPICS/KANBAN regen** — those regen lines reflect
   *this task moving to closed*, so they are part of this commit even
   under the "commit only your own work" rule in `CLAUDE.md`.

   The pathspec list must include **both** the source path and the
   destination path of the housekeep rename. Naming only the
   destination commits the addition but leaves the source-side
   deletion orphaned in the working tree as a `D` entry — this is
   the exact bug TASK-347 fixed. Both paths must appear:

   - Source path of the rename — the file's old location, one of
     `docs/developers/tasks/active/task-NNN-<slug>.md`,
     `docs/developers/tasks/paused/task-NNN-<slug>.md`, or
     `docs/developers/tasks/open/task-NNN-<slug>.md` depending on
     where the task was before housekeep moved it.
   - Destination path —
     `docs/developers/tasks/closed/task-NNN-<slug>.md`.
   - `docs/developers/tasks/OVERVIEW.md`,
     `docs/developers/tasks/EPICS.md`,
     `docs/developers/tasks/KANBAN.md`.
   - Any per-release archive overview that housekeep just touched
     (e.g. `docs/developers/tasks/archive/v0.X.Y/OVERVIEW.md`).

   Do **not** stage unrelated working-tree changes — other in-flight
   sessions' files must stay out. If a parallel session already had
   stale OVERVIEW lines for *its* tasks, your regen will incorporate
   them; that is fine and expected — the index always reflects current
   on-disk state, not "who edited what".

   Commit via `/commit` with the message
   `close TASK-NNN: <task title from frontmatter>` and the full
   pathspec list above. Do NOT push.

2. Report: "TASK-NNN moved to closed/, overviews updated, and committed."
