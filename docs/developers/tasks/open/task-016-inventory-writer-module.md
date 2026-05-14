---
id: TASK-016
title: Implement src/partsledger/inventory/writer.py with upsert_row() contract
status: open
opened: 2026-05-14
effort: Large (8-24h)
complexity: Senior
human-in-loop: No
epic: markdown-inventory-schema
order: 3
prerequisites: [TASK-014, TASK-022]
---

## Description

Implement the single `INVENTORY.md` writer that three downstream call-sites
will share: `/inventory-add` (skill path), the camera-path pipeline
(IDEA-007 Stage 4 silent qty++ / new-row insert), and the enrichment
integrator (IDEA-008 Stage 4 cell extension). The contract is pinned in
IDEA-004 § `INVENTORY.md` writer contract — this task implements it
verbatim.

**Signature.** Per IDEA-004:

```python
def upsert_row(
    part_id: str,
    qty_delta: int,
    *,
    source: str,
    section: str | None = None,
    cells: dict[str, str] | None = None,
) -> WriteResult: ...
```

`WriteResult` carries the disposition (`inserted`, `bumped`,
`metadata_updated`, `no_op`), the post-write qty, and the section the row
landed in.

**Idempotency.** Keyed by `part_id`. Calling twice with the same args
produces the same end state, except `qty_delta` accumulates by design.
No de-dup on camera-frame identity — the undo journal handles that.

**Atomicity.** One call → one file write. Read `INVENTORY.md`, mutate the
in-memory representation, re-pad the affected table per markdownlint
MD060, write the whole file back via the atomic-rename pattern (temp file
in the same directory, `os.replace`). A crash mid-write leaves the file
in either the pre-call or post-call state, never half-written.

**Pre-flush invariant check.** Before flushing, the writer runs the same
lint pass that `scripts/lint_inventory.py` (TASK-017) runs as a
pre-commit hook. A failure raises rather than writes a malformed file.
This is what makes the writer safe from code paths with no Claude
codeowner skill in the loop.

**Error contract.** Raises on:

- malformed pre-state (`INVENTORY.md` doesn't parse) — caller sees the
  parse error with a line number; no auto-repair;
- section unresolvable (`section=None` and no H2 headings yet, or
  `section="Foo"` but no `## Foo`);
- source-shape violation (empty, whitespace, mixed-case);
- lint failure on the post-state (pre-flush check rejected the mutated
  representation; diagnostic included).

Does **not** raise on negative final qty, unknown section that has a
matching H2, or extra keys in `cells` (silently ignored, forward-compat).

**Single implementation, three callers.** The two skills
(`/inventory-add`, the camera-path writer hook) and the enrichment
integrator (`enrich()` in IDEA-008 Stage 4) all import this module. No
lookalike. If a caller's needs grow beyond `upsert_row`, the writer
module grows a sibling function; the existing signature stays stable.

Module location: `src/partsledger/inventory/writer.py` (under the
package layout TASK-022 lands).

## Acceptance Criteria

- [ ] `src/partsledger/inventory/writer.py` exists with the exact
      `upsert_row` signature from IDEA-004 (positional `part_id`,
      `qty_delta`; keyword-only `source`, `section`, `cells`).
- [ ] `WriteResult` exposes `disposition`, post-write `qty`, and
      `section`.
- [ ] All file writes use the atomic-rename pattern (temp file +
      `os.replace`); a simulated crash mid-write leaves the file in a
      consistent pre- or post-call state.
- [ ] Pre-flush calls into `partsledger.inventory.lint` (TASK-017) and
      raises with the lint diagnostic on failure.
- [ ] Raises the four documented errors (malformed pre-state, section
      unresolvable, source-shape violation, lint failure on post-state).
- [ ] Idempotent on `part_id` for same-args calls (except `qty_delta`
      accumulates).
- [ ] Extra keys in `cells` are silently ignored.

## Test Plan

**Host tests (pytest):** `tests/unit/test_writer.py` — cover
insert/bump/metadata_updated/no_op dispositions, atomic-rename behavior
on simulated crash, pre-flush lint integration, error raises on
malformed input. No on-device tests.

## Prerequisites

- **TASK-014** — delivers the `Source` column and section-flex schema
  that the writer must round-trip.
- **TASK-022** — delivers the `src/partsledger/` package layout the
  writer module lives in.

## Sizing rationale

Writer contract is atomic — three downstream callers (TASK-016, TASK-043,
TASK-048) all depend on the full `upsert_row` signature including
pre-flush lint integration; splitting would invite signature drift
between partial scaffolds.
