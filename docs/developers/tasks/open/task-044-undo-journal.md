---
id: TASK-044
title: Undo journal at inventory/.embeddings/undo.toml, depth 1
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: visual-recognition
order: 6
prerequisites: [TASK-043]
---

## Description

IDEA-007 Stage 5 — disk-persistent single-step undo. Reverses the last
qty++ **and** its cache row in one atomic transaction so a wrong silent
write never poisons the cache for future captures in the same
neighbourhood.

New module `src/partsledger/recognition/undo.py` manages
`inventory/.embeddings/undo.toml`. Depth-1 by default (configurable in
`[recognition]` per IDEA-007 § Configuration files). After each
successful pipeline write, the journal records:

```toml
[[entries]]
action      = "write"
part_id     = "lm358n"
qty_before  = 3
qty_after   = 4
cache_row_id = 1287
timestamp   = "2026-05-14T16:23:11Z"
```

`undo_last()` reverses the most recent entry: decrement qty in the part
MD (via the TASK-016 writer), delete the cache row (via
`cache.delete_last_inserted()` or by row id), then remove the journal
entry. Atomic from the maker's perspective per IDEA-007 § Three pipeline
microdecisions — the viewfinder either shows *"reverted"* or *"undo
failed"*, never a partial state. A failed MD decrement leaves the cache
row and journal entry untouched for a later retry.

Viewfinder `U`-keypress dispatch is owned by IDEA-006; this task only
delivers the `undo_last()` handler. The hand-off contract: IDEA-006
calls `undo.undo_last() -> UndoOutcome` and renders the result.

## Acceptance Criteria

- [ ] After a tight cache hit, `undo_last()` decrements qty in the part MD **and** deletes the just-inserted cache row.
- [ ] After a VLM hit, same behaviour (no source-dependent code-path divergence).
- [ ] Calling `undo_last()` twice in a row only reverses one write — depth-1 default.
- [ ] Journal persists across process restart: write in session A, close, open session B, `undo_last()` reverses correctly.
- [ ] Calling `undo_last()` on an empty journal returns a clean *"nothing to undo"* outcome, no exception.
- [ ] A simulated MD-writer failure during undo leaves the cache row intact and the journal entry in place for retry — never half-undone.

## Test Plan

**Host tests** (pytest):

- Add `tests/recognition/test_undo.py`.
- Cover: round-trip undo after tight cache hit (mocked); after VLM hit
  (mocked); depth-1 (second undo no-ops cleanly); persistence across a
  simulated process restart (close + reopen the TOML); empty-journal
  case; writer-failure leaves a recoverable state.

## Prerequisites

- **TASK-043** — pipeline writes are what get journalled; undo consumes
  the same writer / cache primitives the pipeline drove.

## Notes

Depth > 1 is explicit polish per IDEA-007 § Three pipeline microdecisions
("Single step only; longer history is a polish, not a primitive") and not
in this task's scope. The journal schema leaves room for future depth
without breaking format.
