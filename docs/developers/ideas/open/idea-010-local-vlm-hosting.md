---
id: IDEA-010
title: Local model hosting — VLM and embedding backbone, Ollama-first, fully offline mode
description: Local hosting of all camera-path models — VLM (Pixtral et al. via Ollama / vllm / llama.cpp) and DINOv2 embedding backbone (via torch.hub). Owns the fully-offline story.
category: camera-path
---

> *Spun off from [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md)
> during the 2026-05-13 hone, when the recognition-pipeline dossier
> adopted an OpenAI-compatible REST interface for the VLM. With that
> interface in place, **where** the VLM physically runs becomes a
> deployment decision rather than an architectural one — and deserves
> its own dossier instead of crowding IDEA-007.*

## Status

⏳ **Planned.** No code yet. Lives alongside the rest of the
camera-path family ([IDEA-006](idea-006-usb-camera-capture.md),
[IDEA-007](idea-007-visual-recognition-dinov2-vlm.md),
[IDEA-008](idea-008-metadata-enrichment.md)).

## Why this is its own idea

[IDEA-007 § VLM interfacing](idea-007-visual-recognition-dinov2-vlm.md#vlm-interfacing--one-openai-compatible-rest-adapter)
speaks OpenAI-compatible REST to whatever endpoint `$PL_VLM_BASE_URL`
points at. Whether that endpoint lives on `api.anthropic.com`,
`localhost:11434` (Ollama), or a self-managed `vllm` server is a
**deployment** decision, not a recognition-pipeline one. Mixing the
two concerns muddied both halves of the previous IDEA-007. This
dossier owns the local-VLM deployment story; IDEA-007 keeps owning
what to do with the verdict the VLM emits.

## What this idea covers

- **Runtime options** for hosting a multimodal LLM locally —
  Ollama as the default, `vllm` and `llama.cpp` as power-user
  alternatives.
- **Model choices** that work for the marking-text-reading workload
  IDEA-007 needs (Pixtral 12B, LLaVA-NeXT, Qwen-VL, …).
- **Hardware requirements** — VRAM, CPU vs GPU, sweet-spot models
  for laptop-class hardware.
- **The fully-offline-mode story** — when local hosting actually
  matters, and how the maker switches between hosted and local.
- **Model-pull / management workflow** — how the maker swaps models
  without touching code.
- **Embedding backbone hosting** — the small DINOv2-ViT-S/14 model
  IDEA-007's cache stage uses. Comes via `torch.hub`, not Ollama,
  but its *"how do I run this offline?"* question is the same shape
  as the VLM's and belongs in the same dossier.

## What this idea explicitly does NOT cover

- The recognition pipeline itself — distance bands, verdicts, undo,
  the re-frame loop. That lives in
  [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md).
- The viewfinder UI and overlays. That lives in
  [IDEA-006](idea-006-usb-camera-capture.md).
- Choosing between *hosted* providers (Anthropic vs Mistral vs
  OpenRouter etc.). The OpenAI-compatible REST adapter in IDEA-007
  treats all endpoints uniformly; hosted-vs-local is one env var.

## Runtime options

### Ollama — the recommended default

[Ollama](https://ollama.ai/) wraps `llama.cpp` with a maker-friendly
CLI plus an OpenAI-compatible REST server. The exact integration
point this dossier promises:

```bash
ollama pull pixtral
ollama serve   # exposes http://localhost:11434/v1/chat/completions
```

Then in PartsLedger's `.envrc`:

```bash
export PL_VLM_BASE_URL="http://localhost:11434/v1"
export PL_VLM_MODEL="pixtral"
# No PL_VLM_API_KEY needed for local Ollama
```

The IDEA-007 adapter speaks the same OpenAI-compatible REST to
Ollama as it does to Anthropic. Switching between local and hosted
is purely env-var-driven; no code change.

Why Ollama as the default:

- **Single-binary install** on Linux, macOS, Windows.
- **Model management built-in** (`ollama pull`, `ollama list`,
  `ollama rm`).
- **GPU + CPU fallback** without configuration.
- **Cross-platform** matches PartsLedger's Linux + Windows 11
  development context ([CLAUDE.md § OS context](../../../../CLAUDE.md#os-context)).
- **OpenAI-compatible API native** — no shim, no manual JSON
  munging on PartsLedger's side.

### vllm — the power-user option

For makers with multi-GPU machines, batch-inference needs, or
specific quantisation preferences, [vllm](https://github.com/vllm-project/vllm)
is the go-to. Higher throughput, lower latency, more knobs.
PartsLedger doesn't recommend it as the default because the setup
gap to "first capture identified" is much wider than Ollama's.

`vllm` also exposes an OpenAI-compatible endpoint, so the
integration contract is identical:

```bash
vllm serve mistralai/Pixtral-12B-2409 --port 8000
# In .envrc: export PL_VLM_BASE_URL="http://localhost:8000/v1"
```

### llama.cpp — the bare-metal option

Direct [llama.cpp](https://github.com/ggerganov/llama.cpp) (without
Ollama on top) is documented as a fallback for environments where
Ollama can't run — very constrained containers, exotic
architectures. Same OpenAI-compatible endpoint pattern via
`llama-server`.

## Model choices

Marking-text reading is the discriminative feature IDEA-007 needs.
The following local-runnable VLMs are candidates — to be
re-benchmarked when this idea is implemented because the model
landscape moves fast:

| Model | VRAM (fp16) | License | Notes |
|---|---|---|---|
| Pixtral 12B | ~24 GB | Apache 2.0 | Strong marking-text reader, the bar to beat. |
| LLaVA-NeXT 7B | ~14 GB | Llama-2 | Fits on most consumer GPUs. |
| LLaVA-NeXT 13B | ~26 GB | Llama-2 | Similar OCR-ish capability to Pixtral. |
| Qwen-VL 7B / 14B | ~16 / ~30 GB | Apache 2.0 | Especially strong on Asian-text marking. |

Quantised versions (Q4\_K\_M, Q5\_K\_M) cut these by 50–60 % VRAM
at modest quality cost. The exact best model depends on the maker's
marker mix — to be benchmarked on a representative slice of the
bastelkiste before any default lands.

## Hardware requirements

- **Comfortable home.** Any consumer GPU with ≥ 16 GB VRAM
  (RTX 4080, 4090, 3090) runs a quantised Pixtral 12B or a full
  LLaVA-NeXT 7B comfortably at ~5–10 s per capture.
- **Tight fit.** An 8 GB VRAM GPU (RTX 4060, 3060) runs LLaVA-NeXT
  7B at aggressive quantisation. Slower but usable.
- **CPU-only.** Works for the smallest models but inference is
  measured in 30+ seconds per capture. Only worth it if the maker
  is deeply committed to offline operation and has time to spare.

## Embedding backbone hosting

The DINOv2-ViT-S/14 model that
[IDEA-007 § Stage 1](idea-007-visual-recognition-dinov2-vlm.md#stage-1--dinov2-as-similarity-cache)
uses ships **not** as a model file but as a `torch.hub` pull:

```python
model = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14")
```

On first invocation, `torch.hub` fetches ~80 MB of weights from
GitHub into `~/.cache/torch/hub/`. **Subsequent calls are offline** —
the weights cache is honoured automatically. So the embedding
backbone needs network *exactly once per maker per model version*.

**Fully-offline path** (for makers who never want the workstation
to reach out, even on first run):

- Pre-pull on a connected machine: run the `torch.hub.load(...)`
  call once. The weights land in `~/.cache/torch/hub/`.
- Copy / `rsync` that directory to the offline workstation.
  PartsLedger then uses the cached weights and never touches the
  network for embeddings again.
- IDEA-007 pins the backbone model name + content hash in the
  embedding cache; if the offline workstation's cached weights
  don't match what the cache expects (e.g. the maker rebuilt a
  fresh `~/.cache/torch/hub/` and got a different version), the
  cache-rebuild policy from IDEA-007 catches the mismatch and
  treats the cache as empty.

### Hardware — why this isn't a story

DINOv2-ViT-S/14 is small: 21M params, fits in any consumer GPU's
VRAM headroom, runs on **CPU** at ~200 ms/image, on a consumer GPU
at < 20 ms. No quantisation. No model-pull skill. No GPU-class
threshold worth a table. The hardware constraint for the camera
path lives entirely with the VLM (see
[§ Hardware requirements](#hardware-requirements) above).

### Why this is in IDEA-010 and not IDEA-007

The embedding backbone is a **local model just like Pixtral**. It's
small enough that its *"how do I run this offline?"* question is
much shorter (no GPU sizing, no quantisation, no `ollama pull`),
but it's the same shape of question. Putting it next to the VLM
hosting story keeps both *"local model"* questions in one place,
and matches the dossier's renamed scope (*"local model hosting"*,
not *"local VLM hosting"*).

## Fully offline mode — when this matters

The architecture is designed so that `$PL_VLM_BASE_URL` pointing at
`http://localhost:11434/v1` *and* `$PL_NEXAR_*` left unset gives the
maker a pipeline that makes **zero network requests** end-to-end.
The trade-off is the manual datasheet step — the maker pastes the
datasheet URL after identification, because
[IDEA-008](idea-008-metadata-enrichment.md) metadata enrichment is
the other half of the network-dependence story.

When is this a real concern, not aspiration?

- Maker is on a flight, in a workshop without WiFi, or behind a
  firewall that blocks LLM APIs.
- Maker is privacy-allergic about photos of their bench / parts
  leaving the workstation.
- Cost discipline — the maker wants a pay-once-in-GPU-and-electricity
  identification path rather than per-capture API spend.

For the average bastelkiste session, hosted is faster and cheaper
*per capture* but local is cheaper *amortised over hundreds of
captures* and is fully under the maker's control. Both are valid
defaults for different makers.

## Model-pull / management workflow

The naive answer: the maker runs `ollama pull <model>` when they
want a new model, and updates `$PL_VLM_MODEL` in `.envrc`.
PartsLedger itself stays model-agnostic; the model identity is in
configuration, not code.

Open question: should PartsLedger ship a *recommended model* helper
that runs `ollama pull` for the maker on first run? Or should we
trust the maker to know what they want? Probably the latter —
exposing more `ollama` to the maker risks the same anti-pattern as
the V4L2 / DirectShow vocabulary that
[IDEA-006](idea-006-usb-camera-capture.md) explicitly hides.

## Open questions to hone

- **Default local model.** Once the bastelkiste's marker makeup is
  known, benchmark Pixtral 12B vs LLaVA-NeXT vs Qwen-VL on the
  maker's representative parts and pick a recommended default.
  Until then, Pixtral 12B is the placeholder.
- **Quantisation policy.** Q4\_K\_M vs Q5\_K\_M vs fp16. The
  trade-off is VRAM vs marking-text-reading accuracy. Worth
  benchmarking before promoting any default.
- **GPU-class threshold.** What's the minimum GPU below which we
  recommend the maker just use the hosted Anthropic path instead?
  Likely ~8 GB VRAM, but worth validating. (Inherited from
  IDEA-007's *GPU requirements* open question.)
- **Ollama vs llama.cpp split.** Is Ollama enough for everyone, or
  do we need to document `vllm` / `llama.cpp` as first-class
  options? Depends on how many makers actually want the bare-metal
  control.
- **Cross-platform Ollama quirks.** Windows 11 GPU acceleration for
  Ollama is younger than Linux's; any caveats worth documenting?
- **DINOv2 weight re-use across Win11 + Ubuntu.** PartsLedger
  develops on both OSes
  ([CLAUDE.md § OS context](../../../../CLAUDE.md#os-context)),
  so the same maker rebuilds `~/.cache/torch/hub/` twice — once
  per machine. The
  [embedding-backbone offline section](#embedding-backbone-hosting)
  above covers the *first-pull-then-rsync* path, but doesn't
  address the dual-boot / dual-workstation case where the same
  maker would happily share weights between their two machines.
  Options: (a) document a portable `~/.cache/torch/hub/` shared
  via Syncthing or a USB stick; (b) ship a `partsledger
  prefetch-weights` helper that writes into a project-local
  `inventory/.embeddings/torch-hub/` so the cache rides along
  with the inventory tree; (c) accept the one-time ~80 MB
  re-download as a non-issue. Low priority — *one-time per
  machine* annoyance, not per-session friction. Re-open if the
  maker actually rebuilds weights often enough to care.
- **First-run-helper.** Should PartsLedger ship a small bootstrap
  that runs `ollama pull` for the maker on first invocation, or do
  we deliberately stay hands-off?
- **Should this idea become a task?** When the maker actually
  decides to invest in local hosting, this dossier should turn into
  a set of tasks (install Ollama, pull a model, benchmark, document).
  Until then it stays an idea.

## Related

- [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) — the
  recognition pipeline this idea hosts the VLM for. IDEA-007's
  OpenAI-compatible REST interface is what makes this spin-off
  clean.
- [IDEA-006](idea-006-usb-camera-capture.md) — the capture stage;
  doesn't care where the VLM lives.
- [IDEA-008](idea-008-metadata-enrichment.md) — the other half of
  the fully-offline-mode story (datasheet enrichment is the other
  network-dependent step).
- [CLAUDE.md § OS context](../../../../CLAUDE.md#os-context) —
  Linux + Windows 11 platform support shapes the runtime choice.
