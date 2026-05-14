---
id: TASK-028
title: Drift audit on already-copied scripts/ files vs CircuitSmith
status: closed
opened: 2026-05-14
closed: 2026-05-14
effort: Medium (2-8h)
effort_actual: Medium (2-8h)
complexity: Senior
human-in-loop: Clarification
epic: project-setup
order: 7
prerequisites: [TASK-022]
---

## Description

Audit every Python file under `scripts/` that originated as a port
from CircuitSmith and decide, per file, whether to pull CircuitSmith's
newer version, keep PartsLedger's local copy, or merge the two.

Per IDEA-014 § Open questions — drift audit on shared scripts. The
overlap is substantial: per IDEA-014 § What probably doesn't port —
last paragraph, the in-scope set is at least `commit-pathspec.sh`,
`housekeep.py`, `release_burnup.py`, `release_snapshot.py`,
`security_review_changes.py`, `task_system_config.py`,
`update_idea_overview.py`, `update_task_overview.py`,
`update_scripts_readme.py`, `codeowner_hook.py`, `pre-commit` (the
hook itself), and `install_git_hooks.sh`. Walk every Python file under
`scripts/` (and the `.sh` files that are part of the same shared
plumbing); compare each against its CircuitSmith counterpart at
`../CircuitSmith/scripts/<same-name>`.

Per-file decision matrix:

- **pull-from-upstream** — PartsLedger's copy is strictly older with
  no local divergence; replace it.
- **keep-local** — PartsLedger has diverged for a project-specific
  reason (e.g. a CircuitSmith-only step that doesn't apply); record
  the divergence rationale so future audits don't re-litigate it.
- **merge** — both repos have diverged; merge the changes, picking
  the right behaviour case by case.

Output: a written audit note. Two acceptable shapes — `scripts/DRIFT_AUDIT.md`
(table form, one row per file) or an ADR at `docs/developers/adr/0002-scripts-drift-audit.md`
recording the audit + the per-file decisions in one place. Pick the
ADR form if the audit ends up encoding cross-cutting policy
(e.g. "PartsLedger's `housekeep.py` keeps its inventory-overview
generation step that CircuitSmith doesn't have"); pick the
`DRIFT_AUDIT.md` form if it's a pure per-file table.

The drift is then resolved per classification in the same commit (or
a sequenced follow-up if the diff is large enough to warrant one).

## Acceptance Criteria

- [x] Every Python file under `scripts/` (plus shared `.sh` plumbing)
      is enumerated in the audit output.
- [x] Each file has a decision (`pull-from-upstream`, `keep-local`,
      `merge`) plus a one-line rationale.
- [x] Drift is resolved per classification — pulled files replaced,
      kept files annotated, merged files updated.
- [x] CHANGELOG bullet under `[Unreleased] / ### Tooling` names the
      audit and references this task.

## Test Plan

Host tests (pytest) — indirect: after the drift is resolved,
`pytest` and the pre-commit hook still pass on a clean tree, and
`scripts/housekeep.py --apply` still rolls the index files
identically (no functional regression).

## Prerequisites

- **TASK-022** — delivers the package layout. Some `scripts/` shims
  may move into `src/partsledger/_dev/` as part of the merge
  decisions; that move depends on the package existing.

## Notes

This task is `human-in-loop: Clarification` because the per-file
decisions for `housekeep.py`, `pre-commit`, and `task_system_config.py`
are likely to surface places where PartsLedger and CircuitSmith have
intentionally diverged. Surface the candidate decision per file and
ask the maintainer before resolving.

CircuitSmith's domain-specific scripts (`check_circuit_schema.py`,
`check_erc_reports.py`, `regenerate_circuit_artefacts.py`, etc., per
IDEA-014 § What probably doesn't port) are explicitly **out of
scope** — do not stage them for porting during the audit.
