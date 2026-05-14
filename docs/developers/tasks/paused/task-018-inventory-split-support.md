---
id: TASK-018
title: Multi-file INVENTORY.md split support + suggestion trigger
status: paused
opened: 2026-05-14
effort: Large (8-24h)
complexity: Medium
human-in-loop: Clarification
epic: markdown-inventory-schema
order: 5
prerequisites: [TASK-014]
---

## Description

Implement IDEA-004 Stage 3 — multi-file `INVENTORY.md` once a maker's
bin reaches the size where one file is uncomfortable. Not a speculative
ship: only land when a maker actually accepts the suggestion or asks
for it. Schema-side, the row format is identical either way; only the
file boundary moves.

Three coordinated layers:

1. **Glob-by-convention reader.** Every tool that reads `INVENTORY.md`
   directly today switches to a glob: `inventory/*.md` minus the master
   file. Frontmatter `parts:` manifest reserved as a fallback only if a
   maker has unrelated `.md` files in `inventory/`.
2. **`co-inventory-master-index` extension.** When the master file
   contains link-to-per-section-file rows rather than table rows,
   validate the split shape: per-section files share the row schema;
   the master lists all of them; no row appears twice across files.
3. **`/inventory-add` suggestion trigger** with decline-stickiness. The
   trigger fires when the master file passes a practical threshold
   (initial proposal: 200 rows or 30 KB, whichever first; refine on
   real data). Suggestion is advisory; the maker has the final call.
   A "no thanks" persists via a single HTML-comment marker the skill
   writes directly below the H1:

   ```text
   <!-- pl: split-suggestion-declined -->
   ```

   The trigger reads the file before nagging; if the marker is present,
   it stays silent. Marker storage matches the project's
   MD-as-source-of-truth stance — no sidecar files, no hidden state. A
   maker who later wants the suggestion to fire again deletes the line
   by hand; that's the only re-arm path, by design.

Documentation update: IDEA-004 § `INVENTORY.md — the flat index` points
at the implementation.

## Paused

2026-05-14: Deferred until a maker's bin grows past the practical
single-file threshold (proposal: 200 rows or 30 KB).

## Acceptance Criteria

- [ ] A split test bin (three section files + master) round-trips
      through `co-inventory-master-index` cleanly.
- [ ] The glob-by-convention reader picks up every section file and
      ignores the master.
- [ ] No row appears twice across files (validated by the guard
      extension).
- [ ] Threshold-hit fires the suggestion exactly once; a decline writes
      the HTML-comment marker and silences future suggestions for that
      bin.
- [ ] Deleting the marker by hand re-arms the trigger.

## Test Plan

Host tests (pytest) + manual: split test bin (3 section files + master)
round-trips through `co-inventory-master-index` cleanly; threshold-hit
fires once; decline silences.

## Prerequisites

- **TASK-014** — delivers the `Source` column and section-flex schema
  the split files share; the family-page and row-shape invariants must
  be settled before the split-mode guard can validate them across files.

## Sizing rationale

Split-mode is a coherent shape-change touching three layers (reader
glob, runtime guard, suggestion trigger with persistent decline marker);
decomposing would create partial states where two layers disagree about
the split shape.
