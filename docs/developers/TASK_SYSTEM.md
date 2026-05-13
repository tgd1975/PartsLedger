# Task System

How PartsLedger plans, tracks, and executes work. The system is an
installed copy of the upstream `awesome-task-system` package — see
[`CLAUDE.md` § Task-system installation](../../CLAUDE.md#task-system-installation)
for the install-vs-upstream relationship.

This doc is the **human-facing** counterpart to
[`AUTONOMY.md`](AUTONOMY.md). AUTONOMY.md is the agent's operational
protocol; this is the contributor's map.

## Three artefact types

| Type | Lifetime | Purpose | Example |
|---|---|---|---|
| **IDEA** | Long. Lives in `docs/developers/ideas/{open,archived}/`. | A design proposal. Captures *what* and *why* before any *how* lands. Ideas archive when they convert into epics or get rejected. | [`idea-001-partsledger-concept`](../ideas/open/idea-001-partsledger-concept.md) — the dossier behind the inventory pipeline. |
| **EPIC** | Medium. Lives in `docs/developers/tasks/{open,active,closed}/`. | A bundle of related tasks that ship together on a single branch (`release/epic-NNN-<slug>` or `feature/<slug>`). Closes when every constituent task closes. | [`epic-001-align-with-circuitsmith`](tasks/active/epic-001-align-with-circuitsmith.md) — this very epic. |
| **TASK** | Short. Lives in `docs/developers/tasks/{open,active,paused,closed}/`. | One concrete deliverable, sized Small/Medium/Large, with acceptance criteria and a test plan. The unit of one commit (or one tight commit cluster). | TASK-006 — port the 13 verbatim docs. |

## Lifecycle states

```text
        ┌─────────────────────────────────────────┐
        ▼                                         │
     open ─── /ts-task-active ──▶ active ─── /ts-task-done ──▶ closed
                  ▲                  │
                  │                  │
                  │             /ts-task-pause
                  │                  │
              /ts-task-active        ▼
                  └────────────── paused
```

| State | What it means | Folder |
|---|---|---|
| `open` | Not started; prerequisites may or may not be met. | `open/` |
| `active` | Work in progress on the current branch. Activation rides along with the first real commit. | `active/` |
| `paused` | Blocked on an unmet prerequisite. The blocker is recorded in `prerequisites:`; the task auto-resumes when the blocker closes. | `paused/` |
| `closed` | Done. `closed:` date and `effort_actual:` recorded. | `closed/` |

Status changes happen via the `/ts-*` skills below; the file's folder
follows the status automatically when `/housekeep` runs.

## The skills

| Skill | Use when |
|---|---|
| `/ts-idea-new` | Drafting a new design proposal. Scaffolds `ideas/open/idea-NNN-<slug>.md`. |
| `/ts-idea-list` | Want a list of all open ideas. |
| `/ts-idea-archive` | An idea converted into one or more epics (or was rejected); move it to `archived/`. |
| `/ts-epic-new` | Promoting a cluster of related work into an epic. Scaffolds `tasks/open/epic-NNN-<slug>.md`. |
| `/ts-epic-list` | Want a status snapshot of every epic and its task counts. |
| `/ts-task-new` | Adding a task under an existing epic. Scaffolds `tasks/open/task-NNN-<slug>.md`. |
| `/ts-task-list` | Want a list of every open and active task. |
| `/ts-task-active` | About to start work on a task — **call this before your first edit** per [CLAUDE.md § Auto-activate tasks](../../CLAUDE.md#auto-activate-tasks-when-work-begins). |
| `/ts-task-pause` | Discover mid-task that you are blocked on an unfinished prerequisite. Records the blocker and moves the file to `paused/`. |
| `/ts-task-reopen` | A closed task needs to be revisited. |
| `/ts-task-done` | Acceptance criteria met. Records `effort_actual` and moves the file to `closed/`. |

## `/housekeep` and the index files

Four files are **entirely generated** by
[`scripts/housekeep.py`](../../scripts/housekeep.py):

- [`docs/developers/tasks/OVERVIEW.md`](tasks/OVERVIEW.md) — full
  task list grouped by status.
- [`docs/developers/tasks/EPICS.md`](tasks/EPICS.md) — per-epic
  rollup with task counts.
- [`docs/developers/tasks/KANBAN.md`](tasks/KANBAN.md) — open /
  active / closed columns.
- [`docs/developers/ideas/OVERVIEW.md`](../ideas/OVERVIEW.md) — idea
  index, open vs archived.

**Manual edits to these files are lost** at the next housekeep run.
Edit the underlying task / epic / idea file; let housekeep regenerate
the index.

Run `/housekeep` after any task-system state change you make by hand
(rare; the `/ts-*` skills already invoke housekeep internally). Sweep
the regenerated indexes into the same commit as the change that
triggered them — see [`CLAUDE.md` § Task-system regen](../../CLAUDE.md#task-system-regen--use-housekeep).

## Prerequisites

Tasks declare `prerequisites: [TASK-NNN, TASK-MMM]` in frontmatter.
The semantics:

- A task with **all** prerequisites closed is *eligible* — pick it up
  any time.
- A task with **some** prerequisite still open is *blocked* — try to
  activate it and `/ts-task-active` will refuse (or, if you forced the
  activation manually, `/ts-task-pause` is the right move).
- A task pauses when work starts and a fresh prerequisite is
  discovered mid-stream. The blocker goes into the `prerequisites:`
  list; the file moves to `paused/`. Auto-resumes when the blocker
  closes.

Prerequisites are about **work order**, not about importance. A task
without prerequisites is not "trivial"; it just has no upstream
gate.

## Human-in-loop semantics

Every task carries a `human-in-loop:` field. The four values map to
distinct agent behaviours under the autonomous-implementation
protocol; the depth lives in
[`AUTONOMY.md` § Human-in-loop levels](AUTONOMY.md#human-in-loop-levels).
The contributor's view:

| Value | Means |
|---|---|
| `No` | Pure autonomous work. The agent picks the task up, finishes it, and closes it without prompting. |
| `Clarification` | The agent may pause **once** for a decision the task body explicitly names. Otherwise behaves like `No`. |
| `Support` | The agent works up to a defined stop-line in the body, hands off the rest to a human. |
| `Main` | Hands the **entire task** to a human (e.g. applying GitHub branch protection — TASK-013). |

When in doubt, the agent's contract is to read AUTONOMY.md; the
human's contract is to set the field deliberately when scaffolding
the task.

## Connection to `CLAUDE.md`

[`CLAUDE.md`](../../CLAUDE.md) is the agent-facing operating manual.
The rules that touch the task system live there:

- *Auto-activate tasks when work begins* — `/ts-task-active` before
  the first edit.
- *Commits go through /commit — always* — closing a task is one
  commit, not many.
- *Task-system regen — use /housekeep* — regen indexes ride with the
  triggering commit.
- *Task-system installation* — this is an installed copy of
  `awesome-task-system`; edits land here, upstream consulted by hand.

Cross-reference: [`AUTONOMY.md`](AUTONOMY.md) is the operational
protocol the agent runs; this doc is its prose summary.
