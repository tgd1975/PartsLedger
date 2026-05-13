# Project: PartsLedger

> *PartsLedger keeps the record. [CircuitSmith](../CircuitSmith/) reads it before forging.*

PartsLedger is an LLM-native inventory for an electronics parts bin: USB camera
captures a part, the pipeline (DINOv2 embeddings → Claude Opus 4.7 Vision →
Nexar/Octopart) identifies it, and the result lands in
`inventory/parts/<part>.md`. See [`README.md`](README.md) for the vision and
[`docs/developers/ideas/`](docs/developers/ideas/) (IDEA-004 — IDEA-009) for
the per-toolchain-piece dossiers.

## OS context

This project is developed on both **Windows 11** and **Ubuntu**. At the start
of every session, check the platform from the system environment info (or run
`uname -s`) and apply the correct shell syntax. Run `/os-context` if in doubt.

## Missing executables

When a CLI tool or Python package is not found (e.g. `markdownlint`, `torch`,
`cv2`, `sqlite_vec`):

1. Try once with the most obvious alternative (`uv pip`, `npx`, full path).
2. If it still fails, **stop and ask the user** to install it — do not spiral
   through fallback strategies or reimplement the tool's logic.

PartsLedger has a lot of heavyweight dependencies (PyTorch, OpenCV, sqlite-vec,
optionally PaddleOCR/Tesseract). Use `/check-tool` before invoking commands
that depend on them.

## Inventory is the source of truth

`inventory/parts/*.md` files are the **only** authoritative store. Everything
else is regenerable:

- `inventory/.embeddings/vectors.sqlite` — DINOv2 cache, rebuildable from images + MDs.
- `inventory/README.md` — auto-generated index + stats.

Never write to the SQLite DB without a corresponding `.md` update.
Never edit `.md` files without keeping them schema-compatible with the
CircuitSmith component-profile format (see [`IDEA-004 § Example`](docs/developers/ideas/open/idea-004-markdown-inventory-schema.md#example--an-lm358n-entry)).

## Bash commands — no diagnostic suffix

Do not append `; echo "EXIT=$?"`, `&& echo OK`, or similar diagnostic chains
to Bash tool invocations. The Bash tool already reports exit codes in its
result, so the suffix is redundant. It also defeats the project's permission
allowlist: the matcher checks the whole command string, and a compound like
`cmd ; echo …` requires *both* halves to satisfy an allow rule. Since
`Bash(echo:*)` is deliberately **not** allow-listed (adding it would just
train the wrong chaining habit), the suffix forces a permission prompt even
when the primary command is allowed.

Just run the command; trust the tool result for success/failure signal.

## Human interaction — batch questions, don't loop

If N questions can be asked simultaneously, ask all N at once. Only use a
sequential loop when each answer genuinely depends on the previous one.

## No end-of-turn "continue?" checkpoints

Do **not** ask "want me to continue with the next task, stop here, or do
something else?" at the end of a successful turn. Suspending work is the
user's job, not yours — they close the laptop and the OS hibernates. The
session resumes whenever they reopen it.

The right pattern: keep going until you finish the work the user asked for,
or until you hit a *genuine* stop-line. Genuine stop-lines are:

- An irreversible / remote-effect action (push, merge, PR comment posted,
  destructive op).
- A real ambiguity where you cannot pick a defensible default and an ADR
  would be premature.
- The work the user named is actually done.

Sequencing through tasks under an active epic the user said to "continue
execute" is **not** a stop-line — keep going. The end-of-turn summary
should be a one or two sentence status, no question attached.

## Auto-activate tasks when work begins

As soon as you actually start working on a task — i.e. you are about to make
edits in service of `TASK-NNN` — invoke `/ts-task-active TASK-NNN` **before
the first such action**. Pure reading / planning does not count. Do not commit
the activation; it rides along with the first real commit for the task.

## Commits go through /commit — always

Every commit must flow through the `/commit` skill, which uses git's pathspec
form (`git commit -m "..." -- <files>`) via `scripts/commit-pathspec.sh`. The
script writes a one-shot token at `.git/pl-commit-token`; the pre-commit hook
validates it and rejects raw `git commit` invocations.

**Bypass:** `PL_COMMIT_BYPASS="<reason>"` in the env. Logged to
`.git/pl-commit-bypass.log`. Reserved for interactive rebase, recovery from a
broken `/commit` skill, and rare manual repo surgery.

**Rationale:** [`docs/developers/COMMIT_POLICY.md`](docs/developers/COMMIT_POLICY.md)
— the race-condition story, the provenance-token mechanics, the
three-check hook-failure protocol, and the bypass-review policy.

Stage and commit only the files **you** changed. If `git status` shows files
you did not touch, leave them alone unless the user explicitly says
"commit everything".

## Branch merges — squash, not fast-forward

Topic branches (epic, chore, fix, refactor) land on `main` as **one
squashed commit per branch** — never plain fast-forward, never a merge
commit. The commit subject names the branch's primary purpose
(`close EPIC-NNN: ...` for an epic, `chore(scope): ...` for a chore,
`fix(scope): ...` for a bug fix). Commits that rode along on the same
branch but aren't strictly the named work get rolled into the same
squash; the commit body enumerates them so the rollup is traceable.

Mechanic (local): from `main`, `git merge --squash <topic-tip>` stages
the change; then add the CHANGELOG bullets (see next section), and
`/commit` records it as one commit. GitHub's "Squash and merge" PR
button is the remote equivalent.

The rule applies to **every** merge to main, not just release boundaries.

## CHANGELOG updates ride with the merge

`CHANGELOG.md`'s `[Unreleased]` section must be updated **as part of
the same squash commit** that lands the work, not in a follow-up.
One bullet per closed task (with `TASK-NNN` reference) or per logical
non-task change, filed under the appropriate Keep-a-Changelog heading
(`### Added`, `### Tooling`, `### Policy`, etc.).

If you finish a branch and realise the CHANGELOG wasn't updated,
amend before merging — do not merge first and "circle back". A
CHANGELOG diff that lags behind `git log` defeats the purpose of
having a changelog.

## Project env vars — use `$PL_*`, never hard-code paths

Per-developer paths and credentials live in `.envrc` and are exposed as
`$PL_NEXAR_CLIENT_ID`, `$PL_NEXAR_CLIENT_SECRET`, `$PL_CAMERA_INDEX`,
`$PL_INVENTORY_PATH`, `$PL_PYTHON`, plus the standard `$ANTHROPIC_API_KEY`.
Reference these in commands and skills — never retype literal paths or keys
inline. Template is at [.envrc.example](.envrc.example).

## Task-system regen — use /housekeep

After any task-system file change (status edits, idea moves, epic edits),
invoke `/housekeep` rather than running `python scripts/housekeep.py --apply`
directly.

The four index files (`docs/developers/tasks/{OVERVIEW,EPICS,KANBAN}.md`,
`docs/developers/ideas/OVERVIEW.md`) are entirely generated. If they show as
modified in `git status`, sweep them into any commit — they have no per-author
authorship.

## Task-system installation

The task-system scripts (`scripts/housekeep.py`, `update_*.py`, etc.) and
skills (`.claude/skills/ts-*`) are an **installed copy** of the upstream
`awesome-task-system` package. This repo is not the package's home — edits
land here directly, and the upstream is consulted by hand if drift becomes
a problem. There is no in-repo sync mechanism.

## Skill registration

When adding a new skill (creating `.claude/skills/<name>/SKILL.md`), always
also add `<name>` to `enabled_skills` in [.vibe/config.toml](.vibe/config.toml).

## Autonomy

Autonomous epic runs follow the protocol in
[`docs/developers/AUTONOMY.md`](docs/developers/AUTONOMY.md). The
`human-in-loop:` field on every open task is the **operational
contract** for that protocol — not a decorative label. The four
values (`No`, `Clarification`, `Support`, `Main`) each map to a
defined agent behaviour, documented there.

Mid-task ambiguities resolve via the ADR-on-ambiguity rule: pick the
most defensible default, file an ADR under
[`docs/developers/adr/`](docs/developers/adr/) using
[`0000-template.md`](docs/developers/adr/0000-template.md), continue.
ADRs are reviewed in batch at the next stop-line.

Remote-effect actions (`git push`, `gh pr create`, `gh pr merge`,
`--no-verify`, `PL_COMMIT_BYPASS`) **always** require explicit
per-invocation user approval. Some are hard-denied in
`.claude/settings.json` (`git push origin main`, `git push --force`);
others go through the harness's prompt-by-default path (`gh pr create`,
`gh pr merge`) because the user sometimes wants the agent to run them.
See [`AUTONOMY.md` § No-published-effect-without-approval](docs/developers/AUTONOMY.md#no-published-effect-without-approval).
