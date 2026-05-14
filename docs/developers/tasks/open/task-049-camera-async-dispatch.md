---
id: TASK-049
title: Camera-path async dispatch — dispatch_async() + single-worker thread + enrichment.log
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: metadata-enrichment
order: 5
prerequisites: [TASK-043, TASK-048]
---

## Description

Wire the `enrich()` orchestrator (TASK-048) into the camera-path
recognition pipeline (TASK-043 / IDEA-007 Stage 4) as a
fire-and-forget background job (IDEA-008 Stage 5). The capture loop
never blocks on network I/O — the silent-qty++ promise from IDEA-007
stays intact.

New module `src/partsledger/enrichment/dispatch.py` exposes
`dispatch_async(part_id)`. The function submits `enrich(part_id)` to
a bounded background worker built on
`concurrent.futures.ThreadPoolExecutor(max_workers=1)`. Single worker
is enough at hobbyist cadence and rules out concurrent Nexar
requests (no rate-limit failure mode).

All outcomes (success, failure, timeout, rate-limit, offline-skip)
are logged to `inventory/.embeddings/enrichment.log` so the maker can
audit. The log is the receipt; no viewfinder verdict, no toast, no
retry storm. Empty INVENTORY.md cells are the only user-visible
signal that enrichment did not land.

The recognition pipeline hook calls `dispatch_async(part_id)` right
after the cache-learn step and then returns to *ready for next
capture* immediately — collapsing the `LEARN → NX → READY` edge from
IDEA-007's mermaid into a single non-blocking dispatch tick.

## Acceptance Criteria

- [ ] `dispatch_async(part_id)` returns control to the caller in
      < 50 ms regardless of Nexar latency.
- [ ] Enrichment completes asynchronously on the worker; the row's
      Description / Datasheet / Notes cells populate when it
      resolves.
- [ ] Every outcome (success, unknown-MPN, offline, network error,
      rate-limit) writes one line to
      `inventory/.embeddings/enrichment.log`.
- [ ] Only one enrichment runs at a time (`max_workers=1`); a burst
      of captures queues serially, never concurrently.
- [ ] Background-task exceptions never propagate to the viewfinder —
      they are caught, logged, and dropped.

## Test Plan

**Host tests (pytest)** under `tests/enrichment/test_dispatch.py`:

- Mock `enrich()` to return each `EnrichmentResult` variant; assert
  the dispatcher logs one appropriate line per outcome.
- Mock `enrich()` to raise; assert the exception is swallowed and
  logged, never re-raised on the caller's thread.
- Concurrency: submit N dispatch calls in rapid succession; assert
  they execute serially (use a barrier / event to verify
  `max_workers=1`).
- Latency: time `dispatch_async()` return against a `time.sleep`-stubbed
  `enrich()`; assert return is < 50 ms.
- Log path: assert `inventory/.embeddings/enrichment.log` is written
  in append mode and survives process restart.

**Manual integration test**: trigger a first-sighting via the camera
path; verify the viewfinder returns immediately and the row's
metadata cells populate within ~30 seconds against live Nexar
credentials.

## Prerequisites

- **TASK-043** — recognition pipeline glue exposes the post-LEARN
  hook this dispatcher attaches to.
- **TASK-048** — `enrich(part_id)` is the call the worker executes.

## Notes

- Log file: `inventory/.embeddings/enrichment.log`. Regenerable; not
  versioned.
- `concurrent.futures` is stdlib; no new runtime dep.
- Rate-limit failure surface: with `max_workers=1`, the worker holds
  the Nexar lock implicitly. If a 429 still happens (free-tier daily
  cap), one log line and quiet drop — no retry storm.
