---
id: TASK-031
title: Write README.md / QUICKSTART.md bootstrap section
status: closed
opened: 2026-05-14
closed: 2026-05-14
effort: Medium (2-8h)
effort_actual: Medium (2-8h)
complexity: Medium
human-in-loop: No
epic: project-setup
order: 10
prerequisites: [TASK-022, TASK-024]
---

## Description

Write the fresh-clone-to-first-part bootstrap walk-through so a new
contributor (or the maintainer on a new machine) can stand the system
up end-to-end without asking questions.

Per IDEA-012 Gap 5 (folded into EPIC-004 per the implementation plan):
PartsLedger's current `README.md` is the vision document, not the
operations manual. Phase 0b is where the operations manual gets
written, because it's the first moment the entire stack — package
layout, release tooling, CI, lockfile — is real enough to walk
through.

Coverage, in order:

1. **Install** — clone, `direnv allow` (or manual `.envrc` source),
   `uv venv && uv sync` (after TASK-025 lands the lockfile) or
   `uv pip install -e .[dev]` (fallback).
2. **`.envrc`** — copy `.envrc.example` to `.envrc`, fill in
   `PL_NEXAR_CLIENT_ID`, `PL_NEXAR_CLIENT_SECRET`, `ANTHROPIC_API_KEY`,
   `PL_CAMERA_INDEX`, `PL_INVENTORY_PATH`. Reference the existing
   `.envrc.example` rather than re-listing variables here.
3. **First capture** — placeholder pointer to EPIC-005's camera
   capture entry point (the bootstrap doc references the
   `partsledger capture` command; until EPIC-005 lands, the section
   notes "Phase 1+" and tells the user the camera path is
   forthcoming).
4. **First `/inventory-add` walk-through** — concrete: a Maker drops
   an LM358N in the bin, invokes `/inventory-add LM358N 5`, sees the
   row appear under `## ICs` with `Source: manual`, sees the new
   `inventory/parts/lm358n.md` linked from the table.

Output shape: split or single file based on length. If the bootstrap
section fits in ~80 lines of markdown, fold it into `README.md` under
a `## Quickstart` heading. If it grows past that, split into a
dedicated `QUICKSTART.md` at the repo root and reference it from
`README.md`. Pick at write-time, not now.

A `partsledger doctor` command (health-check on the install) is
**deferred** unless the doc proves insufficient — i.e. unless a real
contributor follows it and gets stuck somewhere a doctor command
would have unblocked. The doc-first approach matches the maker-UX
principle (no tech internals exposed by default).

## Acceptance Criteria

- [x] A fresh-clone bootstrap walk-through exists at `README.md`
      (Quickstart section) or `QUICKSTART.md`, covering install,
      `.envrc`, first capture, first `/inventory-add`.
- [x] The walk-through references concrete commands, not abstractions
      (`uv sync`, `/inventory-add LM358N 5`, not "install
      dependencies" / "add a part").
- [x] A contributor who has never seen the repo can follow the doc
      from clone to first inventory row without external help —
      validated by the maintainer reading the final version with
      fresh eyes.
- [x] The walk-through links to (and does not duplicate)
      `.envrc.example`, `RELEASING.md`, and the relevant skill specs.
- [x] CHANGELOG bullet under `[Unreleased] / ### Added` records the
      bootstrap docs.

## Test Plan

No automated tests required — change is documentation. Validation:
maintainer self-bootstrap on a throwaway clone on the second platform
(Windows if written on Ubuntu, or vice versa); any step that
required improvisation is a doc bug, not a user bug.

## Prerequisites

- **TASK-022** — delivers the package layout `pip install -e .`
  resolves against; the install step in the bootstrap doc references
  it.
- **TASK-024** — delivers CI workflows. The bootstrap doc points
  contributors at CI as the source of truth for "what gets validated
  on a PR", so the workflows need to exist before the doc references
  them.

## Notes

Defer `partsledger doctor` per the IDEA-012 Gap 5 plan-resolution.
The deferral is a real bet: if the first external contributor (or
the maintainer on a new machine) gets stuck, write the doctor command
in a follow-up task at that point, not now.

This is the **last** EPIC-004 task by `order:`. Closing it closes
Phase 0b and unblocks EPICs 005, 006, 007, 008 in parallel.
