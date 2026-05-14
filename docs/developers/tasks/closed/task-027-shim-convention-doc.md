---
id: TASK-027
title: Document shim convention (scripts/ and skill .py files as thin shims)
status: closed
opened: 2026-05-14
closed: 2026-05-14
effort: Small (<2h)
effort_actual: Small (<2h)
complexity: Medium
human-in-loop: No
epic: project-setup
order: 6
prerequisites: [TASK-022]
---

## Description

Write the project-wide shim convention down so every future Python
task lands code in the right place by default, not after a review
round-trip.

Per IDEA-014 § What to port — fourth bullet (broadened to cover
`scripts/` as well as `.claude/skills/`): all Python product code
lives in `src/partsledger/<module>/`. Files under `scripts/*.py` and
`.claude/skills/*/*.py` are **thin shims** — argparse (or click)
plus a single call into `partsledger.*`. Module-deep logic never
lives at either location.

Rationale:

- Skill `.py` files inside `.claude/skills/` are not packaged with
  the wheel — putting logic there means the published distribution
  is missing functionality the agent uses.
- `scripts/*.py` files are runnable from a developer checkout but
  also not part of the wheel — same problem.
- Keeping both as thin shims gives one canonical implementation
  (in-package), one canonical test surface (`tests/test_<module>.py`),
  and one canonical place to look when behaviour changes.

The convention is recorded in [`CLAUDE.md`](../../../../CLAUDE.md)
(it is project-wide policy, not a per-skill detail), and a reference
shim is checked in alongside it so reviewers have something concrete
to point at. Candidate reference shim: TASK-026's
`scripts/portability_lint.py` if that task has landed; otherwise a
minimal `scripts/_shim_example.py` that calls into a trivial
`partsledger._dev` helper.

## Acceptance Criteria

- [x] [`CLAUDE.md`](../../../../CLAUDE.md) carries a `## Shim convention`
      section (or equivalent) stating the rule.
- [x] The section references at least one concrete shim in the tree
      as a worked example.
- [x] The section calls out both `scripts/*.py` *and*
      `.claude/skills/*/*.py` — not just one of the two.
- [x] The shim convention is also referenced from the EPIC-004 epic
      file (`docs/developers/tasks/open/epic-004-project-setup.md`),
      which already mentions it; cross-link to CLAUDE.md.

## Test Plan

No automated tests required — change is documentation. Validation:
read the new section, confirm it answers "where does new Python code
go?" without ambiguity.

## Prerequisites

- **TASK-022** — delivers `src/partsledger/`, the destination the
  convention points to. Documenting the convention before the
  destination exists would be premature.

## Notes

CircuitSmith captured the equivalent convention as part of ADR-0012
(library as installable package). PartsLedger captures the layout
decision in TASK-030's ADR-0001 and the shim convention here in
CLAUDE.md — same rule, split across two artefacts because the ADR
records the *decision* once and CLAUDE.md is where the rule needs to
be visible every session.
