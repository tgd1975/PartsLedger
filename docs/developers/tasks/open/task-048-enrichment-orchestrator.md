---
id: TASK-048
title: Orchestrator enrich(part_id) + writer-integration (no clobber on non-empty cells)
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: metadata-enrichment
order: 4
prerequisites: [TASK-016, TASK-045, TASK-046, TASK-047]
---

## Description

Assemble TASK-045 (Nexar), TASK-046 (cache), and TASK-047 (family
fallback) behind a single `enrich(part_id)` entry point and wire its
output into the INVENTORY.md writer from TASK-016 (IDEA-008 Stage 4).

New module `src/partsledger/enrichment/__init__.py` exposes
`enrich(part_id: str) -> EnrichmentResult`. Variants: `Enriched(payload)`
and `NoEnrichment(reason)`. The reasons enumerate the four soft-fail
cases from IDEA-008's *Failure is not a gate* section: `offline`,
`network_unreachable`, `unknown_mpn`, `fallback_missed`.

Pipeline order: `cache.get(mpn)` → on miss, `nexar.lookup_mpn(mpn)` →
`cache.put(mpn, payload, lifecycle)` → on no-datasheet,
`family_datasheets.lookup_family(mpn)` → assemble result.

**Writer integration.** Extend the writer (TASK-016) to accept an
`EnrichmentResult` and fill the Description / Datasheet / Notes cells
on the INVENTORY.md row. The **idempotency rule**: the writer never
clobbers a non-empty cell. If the maker has hand-edited Description,
re-running `enrich()` leaves it alone. Only empty cells get filled.
Manufacturer name lives in the response cache, not in INVENTORY.md
as a column — page generation reads it from the cache directly.

## Acceptance Criteria

- [ ] Fresh `enrich("LM358N")` populates the row's empty Description,
      Datasheet, and Notes (package; lifecycle only if not `Active`).
- [ ] Re-running `enrich()` on a fully populated row is a no-op —
      the writer finds the cells already populated and exits clean.
- [ ] Hand-editing Description, then re-running `enrich()`, preserves
      the hand-edit (no clobber).
- [ ] `$PL_NEXAR_CLIENT_ID` unset → `NoEnrichment(reason='offline')`
      and zero MD writes.
- [ ] Forced Nexar miss + family-table miss →
      `NoEnrichment(reason='fallback_missed')`; the row is left
      untouched but the attempt is logged.
- [ ] Cache-miss path exercises Nexar then the family fallback in
      order, then writes the result.

## Test Plan

**Host tests (pytest)** under `tests/enrichment/test_orchestrator.py`:

- Mock Nexar transport (TASK-045) and the family-fallback module
  (TASK-047). Use a temp-dir cache (TASK-046) and a temp INVENTORY.md
  fixture (TASK-016).
- Cover each soft-fail reason: `offline` (env unset),
  `network_unreachable` (mock raises connection error),
  `unknown_mpn` (Nexar returns `None`, family lookup returns `None`),
  `fallback_missed` (Nexar returns part without datasheet, family
  lookup returns `None`).
- No-clobber: pre-populate Description; assert it survives
  re-enrichment.
- Pipeline ordering: assert cache is consulted first, then Nexar,
  then family fallback.

**Manual integration test** against live Nexar credentials: one
end-to-end `enrich("LM358N")` against a fresh inventory row,
verifying the cells land and re-running is a no-op.

## Prerequisites

- **TASK-016** — INVENTORY.md writer module that this orchestrator
  invokes to fill cells.
- **TASK-045** — Nexar GraphQL adapter (`lookup_mpn`).
- **TASK-046** — SQLite response cache (`get` / `put`).
- **TASK-047** — Family-datasheet fallback (`lookup_family`).

## Notes

- Manufacturer name lives in the response cache only — never written
  to INVENTORY.md as a column. Page generation (TASK-050 and
  IDEA-005) reads it from the cache.
- The orchestrator does not retry on transient network errors — that
  layer belongs to the dispatcher (TASK-049).
