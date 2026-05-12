# Project: PartsLedger

> *PartsLedger keeps the record. [CircuitSmith](../CircuitSmith/) reads it before forging.*

PartsLedger is an LLM-native inventory for an electronics parts bin: USB camera
captures a part, the pipeline (DINOv2 embeddings → Claude Opus 4.7 Vision →
Nexar/Octopart) identifies it, and the result lands in
`inventory/parts/<part>.md`. See [`concept.md`](concept.md) for the full design.

## OS context

This project is developed on both **Windows 11** and **Ubuntu**. At the start
of every session, check the platform from the system environment info (or run
`uname -s`) and apply the correct shell syntax. Run `/os-context` if in doubt.

## Missing executables

When a CLI tool or Python package is not found (e.g. `markdownlint`, `torch`,
`cv2`, `sqlite_vec`):

1. Try once with the most obvious alternative (`pip`, `npx`, full path).
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
CircuitSmith component-profile format (see [`concept.md`](concept.md#example-partsic-lm358nmd)).

## Human interaction — batch questions, don't loop

If N questions can be asked simultaneously, ask all N at once. Only use a
sequential loop when each answer genuinely depends on the previous one.

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

Stage and commit only the files **you** changed. If `git status` shows files
you did not touch, leave them alone unless the user explicitly says
"commit everything".

## Project env vars — use `$PL_*`, never hard-code paths

Per-developer paths and credentials live in `.envrc` and are exposed as
`$PL_NEXAR_CLIENT_ID`, `$PL_NEXAR_CLIENT_SECRET`, `$PL_CAMERA_INDEX`,
`$PL_INVENTORY_PATH`, `$PL_PYTHON`, plus the standard `$ANTHROPIC_API_KEY`.
Reference these in commands and skills — never retype literal paths or keys
inline. Template is at [.envrc.example](.envrc.example).

## Task-system regen — use /housekeep

After any task-system file change (status edits, idea moves, epic edits),
invoke `/housekeep` rather than running `python scripts/housekeep.py --apply`
directly. The pre-commit hook also runs `sync_task_system.py --check` as a
backstop against `awesome-task-system/` ↔ live divergence.

The four index files (`docs/developers/tasks/{OVERVIEW,EPICS,KANBAN}.md`,
`docs/developers/ideas/OVERVIEW.md`) are entirely generated. If they show as
modified in `git status`, sweep them into any commit — they have no per-author
authorship.

## Task-system source-of-truth

`awesome-task-system/` is the **canonical source** for the task-system scripts,
skills, config, and tests. The live copies under `scripts/`, `.claude/skills/`,
and `docs/developers/task-system.yaml` are generated artefacts.

**Workflow when changing any task-system file:**

1. Edit the package copy under `awesome-task-system/` — never edit the live copy.
2. Run `python scripts/sync_task_system.py --apply` to copy package → live.
3. Stage and commit both sides together.

The pre-commit hook calls `sync_task_system.py --check` and rejects any commit
where the two sides diverge.

## Skill registration

When adding a new skill (creating `.claude/skills/<name>/SKILL.md`), always
also add `<name>` to `enabled_skills` in [.vibe/config.toml](.vibe/config.toml).
