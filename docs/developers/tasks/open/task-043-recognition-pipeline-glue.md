---
id: TASK-043
title: Pipeline glue — pipeline.run(image) -> Outcome with re-frame loop and writer hand-off
status: open
opened: 2026-05-14
effort: Large (8-24h)
complexity: Senior
human-in-loop: Support
epic: visual-recognition
order: 5
prerequisites: [TASK-016, TASK-017, TASK-041, TASK-042, TASK-048]
---

## Description

IDEA-007 Stage 4 — the integration step where the dossier becomes a
working camera-path. This is the **integration choke-point** for the
visual-recognition epic: first runtime use of TASK-016 (writer contract),
TASK-017 (pre-flush lint), TASK-041 (banded recognition), TASK-042 (VLM),
and TASK-048 (enrichment orchestrator).

Extend `src/partsledger/recognition/pipeline.py` with
`run(image) -> Outcome`. Variants:

- `Wrote(label, source: cache | vlm)` — silent qty++ happened; cache row
  inserted; the IDEA-006 viewfinder will render a confirmation flash
  (annotated *"via VLM"* when `source == vlm`).
- `Reframing(hint)` — viewfinder shows the *R retry / X abort* prompt
  with the hint as overlay.
- `EscalatedToManual` — hand off to `/inventory-add`; no write, no cache
  row.

Branching follows IDEA-007 § The recognition pipeline:

| Classify band | Action |
|---|---|
| `tight` | Silent cache-write via TASK-016 writer; cache-learn. |
| `tight_ambiguous` | VLM disambiguates; route VLM verdict per below. |
| `medium` | `Reframing(generic-hint)` — never auto-VLM, never auto-pick. |
| `miss` | VLM identifies; route VLM verdict per below. |

VLM verdict routing:

- `HedgedID` → silent write (source: vlm); cache-learn with marking text.
- `NeedsReframe(hint)` → `Reframing(hint)`.
- `NoIdea` → `EscalatedToManual`.

Re-frame loop is owned by this stage — IDEA-006 stays loop-less. Cap of
**2 retries per part** before the abort path triggers automatically;
counter resets on the next physically distinct part (time gap +
distinctly different embedding heuristic).

Cache-learn happens after every successful silent write — insert
`(embedding, label, marking_text_or_null, image_hash)` via
`cache.insert()`.

MD write goes through the TASK-016 writer contract; lint runs pre-flush
via TASK-017. Best-effort enrichment hand-off via TASK-048 per IDEA-007
§ Pipeline failure modes — enrichment failures **never** roll back the
write.

## Acceptance Criteria

- [ ] Golden image with a pre-cached match → `Wrote(label, source=cache)`; new cache row inserted.
- [ ] Tight-band ambiguity → VLM (mocked, returns `HedgedID`) → `Wrote(label, source=vlm)`; flash annotated *via VLM*.
- [ ] Medium-band image → `Reframing(generic-hint)`; retry-counter increments; third attempt yields `EscalatedToManual`.
- [ ] Miss + VLM `NoIdea` → `EscalatedToManual`; no qty++, no cache row.
- [ ] Mocked enrichment failure (TASK-048) during a write → qty++ and cache-learn still land; pipeline does not retry, does not roll back.
- [ ] MD-writer failure (TASK-016) aborts before cache-learn — cache and inventory never diverge.

## Test Plan

**Host tests** (pytest):

- Add `tests/recognition/test_pipeline_run.py`.
- Mock cache, VLM, writer, and enrichment; cover each branching path in
  the table above plus the failure-soft enrichment edge and the
  hard-abort writer edge.

**Manual integration test** (run by maintainer at task close):

- Exercise the full chain against a fixture image set; the corpus is
  delivered by TASK-057 in EPIC-009 (pipeline test fixtures: golden
  frames + pre-cached embeddings + mocked VLM responses).
- Walk one image through each band (tight, tight_ambiguous, medium,
  miss); confirm the expected `Outcome` and inventory side-effects.
- The `human-in-loop: Support` value reflects this — a human runs the
  fixture walk before the task closes.

## Prerequisites

- **TASK-016** — MD writer contract: `Outcome` shape (success / lint-fail / disk-fail) consumed here.
- **TASK-017** — pre-flush lint: invoked before every write so a malformed MD never lands.
- **TASK-041** — banded `classify()`: the branching decision input.
- **TASK-042** — VLM adapter: called on `tight_ambiguous` / `medium` / `miss` per the routing table.
- **TASK-048** — enrichment orchestrator: best-effort hand-off after every silent write.

## Sizing rationale

Pipeline glue is the convergence point for five upstream modules with
structured outputs (writer Outcome, lint result, recognition band, VLM
verdict, enrichment hand-off); decomposing would create partial wirings
that mask integration defects until late.

## Notes

The `Outcome` variants here are the payload IDEA-006 § Overlays during
recognition renders on the viewfinder. The schema is co-constrained with
that surface — changes here imply IDEA-006 viewfinder changes.
