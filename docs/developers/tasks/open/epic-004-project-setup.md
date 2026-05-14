---
id: EPIC-004
name: project-setup
title: Project setup — port from CircuitSmith
status: open
opened: 2026-05-14
closed:
assigned:
branch: feature/project-setup
---

Seeded by IDEA-014 (Project setup review vs CircuitSmith) and IDEA-012
(Integration pass — Gap 5 on bootstrap docs).

The cross-cutting **Phase 0b** prerequisite for every Phase 1+
camera-path module — `src/partsledger/` layout, release pipeline,
CI/release workflows, lockfile, portability lint, shim convention,
drift audit, optional-dependencies extras, ADR-0001 recording the
library-as-package move, and the README/QUICKSTART bootstrap section.

Project-wide convention applied throughout: Python code lives in
`src/partsledger/<module>/`; `scripts/*.py` and `.claude/skills/*/*.py`
files are thin shims (argparse + one call into `partsledger.*`). Every
Python task in later epics follows this rule once it lands here.

EPIC-004 is a hard prerequisite for every task in EPICs 005, 006, 007,
and 008. No module is importable as `partsledger.*` until the package
layout ships.

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
