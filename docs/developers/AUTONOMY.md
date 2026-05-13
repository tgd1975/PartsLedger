# Autonomous-implementation mode

This document codifies the operational protocol for autonomous epic
runs in PartsLedger. The user's goal: brief at the start, review at
the end, intervene only on rare occasions in between. The task system
already supplies the mechanical pieces (`/ts-task-active`,
`/ts-task-done`, `/housekeep`, `/commit`, `/check-branch`,
`human-in-loop` labels); this protocol turns them into a coherent
loop the agent can drive.

The protocol is the operational contract. The `human-in-loop`
frontmatter field is **not** a label — it has defined semantics
(see [§ HIL semantics](#hil-semantics)) and the agent honours them.

If anything below is ambiguous, the agent picks the most defensible
option, files an ADR under [`docs/developers/adr/`](adr/), and
continues. ADRs are reviewed in batch at the next stop-line.

## HIL semantics

Every open task has a `human-in-loop:` field with one of four values.
The agent's behaviour for each:

| Value | Agent behaviour |
|---|---|
| **No** | Fully autonomous. Activate → implement → test → commit → close. Hit `/ts-task-done` without pausing. Mid-task ambiguities are resolved by the [ADR-on-ambiguity rule](#adr-on-ambiguity). |
| **Clarification** | Mostly autonomous, but pause for one batched question if the task body explicitly names a decision the user must own (e.g. "the proposed sweep — to be confirmed in one batched user decision"). All such questions land in one `AskUserQuestion` call, not sequentially. |
| **Support** | Autonomous up to a defined stop-line in the task body; then surface a [review packet](#review-packet) and exit. Resumes when the user responds. |
| **Main** | Auto-prepare up to the stop-line, then **stop**. Main-HIL tasks are typically irreversible / physical / remote-push steps (applying GitHub branch protection, cutover PR). The agent never executes the irreversible step on its own; it surfaces the review packet and waits. |

A task without an explicit `human-in-loop:` field defaults to **No**.

## ADR-on-ambiguity

When the agent encounters a decision mid-task with no defensible
default — multiple reasonable options, each costing real
trade-offs — it:

1. Picks the option most consistent with the existing ADRs and the
   IDEA-004 — IDEA-009 dossier set (the per-toolchain-piece design docs).
2. Records the decision in a new ADR under [`docs/developers/adr/`](adr/)
   using the format from [`adr/README.md`](adr/README.md).
3. Continues the task.

ADRs are reviewed in batch at the next stop-line (typically the
end-of-epic [review packet](#review-packet)). The user can
supersede a freshly-filed ADR there — the dossier's adversary
review is fast and cheap once the work is otherwise complete.

If the agent **cannot** pick a defensible default — the trade-offs
are roughly balanced and the choice is load-bearing — that's the
exception that warrants a `Clarification` pause instead of an ADR.

## Epic-driver loop

`/epic-run EPIC-NNN` (see [`.claude/skills/epic-run/SKILL.md`](../../.claude/skills/epic-run/SKILL.md))
drives one epic to completion. The loop has two phases —
**work phase** (accumulate changes in the working tree, no
commits) and **commit phase** (split the accumulated changes into
per-task commits at the end).

### Work phase

For each task in the epic, in `prerequisites + order` topological
order:

```text
work-phase loop:
  next = pick next task with all prerequisites closed
  if no such task or epic is done:
    exit loop
  /ts-task-active <next>
  implement the task — edits, tests, debugging
  run the definition-of-done checklist (see § below)
  edit the task file: status → closed, closed: <date>,
    effort_actual: <size>, tick acceptance criteria
  python scripts/housekeep.py --apply
  if next.human-in-loop == "Main":
    surface review packet and exit (do not advance)
  if next.human-in-loop == "Support" and stop-line reached:
    surface review packet and exit
```

The work phase does **not** commit. Changes accumulate in the
working tree across all tasks in the batch. The indexes regenerate
on each `/housekeep` invocation; their final state reflects all
closed tasks at the end of the batch.

### Commit phase

When the work-phase loop exits, commit the accumulated changes
as **one commit per task closure** (or one per logical unit when
several tasks naturally bundle, e.g. a setup task plus its
immediate uses). Order matters: commit the foundational task
first, dependent tasks after.

For each task's commit, the pathspec is the files **that task
owns** — its new files, its modified files, and the task body's
open→closed rename. Shared files (the registry, the settings
file, indexes, CHANGELOG, scripts/README) ride with the most
relevant commit, typically the last one in the batch. **Do not
roll back shared files** to reproduce an intermediate state for
earlier commits — forward references inside a coordinated branch
are acceptable; the branch is only meaningful as a whole.

The final task's commit also carries:

- The cumulative OVERVIEW / EPICS / KANBAN regen.
- The CHANGELOG `[Unreleased]` bullets covering every closed task
  in the batch.
- `scripts/README.md` regen if any scripts were added.

The loop is a composer over existing skills (`/check-branch`,
`/ts-task-active`, `/commit`, `/housekeep`, `/security-review`) —
it does **not** re-implement state transitions. Skill bugs surface
at the composer level rather than hiding behind a wrapper.

When the commit phase finishes, the agent reports an end-of-epic
review packet (see [§ Review packet](#review-packet)) and waits.
The branch is **not** merged into `main` automatically — that's
the user's call after review.

## Definition of done

Before invoking `/ts-task-done` on any task, the agent verifies:

- [ ] Every acceptance-criteria checkbox in the task body is ticked,
      with a one-line justification in the body when the AC was met
      in a non-obvious way.
- [ ] Tests for the task's deliverable pass locally (`pytest` if
      Python; relevant subset if other).
- [ ] `ruff check` passes on every `*.py` file in the pathspec.
- [ ] `markdownlint-cli2` passes on every `*.md` file in the
      pathspec.
- [ ] `/housekeep` shows no unexpected moves (only the task's own
      open→active or active→closed transition).
- [ ] `/commit` succeeds without `PL_COMMIT_BYPASS` and without
      `--no-verify`. Hook-failure-bypass under the three-check
      protocol is permitted with explicit user approval.

A task closure that requires bypass is **not** done; the bypass is
a stop-line that the agent surfaces, not a routine path.

## Review packet

When the agent stops at a Main / Support stop-line or at end of
epic, it reports:

```text
EPIC-NNN review packet
======================

Branch:        release/epic-NNN-<slug>
Commits ahead: <n>
Tests:         <pass / fail counts>
Lints:         <pass / fail per gate>

Tasks closed in this run:
  - TASK-XXX: <title> (<effort_actual>)
  - …

ADRs filed during the run:
  - ADR-NNNN: <title>
  - …

Open questions (require user input):
  - <one-line question>
  - …

Next stop-line (if applicable):
  TASK-YYY (HIL: Main / Support) — <reason>
```

The user then reviews, supersedes any ADRs they disagree with,
answers open questions, and either resumes the loop or sends the
agent back with concrete fixes.

## No-published-effect-without-approval

The agent **never** runs a command that publishes state to a shared
system without explicit per-invocation user approval. Two
enforcement paths exist; they cover different scenarios:

- **Hard deny** (`.claude/settings.json` `permissions.deny`) for
  commands that are *never* OK by policy: `git push origin main` /
  `git push --force` (always user-driven so reflog recovery stays
  available), `git add` (forbidden by the `/commit` pathspec rule),
  and the Bash-only alternatives to dedicated tools (`sed`, `awk`,
  `head`, `tail`). The harness blocks the call outright.
- **Prompt-by-default** (the harness's normal approval path) for
  commands that are *sometimes* OK with explicit approval:
  `gh pr create`, `gh pr merge`, `gh api … -X PUT/DELETE/POST`,
  `--no-verify`, `PL_COMMIT_BYPASS`. Each invocation surfaces a
  permission prompt; the user approves or rejects per-call. No
  deny entry needed — the prompt itself is the approval mechanism.

This is the load-bearing safety property of autonomous operation.
A pure local-state mistake is reversible (reflog, reset); a
published-state mistake (force-pushed main, merged PR) is not.

## Implementation log

Each epic file gains a `## Implementation log` section. After every
task closure that lands on the epic's branch, the agent appends one
line:

```markdown
- 2026-05-13 — TASK-NNN closed (ADRs filed: …). Effort actual:
  Small. Notes: <one-line if non-obvious>.
```

The log is append-only — historical lines are never edited. It is
the running record of what landed when, paired with the commit
history's view of "what changed". `housekeep.py` does **not**
maintain this section; the agent writes it as part of each task's
close commit.

## Per-epic branch convention

Every open epic file has a `branch:` field set to its working
branch — scheme `release/epic-NNN-<slug>` or `feature/<slug>`.
`main` is **not** an acceptable value.

[`/ts-task-active`](../../.claude/skills/ts-task-active/SKILL.md)
nags on epic/branch mismatch and offers `[c]ontinue` to rewrite
the epic's `branch:` to the current branch. The `[c]ontinue` path
is the routine flow — use it when the branch is correct but the
epic's frontmatter is stale.

## Composition with `/check-branch` and `/commit`

The autonomous loop composes with the existing safety skills, not
around them:

- [`/check-branch`](../../.claude/skills/check-branch/SKILL.md)
  refuses commits on `main`. The autonomous loop runs on the
  epic's branch (created up-front by the user invoking
  `/epic-run`); `/check-branch` is a backstop.
- [`/commit`](../../.claude/skills/commit/SKILL.md)'s
  hook-failure protocol applies unchanged. The autonomous loop
  surfaces a hook failure as a review-packet item rather than
  silently bypassing.
- The post-merge security review applies unchanged. The autonomous
  loop reports its findings in the review packet so the user can
  approve / roll back.

## Pointers

- [`CLAUDE.md`](../../CLAUDE.md) `## Autonomy` — one-paragraph rule
  pointing at this file.
- [`adr/0000-template.md`](adr/0000-template.md) — template for
  ADRs filed mid-run.
