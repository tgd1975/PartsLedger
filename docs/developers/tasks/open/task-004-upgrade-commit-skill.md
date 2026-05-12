---
id: TASK-004
title: Upgrade /commit skill and commit-pathspec.sh to the CircuitSmith versions
status: open
opened: 2026-05-12
effort: Small
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 4
prerequisites: [TASK-003]
---

## Description

Two coupled file replacements:

1. **`.claude/skills/commit/SKILL.md`** — replace with CircuitSmith's
   version. The CS skill is newer: it runs auto-fixers
   (`markdownlint-cli2 --fix`, `ruff check --fix`) scoped to the
   pathspec entries **before** invoking the wrapper, so trivial lint
   issues don't bounce off the hook. It also passes
   `--stage-untracked` to the wrapper and forbids the agent from
   typing `git add` ever (enforced by a `permissions.deny
   "Bash(git add:*)"` entry that lands in TASK-005).
2. **`scripts/commit-pathspec.sh`** — replace with CircuitSmith's
   version. PartsLedger's current wrapper rejects untracked
   pathspec entries with exit code 2 and tells the caller to
   `git add` first. CircuitSmith's wrapper additionally accepts a
   `--stage-untracked` flag that does the `git add` itself in one
   process — tighter parallel-session race window than skill-side
   staging (see CS `COMMIT_POLICY.md`).

**Substitutions** in `commit-pathspec.sh`: `cs-commit-token` →
`pl-commit-token`. No other path changes.

**Substitutions** in the SKILL.md: `cs-commit-token` →
`pl-commit-token`, `cs-commit-bypass.log` → `pl-commit-bypass.log`,
`CS_COMMIT_BYPASS` → `PL_COMMIT_BYPASS`. The skill references CS
TASK numbers (TASK-329, TASK-347, TASK-061) for historical
context — leave those references intact; they point to CS history
and are explanatory, not actionable.

## Acceptance Criteria

- [ ] `scripts/commit-pathspec.sh` accepts both `--no-verify` and
      `--stage-untracked`, in any order, before the message.
- [ ] `scripts/commit-pathspec.sh --stage-untracked "msg" new_file.md`
      commits a brand-new file without the caller running `git add`.
- [ ] `.claude/skills/commit/SKILL.md` body matches CircuitSmith's
      apart from the substitutions above.
- [ ] The skill's fixer registry table lists `*.md` →
      `markdownlint-cli2 --fix <files>` and `*.py` →
      `ruff check --fix <files>`.

## Test Plan

1. Author a fresh `.md` file with a lint violation (e.g. a trailing
      space). Run `/commit "test" path/to/new.md` — the fixer should
      strip the violation and the commit should succeed without the
      hook complaining.
2. Author a fresh `*.py` file with an unused import. Run
      `/commit "test" scripts/temp.py` — ruff fixer should remove the
      import. (Roll back the test file afterwards.)

## Notes

This task does not yet enable the `permissions.deny "Bash(git
add:*)"` entry — that lives in TASK-005. The new `/commit` skill
references the deny in its caller-anti-patterns section, but the
skill works either way; the deny is enforcement, not a runtime
contract.
