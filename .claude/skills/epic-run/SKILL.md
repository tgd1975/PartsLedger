---
name: epic-run
description: Drive an epic to completion autonomously — walks tasks in topological order, composes over /ts-task-active, /commit, /housekeep, /ts-task-done; stops at Main/Support HIL stop-lines and surfaces a review packet.
---

# epic-run

Invoked as `/epic-run EPIC-NNN`. Drives the named epic to
completion in autonomous-implementation mode per
[`docs/developers/AUTONOMY.md`](../../../docs/developers/AUTONOMY.md).

This skill is a **composer** over existing task-system skills. It
does not re-implement state transitions. Every move through the
loop goes through `/ts-task-active`, `/commit`, `/housekeep`,
`/ts-task-done`, and `/check-branch` — bugs in those skills surface
at the composer level rather than hiding behind a wrapper.

## Preconditions

Before invoking `/epic-run`:

- [ ] Current branch matches the epic's `branch:` frontmatter
      (typically `release/epic-NNN-<slug>` or `feature/<slug>`). If
      not, `/ts-task-active` will nag on the first task; resolve via
      the `[s]witch` or `[c]ontinue` path before the loop starts in
      earnest.
- [ ] Working tree is clean (`git status` empty). The loop
      accumulates uncommitted edits while it walks; a foreign
      starting state breaks the "commit only your own work" rule.
- [ ] The user has briefed the agent on epic-specific context that
      isn't in the epic file or the dossier (rare, but
      sometimes necessary for the first task).

## Work phase

For each iteration in the work phase:

1. **Pick next task.** Walk the epic's tasks (any file under
   `docs/developers/tasks/{open,active}/` with the matching
   `epic:` field), filter to those whose `prerequisites:` are all
   closed, sort by `order:` ascending. The first remaining task is
   "next". If none, the epic is done — go straight to **Commit
   phase** (no hand-off needed; nothing for the user to do).

2. **Check HIL stop-lines.** Inspect the picked task's
   `human-in-loop:` field:

   - `No` → proceed silently.
   - `Clarification` → proceed; pause for one batched
     `AskUserQuestion` call **only** if the task body explicitly
     names a decision the user must own. Otherwise, treat as `No`.
   - `Support` → proceed up to the task body's stop-line, then
     enter the **Hand-off phase** (below) with what's accumulated
     so far.
   - `Main` → do not enter the task body. Enter the **Hand-off
     phase** (below) with what's accumulated so far.

3. **Activate.** Run `/ts-task-active TASK-NNN`. This handles the
   epic/branch nag, the open→active transition, and the index
   regeneration. Skip if the task is already `active` (e.g.
   resuming a paused mid-run).

4. **Implement.** Do the task's work — edits, tests, debugging,
   ADRs filed under the
   [ADR-on-ambiguity rule](../../../docs/developers/AUTONOMY.md#adr-on-ambiguity).
   Mid-task `AskUserQuestion` calls are **not** part of the loop;
   if the agent reaches one, that's a Clarification-HIL pause and
   the protocol applies.

5. **Definition-of-done gate.** Run the checklist from
   [AUTONOMY.md § Definition of done](../../../docs/developers/AUTONOMY.md#definition-of-done).
   Every item must pass. A failure aborts the loop with a
   diagnostic; the agent fixes and re-runs.

6. **Close in-tree.** Edit the task file frontmatter:
   `status: closed`, `closed: <today>`, `effort_actual: <size>` per
   the no-peek rule. Tick acceptance-criteria boxes. Run
   `python scripts/housekeep.py --apply` — the task file moves
   from `active/` to `closed/` and the indexes regenerate.
   **No commit is made here.** Changes accumulate in the working
   tree.

7. **Loop.** Back to step 1.

## Hand-off phase (HIL stop-lines only)

When the work phase exits because a `Support` or `Main` stop-line
was hit, the **next thing the user has to do is the stop-line task**
— and that task itself needs the user. The commit phase that
follows also needs the user (per-task commits, `/no-verify`
approvals if any, the final review packet).

Bundling those two user-interaction blocks into one is the more
humane shape: the user sits down once, finishes the stop-line task
collaboratively, and the commit phase rolls up everything in the
same session — including any artefacts the stop-line task produced.

Sequence:

1. **Surface a pre-commit review packet.** Summarise: which tasks
   are closed in-tree (counted, named with their TASK-NNN), what
   files are accumulated and not yet committed, which task triggered
   the stop-line, and what the user needs to do for that task.
   Quote the relevant section of the task body so the user does not
   have to chase the file.
2. **Collaborate on the stop-line task.** For `Main`: hand off
   entirely; the user drives the action, you stay available to
   answer questions, file ADRs, etc. For `Support`: continue past
   the in-body stop-line under the user's direction. Any artefacts
   produced (a new file, a config-applied receipt, an ADR) join the
   working tree and get committed alongside the accumulated work in
   the next phase.
3. **Close the stop-line task in-tree** if the work is done — same
   close-in-tree dance as work-phase step 6 (status, closed,
   effort_actual, ticks, housekeep). The user may decide to leave
   it open (e.g. they want to revisit later); honour that.
4. **Enter the Commit phase** below, treating the stop-line task as
   "just another task in the batch" if it closed, or omitted if it
   did not. Per-task commits in dependency order, ride-alongs at
   the end, as usual.
5. **Surface the final review packet** after the commits land.

## Commit phase

When the work phase finishes, the working tree contains the
accumulated changes from every task closed in the batch. Now split
those changes into **per-task commits**:

For each task closed in this batch, in dependency order (i.e. the
order they were closed):

1. Identify the files **that task owns** — its new files, the
   files only it modified, and the task body's open→closed rename.
2. `/commit "close TASK-NNN: <title>" <pathspec>` with just those
   files.

Shared files (the registries, settings file, OVERVIEW / EPICS /
KANBAN indexes, `scripts/README.md`) ride with the **most relevant
commit**, typically the last one in the batch. Do not roll back
shared files to reproduce an intermediate state for earlier commits
— forward references inside a coordinated branch are acceptable.

The final task's commit also carries the cumulative regen of the
indexes + `scripts/README.md`. **CHANGELOG.md is handled separately
in the CHANGELOG-delta phase below** — it is not bundled with any
per-task commit.

If a task naturally bundles with another (e.g. a mechanism task +
the first consumers of that mechanism), a single combined commit is
fine — but the default is one commit per task closure.

## CHANGELOG-delta phase

Runs **once**, after the per-task commits land and before Exit. The
job is to make `CHANGELOG.md`'s `[Unreleased]` section reflect the
work this epic-run produced, in one final commit.

The rule is **delta-only**: read what is already in `[Unreleased]`,
identify which closed tasks (and other landed changes) are **not yet
represented**, and append only the missing entries. Do not edit,
reorder, reword, or remove existing entries — they may have been
written by hand or by a prior run, and a destructive rewrite would
clobber that work.

Steps:

1. Read [`CHANGELOG.md`](../../../CHANGELOG.md). Focus on the
   `## [Unreleased]` section. Note which `TASK-NNN` IDs and which
   policy / tooling deltas are already named.
2. For each task closed in this epic-run (from the work-phase
   batch and, if applicable, the hand-off-phase stop-line task),
   check whether it is already represented. If not, draft one
   bullet under the appropriate Keep-a-Changelog subheading
   (`### Added`, `### Tooling`, `### Policy`, `### Governance`,
   `### Developer experience`, `### Autonomy`, …). One bullet per
   task; the bullet references `TASK-NNN` and names the artefact
   the task produced.
3. For the ride-along changes from the final commit (skill
   updates, config tweaks, anything that does not have a TASK ID
   but was an intentional part of the run), check whether they are
   already represented. If not, draft one bullet each under the
   appropriate subheading.
4. If the epic itself closed in this run, add a one-line
   **`EPIC-NNN closed`** bullet naming the deliverable and linking
   to the EPIC file. Place it at the bottom of the most relevant
   subheading or as its own line.
5. Choose subheadings that already exist in `[Unreleased]` over
   inventing new ones. Add a new subheading only when no existing
   one fits.
6. `/commit "chore(EPIC-NNN): update CHANGELOG with EPIC-NNN delta"
   CHANGELOG.md`.

This is the **only** way the agent touches `CHANGELOG.md` in an
epic-run. The per-task commits never edit it; the final ride-along
commit never edits it; only this phase does, and only by appending
the delta.

The squash-to-`main` merge (owned by the user) still preserves the
`[Unreleased]` content. The agent's job is to make sure the
branch's `[Unreleased]` is **already correct** by the time the
user hits "squash and merge."

## Exit

On exit (epic done OR Main/Support stop-line resolved OR
definition-of-done failure):

1. Verify the working tree is clean (every accumulated change is
   committed).
2. Surface the
   [review packet](../../../docs/developers/AUTONOMY.md#review-packet)
   to the user — this is the *final* one; the pre-commit packet
   from the Hand-off phase was the first.
3. Stop. Do not start the next iteration. Wait for the user.

## Anti-patterns

These are the failure modes the protocol exists to prevent — do
not reach for any of them.

- **Skipping `/ts-task-active`.** The epic/branch nag and the
  status transition are load-bearing; bypassing them silently
  breaks `/check-branch`, `/housekeep`, and the index files.
- **Batching commits across tasks.** Each task closure is its own
  commit on the epic's branch. The squash-merge to `main` collapses
  them — that is the user's call at merge time, not the loop's.
- **Mid-loop user prompts that aren't HIL-defined.** If you find
  yourself wanting to ask "should I continue with the next task?",
  re-read AUTONOMY.md — the answer is no, the loop drives itself
  until a defined stop-line. End-of-turn "continue?" checkpoints
  are forbidden by [`CLAUDE.md`](../../../CLAUDE.md).
- **Resolving ambiguity by stopping.** If a decision has a
  defensible default, file an ADR and continue. Stopping is the
  exception, not the default.
- **Touching files outside the task's scope.** "While I'm in
  here" edits clobber the squash-merge story and pollute the
  commit. New tasks for new work.

## When NOT to use

- The user is sitting next to you and wants to drive task-by-task.
  Use `/ts-task-active` / `/ts-task-done` directly.
- The epic has no `branch:` field, has `branch: main`, or has tasks
  with unfixed `prerequisites:` that point outside the epic. Fix
  the metadata first.
- The epic is in a half-finished state from a prior run (some
  active tasks, no clear next-up). Resolve the active task by
  hand, then re-invoke.

## Status

`/epic-run` is a **protocol scaffold** for now — the SKILL.md
above is the operational contract the agent follows; the agent
itself is the executor. A future iteration may extract the loop
into a Python driver that orchestrates the underlying skills
explicitly, with the SKILL.md retained as documentation.
