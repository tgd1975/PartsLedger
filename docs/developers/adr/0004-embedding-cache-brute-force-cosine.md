---
id: ADR-0004
title: Embedding cache uses brute-force cosine over sqlite3 BLOBs, not sqlite-vec
status: Accepted
date: 2026-06-21
dossier-section: ../ideas/archived/idea-007-visual-recognition-dinov2-vlm.md
---

## Context

TASK-040 specified the embedding cache as "sqlite-vec backed." The
`sqlite-vec` loadable extension needs `sqlite3.Connection.enable_load_extension`,
which is compiled out of the stdlib `sqlite3` module on a large fraction
of Linux distro and Windows Python builds — so a hard dependency on it
would make `partsledger.recognition.cache` un-openable (and its whole
test suite un-runnable) on those hosts. The alternatives considered were:
(a) require the extension and fail loudly where it is unavailable;
(b) brute-force cosine similarity in numpy over vectors stored as BLOBs;
(c) ship both behind a runtime probe.

## Decision

The cache stores each 768-D vector as a little-endian `float32` BLOB in a
plain `sqlite3` table and computes nearest-neighbours by brute-force
cosine distance in numpy. There is no `sqlite-vec` dependency. IDEA-007
scopes the workflow at hobbyist size (< 10k parts); a full-table cosine
scan over ten thousand 768-D vectors is sub-millisecond, so the index an
ANN extension would buy is not yet load-bearing. The schema (BLOB column,
one row per embedding) is forward-compatible with layering a `vec0`
virtual index on top later without a data migration.

## Consequences

**Easier:**

- The module opens and its tests run on any stock Python 3.11+ with no
  loadable-extension support and no extra wheels.
- One code path, one test surface — no runtime fork between an
  extension-present and extension-absent backend.
- Persistence, idempotency, and the model-hash gate are pure SQL +
  numpy, fully unit-testable offline.

**Harder:**

- Search is O(rows) per query. If a maker's bin ever crosses the
  ~10k-part scale where this matters, an ANN index must be added — that
  revisit lands as a new ADR superseding this one.
- The "sqlite-vec backed" phrasing in the TASK-040 title is now
  aspirational rather than literal; the cache is sqlite-*backed*, vec
  search done in-process.

## See also

- IDEA-007 § *Vector DB choice* and § *Out of scope for this rollout*
  (FAISS/ANN deferred at hobbyist scale).
- TASK-040 — the cache module this decision shapes.
