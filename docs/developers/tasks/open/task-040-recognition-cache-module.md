---
id: TASK-040
title: Implement src/partsledger/recognition/cache.py — sqlite-vec backed
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: visual-recognition
order: 2
prerequisites: [TASK-039]
---

## Description

The *cache* half of IDEA-007 Stage 1. Wraps `sqlite-vec` for the
embedding store that backs the similarity search at the heart of the
recognition pipeline.

New module `src/partsledger/recognition/cache.py` opens or creates
`inventory/.embeddings/vectors.sqlite`, loads the `sqlite-vec` extension,
and exposes:

- `insert(vector, label, marking_text, image_hash) -> row_id` — idempotent
  on `image_hash`; a second insert for the same hash returns the existing
  row id rather than appending a duplicate.
- `nearest(vector, k=3) -> list[(row_id, label, marking_text, distance)]` —
  cosine distance against the stored 768-D vectors.
- `delete_last_inserted() -> bool` — pops the most recently inserted row;
  used by the undo journal (TASK-044).
- `clear_if_hash_mismatch(model_hash)` — the rebuild-on-mismatch gate per
  IDEA-007 closed-Q *Cache rebuild policy*.

A `meta` table stores the backbone identity (`dinov2_vits14#sha256:<hex>`,
sourced from `embed.MODEL_HASH`). On open, if the stored hash differs from
the running backbone's hash, the cache is treated as empty for new
captures and `nearest()` refuses queries with a clear error — the file
itself is not deleted (the maker can inspect before-vs-after).

Storage location is fixed at `inventory/.embeddings/vectors.sqlite` per
IDEA-004 § directory layout. The directory is created on first use.

## Acceptance Criteria

- [ ] `nearest(vec, k=N)` returns up to N rows sorted by ascending cosine distance.
- [ ] `insert()` is idempotent on `image_hash`: the same hash inserted twice yields one row.
- [ ] `delete_last_inserted()` removes only the most recent row and returns `True`; returns `False` on an empty cache.
- [ ] Opening a cache whose stored `MODEL_HASH` differs from `embed.MODEL_HASH` refuses `nearest()` queries until the cache is cleared.
- [ ] The cache file survives process restart; embeddings written in process A are queryable in process B.

## Test Plan

**Host tests** (pytest):

- Add `tests/recognition/test_cache.py`.
- Use an isolated tmp-path cache file per test (parametrise the storage
  path, default to `inventory/.embeddings/vectors.sqlite`).
- Cover: insert + nearest round-trip; idempotency on `image_hash`;
  `delete_last_inserted()` on populated and empty caches; the
  model-hash-mismatch refusal path; persistence across re-open.

## Prerequisites

- **TASK-039** — provides the 768-D vector contract and `MODEL_HASH`
  constant the cache pins in its meta table.

## Notes

`sqlite-vec` is the chosen vector DB per IDEA-007 closed-Q *Vector DB
choice*. FAISS is explicitly out of scope at hobbyist scale (< 10k parts).
Concurrency / WAL is out of scope for the single-bench workflow (IDEA-007
*Out of scope for this rollout*).
