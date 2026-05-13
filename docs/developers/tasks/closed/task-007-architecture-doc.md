---
id: TASK-007
title: Write docs/developers/ARCHITECTURE.md for the PartsLedger pipeline
status: closed
closed: 2026-05-13
opened: 2026-05-12
effort: Medium
effort_actual: Small (<2h)
complexity: Senior
human-in-loop: No
epic: align-with-circuitsmith
order: 7
---

## Description

Fresh-author `docs/developers/ARCHITECTURE.md` for PartsLedger. Unlike
the 13 docs in TASK-006, this is **not** a verbatim port —
CircuitSmith's `ARCHITECTURE.md` is specific to its circuit pipeline
(NetGraph, ERC engine, layout kernel, exporters, AI containment).
PartsLedger's pipeline is the camera → embeddings → vision → external-
API → MD-entry pipeline described in IDEA-001.

Mirror CircuitSmith's **structure**:

1. **Status banner** — current concept-stage caveat ("the modules
   below describe the *target* architecture; none of the product
   code exists yet").
2. **What it produces** — `inventory/parts/<part>.md` entries (the
   only authoritative output). Supporting artefact:
   `inventory/.embeddings/vectors.sqlite` (regenerable cache, never
   the source of truth).
3. **Pipeline** — a mermaid `flowchart LR` per the
   `MERMAID_STYLE_GUIDE.md` conventions:
   `camera capture → DINOv2 embedding → nearest-neighbour lookup → Claude Opus 4.7 Vision identification → Nexar/Octopart metadata fetch → MD entry author`.
   Skill-path entry skips the first three steps; both paths converge
   at "MD entry author".
4. **Module boundaries** — `graph TD` of the module-level
   dependencies. Placeholder until the modules actually land
   (PartsLedger is concept stage); the doc carries the **intent**
   and the forbidden edges that future modules must respect.
5. **Decoupling seams** — the load-bearing invariants:
   - **MD files are source of truth.** SQLite is cache.
     Regenerating the SQLite from MDs + images must always be
     possible. **Forbidden edge:** any writer that updates SQLite
     without a matching MD update.
   - **CircuitSmith reads PartsLedger via `--prefer-inventory`.**
     PartsLedger never imports anything from CircuitSmith. The MD
     schema is the contract; per IDEA-027 vocabulary.
6. **AI containment** — where vision / LLM calls run:
   - **Authoring time, yes.** Claude Opus 4.7 Vision identifies parts
     during entry creation. Claude Code skills (`inventory-add`,
     `inventory-page`) call the model.
   - **Runtime, no.** Inventory queries and CircuitSmith's read path
     hit the MD files directly. No LLM call gates an `inventory`
     read.
7. **Where to go next** — table linking out to `CODING_STANDARDS`,
   `TESTING`, `CI_PIPELINE`, `DEVELOPMENT_SETUP`, `TASK_SYSTEM`,
   `AUTONOMY`, `COMMIT_POLICY`, `BRANCH_PROTECTION_CONCEPT`,
   `SECURITY_REVIEW`, `CODE_OWNERS`, `MERMAID_STYLE_GUIDE`, ADR/.

Every mermaid block gets a prose summary alongside per
`MERMAID_STYLE_GUIDE.md § Accessibility`.

## Acceptance Criteria

- [x] `docs/developers/ARCHITECTURE.md` exists.
- [x] Sections match the seven-block structure above.
- [x] Two mermaid diagrams (pipeline `flowchart LR`, module-boundary
      `graph TD`), each with prose summary.
- [x] Forbidden edges between modules are explicitly named and
      annotated (red dashed style per `MERMAID_STYLE_GUIDE.md`).
- [x] All cross-doc links resolve.
- [x] `markdownlint-cli2` passes on the file.

## Test Plan

Render the mermaid blocks in a markdown viewer (or `mermaid-cli`) to
confirm the diagrams are valid. Walk the doc top-to-bottom and check
every claim against IDEA-001 and `CLAUDE.md` (the canonical
PartsLedger sources).

## Notes

This is design work, not a port. File an ADR under
`docs/developers/adr/` if a decision needs to be recorded mid-write
(per `AUTONOMY.md § ADR-on-ambiguity` once that lands in TASK-012).
Until TASK-012 lands the AUTONOMY framework, ADR-on-ambiguity is the
working contract anyway — `adr/0000-template.md` is in place after
TASK-006.

`MERMAID_STYLE_GUIDE.md` from TASK-006 is the style source — this
task does not predate it. If TASK-006 has not landed yet, defer
TASK-007 or temporarily use plain ASCII pipeline diagrams until
TASK-006 closes.
