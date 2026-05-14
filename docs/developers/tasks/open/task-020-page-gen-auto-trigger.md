---
id: TASK-020
title: Auto-trigger /inventory-page on row creation via /inventory-add
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: skill-path-today
order: 2
prerequisites: [TASK-050]
---

## Description

Land IDEA-005 Stage 3. Today `/inventory-page` is explicit: the maker
invokes it by hand. After this task, a maker-typed `/inventory-add
LM358N 5` lands a row **and** a reference page in one invocation.

**Trigger semantics — new rows only.** A qty++ on an existing row does
not re-run page-gen — the page either already exists (the maker visited
the part before) or the maker declined it once and re-prompting on
every restock would nag. New-row detection is the same signal
`/inventory-add` already computes when it decides between *insert
alphabetically* and *bump qty in place*. On a new row, the chain fires;
on a bumped row, it doesn't.

**Chain shape (skill path, synchronous).** After a new row commits:

1. `/inventory-add` invokes `enrich(part_id)` from IDEA-008 Stage 6
   synchronously. The skill blocks on the result; the maker is already
   in an LLM dialogue, so the extra wait is in the same budget as the
   WebSearch dance the skill runs today. Enrichment populates the
   row's Datasheet / Octopart / Description / Notes cells from the
   IDEA-008 response cache.
2. Chain into `/inventory-page <part-id>` in the same skill invocation.
   The page generator reuses the enriched cells verbatim — no invented
   links. On rare page-gen failure (LLM declines to write), the row
   stays committed; the row write is the load-bearing artefact,
   page-gen is convenience.

**Camera path is untouched.** That dispatch is async, lives in IDEA-008
Stage 5 / IDEA-007 Stage 5, and is out of scope here.

**Batched-add.** When `/inventory-add` accepts multiple comma-separated
`<part> <qty>` pairs, the chain runs once per new-row pair in sequence.
A page-gen failure on row N does not block rows N+1, N+2, …

**Maker override.** A `--no-page` (or equivalent prompt-time intent)
skips page-gen but still runs enrichment. Edge case for makers seeding
a row from a kit without wanting an immediate reference page. Default
behaviour: chain fires, no override needed.

`CHANGELOG.md` carries one bullet under `[Unreleased] / ### Tooling`.

## Acceptance Criteria

- [ ] `/inventory-add LM358N 5` against an empty inventory commits the
      row, runs enrichment, generates `inventory/parts/lm358n.md`, and
      re-links the row's Part cell — all in one invocation.
- [ ] `/inventory-add LM358N 3` against an inventory where the row
      already exists bumps qty in place and does **not** re-run
      enrichment or page-gen.
- [ ] Batched `/inventory-add LM358N 5, TL082CP 2` against an empty
      inventory commits two rows and produces two pages in order.
- [ ] A page-gen failure on row N of a batch does not block subsequent
      rows.
- [ ] `--no-page` skips page-gen but still runs enrichment.
- [ ] The camera path's dispatch is untouched.
- [ ] `CHANGELOG.md` carries the tooling bullet under `[Unreleased] /
      ### Tooling`.

## Test Plan

**Host tests (pytest):** mock `enrich()` and `/inventory-page`
invocation; verify chain triggers exactly when a new row is created
(insert disposition) and not on qty-bump.

## Prerequisites

- **TASK-050** — delivers the IDEA-008 enrichment orchestrator
  (`enrich(part_id)`) and the sync-invocation wiring on IDEA-008's side
  that this task is the IDEA-005 half of.
