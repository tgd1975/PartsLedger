---
id: EPIC-001
name: align-with-circuitsmith
title: Align with CircuitSmith framework
status: open
opened: 2026-05-12
closed:
assigned:
branch: feature/align-with-circuitsmith
---

Seeded by IDEA-002 (Align PartsLedger with CircuitSmith framework).

Transfer CircuitSmith's project framework — commit policy with provenance
token, mandatory ruff + markdownlint pre-commit gates, developer-docs
framework (13 verbatim docs + ADR practice + fresh PartsLedger
`ARCHITECTURE.md`), security-review hooks for pulls/merges/rebases,
codeowner reminder system, autonomous-epic-run skill + `AUTONOMY.md`,
GitHub Actions CI matrix, and server-side branch protection — to
PartsLedger.

**Directive (from IDEA-002):** CircuitSmith is the law. Transfer
everything except content that is literally about CircuitSmith's domain
(schematics, ERC, NetGraph, skill-extraction) and has no PartsLedger
analogue. For those, keep the *mechanism* and skip the *contents*.

The epic lands as 13 tasks. Eleven are mechanical ports / name-
substitutions; two are design work (`ARCHITECTURE.md` for PartsLedger's
pipeline, and the starter `co-*` skills capturing PartsLedger-specific
invariants). One task (apply server-side branch protection) is
`human-in-loop: Main` because it is a remote-effect action on
github.com.

Three preparatory deletions land first via TASK-001:
`awesome-task-system/`, `scripts/sync_task_system.py`. PartsLedger drops
its in-repo sync model to match CircuitSmith's installed-copy
approach. The PartsLedger-specific `## Task-system source-of-truth`
section in `CLAUDE.md` is replaced by CircuitSmith's `## Task-system
installation` section under TASK-011 (the `CLAUDE.md` rewrite).

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
