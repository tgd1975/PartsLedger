---
id: TASK-050
title: Skill-path sync enrichment + page-gen chain (sync for /inventory-add, async for camera)
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: metadata-enrichment
order: 6
prerequisites: [TASK-048, TASK-049]
---

## Description

Wire `enrich()` to the synchronous skill path and chain page
generation per IDEA-008's closed *Page-generation trigger* question
(IDEA-008 Stage 6).

**Skill path (sync).** After `/inventory-add` writes a new row, the
skill calls `enrich(part_id)` **synchronously**. The maker is already
interactive — one extra Nexar round-trip (~300 ms) is fine. When
`enrich()` returns, the skill chains into `/inventory-page <part-id>`
synchronously, which lands the per-part reference page using the
just-enriched metadata (datasheet URL + description + package from
INVENTORY.md, manufacturer from the response cache populated by
TASK-046). Page-gen mechanics themselves are owned by IDEA-005's
matching auto-trigger stage (TASK-020).

**Camera path (async).** Once `dispatch_async()` (TASK-049) resolves
and `enrich()` returns `Enriched(...)`, the dispatcher queues a
page-gen job in the same background worker. The page-gen worker
reads INVENTORY.md + the response cache, generates the page, writes
it. No viewfinder feedback.

**Qty-bump path (skill).** `/inventory-add LM358N 1` against an
existing row is a qty bump only — no re-enrichment, no page-gen.
The enrichment and page already landed on first sighting.

## Acceptance Criteria

- [ ] `/inventory-add LM358N 1` against an empty inventory: row
      lands, `enrich()` runs synchronously, `/inventory-page` runs
      synchronously, `inventory/parts/lm358n.md` exists with content
      sourced from the Nexar-supplied datasheet.
- [ ] `/inventory-add LM358N 1` against an existing row: qty cell
      increments only — no re-enrichment, no page-gen.
- [ ] Camera-path first-sighting: row lands silently with `qty: 1`,
      viewfinder returns to *ready* immediately, page appears in
      `inventory/parts/` within the worker's natural latency
      (~10–30 s LLM page-gen).
- [ ] Camera-path repeat sighting: silent `qty++`, no enrichment,
      no page-gen.
- [ ] Page-gen is skipped when `inventory/parts/<part-id>.md`
      already exists (idempotent chain).

## Test Plan

**Host tests (pytest)** under `tests/enrichment/test_chain.py`:

- Mock Nexar transport, the page-gen skill invocation, and the
  writer. Cover: skill-path first-sighting (row + enrich + page-gen
  all fire), skill-path qty-bump (only writer fires), camera-path
  first-sighting (dispatch + enrich + page-gen all fire async),
  camera-path repeat (only writer fires).
- Idempotency: pre-create `inventory/parts/lm358n.md`; assert the
  chain does not regenerate it.

**Manual integration test** against live Nexar credentials:
end-to-end `/inventory-add LM358N 1` from an empty inventory; verify
the row lands, the page is generated, and the second
`/inventory-add LM358N 1` is a quiet qty bump.

## Prerequisites

- **TASK-048** — `enrich(part_id)` is the synchronous call the skill
  makes.
- **TASK-049** — async dispatcher is the camera-path equivalent and
  also owns the page-gen queueing on the worker.

## Notes

- Page-gen skill internals are out of scope here — owned by
  IDEA-005's auto-trigger stage (TASK-020). This task delivers only
  the dispatch glue (the `/inventory-page <part-id>` invocation).
- The skill-path chain runs inside the user's interactive turn —
  long-running LLM page-gen latency is acceptable; the maker is
  watching.
