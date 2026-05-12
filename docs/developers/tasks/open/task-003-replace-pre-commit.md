---
id: TASK-003
title: Replace scripts/pre-commit with the CircuitSmith version
status: open
opened: 2026-05-12
effort: Small
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 3
prerequisites: [TASK-002]
---

## Description

Replace `scripts/pre-commit` with CircuitSmith's version. The CS file
already contains everything PartsLedger needs:

- Commit-provenance check (validates the one-shot token written by
  `commit-pathspec.sh`).
- Mandatory markdownlint (fails the commit if `markdownlint-cli2` is
  missing — no silent skip).
- Mandatory ruff (fails the commit if `ruff` is missing; lints only
  staged `*.py` files; adopts the registry under TASK-061 in CS).

PartsLedger's current pre-commit has a softer (optional)
markdownlint block, no ruff block, and a `sync_task_system.py
--check` block that is now obsolete (TASK-001 deleted the script).

**Substitutions** (sed-able):

- `CS_COMMIT_BYPASS` → `PL_COMMIT_BYPASS`
- `cs-commit-token` → `pl-commit-token`
- `cs-commit-bypass.log` → `pl-commit-bypass.log`

**Drop** the portability-lint block (`scripts/portability_lint.py` is
camel-vs-giraffe — PartsLedger has no skill-extraction plan that
needs it).

No surgical merging with PartsLedger's current pre-commit — full
file replacement. The portability and ruff cleanup landed in
TASK-002 already, so the first commit after this lands does not
bounce on a ruff finding.

## Acceptance Criteria

- [ ] `scripts/pre-commit` is byte-identical to CircuitSmith's apart
      from the three name substitutions above and the dropped
      portability-lint block.
- [ ] A `/commit` of a `.md`-only change succeeds: markdownlint
      mandatory block fires, ruff block is skipped (no `.py` staged).
- [ ] A `/commit` of a `.py`-only change succeeds: ruff block fires,
      markdownlint block is skipped.
- [ ] Removing `markdownlint-cli2` from `$PATH` causes the next
      `.md` commit to fail with the install instruction in the hook
      output (do not actually commit the missing-tool state — test
      and restore).
- [ ] Same for `ruff`.

## Test Plan

Run a paragraph-of-Markdown commit and a one-line scripts/*.py commit
through `/commit` and confirm the right block fires in each case.

## Notes

The token format is identical between projects — only the file path
inside `.git/` changes (`cs-commit-token` → `pl-commit-token`). The
`commit-pathspec.sh` wrapper writes the token; TASK-004 replaces that
wrapper. The pre-commit and the wrapper must agree on the token path;
TASK-003 and TASK-004 land back-to-back to keep them in sync.
