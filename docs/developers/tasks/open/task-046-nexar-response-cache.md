---
id: TASK-046
title: Implement src/partsledger/enrichment/cache.py — SQLite per-MPN response cache
status: open
opened: 2026-05-14
effort: Small (<2h)
complexity: Medium
human-in-loop: No
epic: metadata-enrichment
order: 2
prerequisites: [TASK-045]
---

## Description

Wrap the Nexar transport from TASK-045 in a per-MPN SQLite cache so
repeat enrichment of the same part is instant and survives process
restart (IDEA-008 Stage 2). New module
`src/partsledger/enrichment/cache.py` opens / creates
`inventory/.embeddings/nexar_cache.sqlite` with schema
`(mpn TEXT PRIMARY KEY, payload_json TEXT, lifecycle TEXT,
cached_at INTEGER)`.

API surface: `get(mpn) -> dict | None`, `put(mpn, payload, lifecycle)`,
`expire_stale()`. TTL policy from IDEA-008's *Cache policy* section:
30 days for `Active` parts, **never** for `Obsolete` / `NRND` (their
metadata is frozen). `expire_stale()` is the only deletion path —
never bulk-clear. The cache is regenerable from MD + live Nexar
re-fetches, same ethos as the embedding cache.

`NexarPart` payloads are serialised via `dataclasses.asdict` +
`json.dumps`; no schema migration concern.

## Acceptance Criteria

- [ ] `put(mpn, payload, lifecycle)` followed by `get(mpn)` round-trips
      the payload byte-identical.
- [ ] `get(mpn)` for an `Active` row whose `cached_at` is older than
      30 days returns `None`; the next caller refetches from Nexar.
- [ ] `get(mpn)` for an `Obsolete` row from any past date still returns
      the cached payload (never expires).
- [ ] Cache file survives process restart and a fresh module import.
- [ ] `expire_stale()` removes only `Active` rows past TTL; `Obsolete`
      and `NRND` rows are untouched.

## Test Plan

**Host tests (pytest)** under `tests/enrichment/test_cache.py`:

- Round-trip put/get with a synthetic `NexarPart`-shaped payload.
- TTL behaviour: manipulate `cached_at` to simulate ages of 1 day,
  29 days, 31 days for an `Active` row; assert get-returns-cached vs
  get-returns-None.
- `Obsolete` and `NRND` rows: insert with a `cached_at` 365 days in
  the past, assert `get` still returns the payload.
- Persistence: write a row, close the DB, reopen, assert `get`
  returns the row.
- `expire_stale()`: insert mixed Active/Obsolete rows, run, assert
  only stale Active rows were removed.

No live Nexar integration is needed — the cache is pure stdlib
`sqlite3`.

## Prerequisites

- **TASK-045** — provides the `NexarPart` dataclass shape that this
  cache serialises.

## Notes

- Cache file path: `inventory/.embeddings/nexar_cache.sqlite`. The
  `.embeddings/` directory is already regenerable per CLAUDE.md.
- `sqlite3` is stdlib; no new runtime dep.
