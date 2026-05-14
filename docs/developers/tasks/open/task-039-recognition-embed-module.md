---
id: TASK-039
title: Implement src/partsledger/recognition/embed.py — DINOv2-ViT-S/14 via torch.hub
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: No
epic: visual-recognition
order: 1
prerequisites: [TASK-022]
---

## Description

Bring up the embedding primitive for the recognition pipeline. This is the
*embed* half of IDEA-007 Stage 1 — Stage 2 (`cache.py`) and Stage 4
(`pipeline.py`) sequence after it.

New module `src/partsledger/recognition/embed.py` loads the
`facebookresearch/dinov2` ViT-S/14 backbone via `torch.hub` on module init,
caches the loaded model so subsequent imports are zero-cost, and exposes
`embed(image: np.ndarray) -> np.ndarray` — BGR `np.ndarray` in, 768-D
L2-normalised `float32` vector out. The backbone stays frozen; no
fine-tuning, no training mode (`model.eval()` only).

First invocation pulls ~80 MB of weights from PyTorch Hub into
`~/.cache/torch/hub/`. The fully-offline pre-pull workflow is owned by
IDEA-010 § Embedding backbone hosting and is out of scope here — this task
only needs the online-first-run path to work.

Also exposes the model's content hash (e.g. `dinov2_vits14#sha256:abc123…`)
as a module-level constant so `cache.py` (TASK-040) can pin it in the
cache's metadata table for the rebuild-on-mismatch policy.

## Acceptance Criteria

- [ ] `embed(image)` returns a 768-D `float32` numpy array with L2 norm == 1.0 (±1e-6).
- [ ] Two calls of `embed()` on byte-identical input return byte-identical vectors.
- [ ] Module-level model load is idempotent: importing the module twice does not re-download or re-instantiate the backbone.
- [ ] A `MODEL_HASH` (or equivalent) constant is exported, formatted as `dinov2_vits14#sha256:<hex>`.
- [ ] CPU path works (no CUDA assumed); the module does not raise on a CPU-only host.

## Test Plan

**Host tests** (pytest):

- Add `tests/recognition/test_embed.py`.
- Cover: output shape (768,), dtype float32, L2 norm ≈ 1.0, determinism on
  identical input, `MODEL_HASH` is non-empty and matches the
  `dinov2_vits14#sha256:` shape.
- The first-run weight download is network-bound; mark the
  network-touching test with a skip-if-offline guard so CI on an
  air-gapped runner does not flake.

## Prerequisites

- **TASK-022** — Python package skeleton under `src/partsledger/` with the
  recognition subpackage in place; this task adds the first module under it.

## Notes

The 768-D figure assumes ViT-S/14 (the chosen backbone — IDEA-007 closed-Q
*Backbone choice*). Do not parameterise the dimension; the cache schema
(TASK-040) pins it.
