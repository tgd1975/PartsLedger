---
id: TASK-057
title: Build pipeline test-fixture corpus under tests/fixtures/
status: paused
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: Support
epic: integration-followups
order: 1
prerequisites: [TASK-043]
---

## Description

Stand up a shared fixture corpus that the camera-path pipeline glue
(TASK-043) and its downstream sites can exercise without hardware or
network. The corpus has four artefacts:

1. **Golden frames** — a small set of well-lit, mid-resolution stills
   of parts already in the maker's bin (a TL082, an LM358N, an
   `xr2206cp`, a generic 2N3904), checked into
   `tests/fixtures/frames/`. These are the canonical inputs every
   recognition test loads.
2. **Cached embeddings** — pre-computed DINOv2 vectors for the golden
   frames, stored as a fixture-only sqlite-vec DB under
   `tests/fixtures/embeddings/vectors.sqlite`. Lets cache tests run
   without invoking the model.
3. **Mocked Nexar responses** — JSON snapshots of `supSearchMpn`
   results for each golden-frame MPN, under
   `tests/fixtures/nexar/<mpn>.json`. Enrichment tests load these via
   the cache module's seeded-fixture path.
4. **Mocked viewfinder verdicts** — recorded `pipeline.run()`
   `Outcome` shapes from running the pipeline against the golden
   frames once, then committed as `tests/fixtures/verdicts/*.toml`.
   Lets EPIC-005 overlay state machine tests run without the full
   recognition stack.

This corpus is the substrate IDEA-012 Gap 6 called out — it un-blocks
the pipeline-glue task's integration test plan and any future
regression test of the camera path.

## Acceptance Criteria

- [ ] `tests/fixtures/frames/` contains at least four golden frames,
      each with a matching `<mpn>.expected.json` describing the
      expected band, confidence, and writer-row outcome.
- [ ] `tests/fixtures/embeddings/vectors.sqlite` is rebuildable from
      the frames by a documented one-liner (`python -m
      partsledger.recognition.cache --rebuild-fixtures`).
- [ ] `tests/fixtures/nexar/` contains real Nexar responses captured
      once with `$PL_NEXAR_*` and scrubbed of secrets.
- [ ] `tests/fixtures/verdicts/*.toml` round-trips through the
      EPIC-005 overlay state machine without invoking the pipeline.
- [ ] CI passes with the corpus committed; no test depends on a live
      camera, live Nexar, or live VLM.

## Test Plan

**Host tests (pytest)**:

- `tests/integration/test_pipeline_fixtures.py` — assert each golden
  frame produces the recorded verdict when run through `pipeline.run()`
  with the cached embeddings and mocked Nexar.
- Cover: each band (`tight`, `tight_ambiguous`, `medium`, `miss`)
  exercised by at least one frame.

**Manual setup** (once, by the maker):

- Capture the golden frames with the actual USB camera.
- Run the one-shot capture script that generates embeddings, verdicts,
  and Nexar snapshots, then commits them.

## Prerequisites

- **TASK-043** — pipeline glue is the first runtime exerciser of the
  writer contract and the immediate consumer of this fixture corpus.

## Paused

- 2026-05-14: Waiting on TASK-043 (recognition pipeline glue) to move
  to active. Building the corpus before the pipeline shape stabilises
  would freeze the wrong verdict format.

## Notes

The corpus must be regenerable. Every artefact has a documented
rebuild path so a future model swap (DINOv2 → DINOv3, …) is a one-
command refresh, not a fixture archaeology dig.
