# PartsLedger — Concept

> *"PartsLedger keeps the record. CircuitSmith reads it before forging."*

## Goal

A maker (through-hole, modules, dev-boards, larger ICs) wants to digitise their parts bin. Hold a component under the USB camera → automatic identification → entry in a Markdown-based inventory with datasheet, description, and storage location. With every use, the system becomes faster and more accurate, with no explicit training.

## Target Audience & Scope

- **Makers / hobbyists**: through-hole components, modules (Blue Pill, ESP32, WeMos D1 Mini, DRV8825, HC-SR04, MAX7219 …), dev-boards, larger ICs in DIP/TO-220/SOIC.
- **Deliberate non-goals**: SMD micro-parts (SOD-323 diodes with 2-3-character marking codes), industrial AOI applications, multi-user web frontend with audit trail.

## Core Idea: LLM-Native Markdown Inventory

The inventory is **not** kept in a SQL database, but as a directory of Markdown files with YAML frontmatter. Rationale:

- LLMs (especially Claude) can read the entire inventory directly — `cat inventory/parts/*.md` is the only "query layer" you need. No API wrapper, no ORM.
- Git becomes the history — every stock movement is a commit; `git log inventory/parts/resistor-10k.md` shows the full history of a part.
- Schema-compatible with [CircuitSmith / IDEA-027](https://github.com/tgd1975/AwesomeStudioPedal/blob/main/docs/developers/ideas/open/idea-027-circuit-skill.md): inventory fields (`quantity`, `locations`) as a superset over the component-profile fields (`vcc_min`, `pins`, …).
- Tool diversity: Obsidian, VS Code, grep, the GitHub web UI all work without adaptation.

## Hardware

- USB webcam (2K is enough), good desk lamp or ring light.
- Any Linux/Win/Mac machine with Python.
- **No** macro lens, **no** USB microscope required (scope: maker components, no SMD marking codes).

## Architecture (Hybrid Pipeline)

```
[USB camera capture via OpenCV]
        │
        ▼
[Compute DINOv2 embedding] ──► [Search local vector DB (sqlite-vec)]
        │                              │
        │                       ┌──────┴──────┐
        │                       ▼             ▼
        │             Small distance:   Large distance:
        │             instant match     "unknown"
        │             (no API call)           │
        │                       │             ▼
        │                       │     ┌───────────────────────────┐
        │                       │     │ Identification pipeline:  │
        │                       │     │  • Claude Opus 4.7 Vision │
        │                       │     │    (reads markings,       │
        │                       │     │     identifies modules)   │
        │                       │     │  • Optional: resistor     │
        │                       │     │    colour-band reader     │
        │                       │     │  • Octopart/Nexar API     │
        │                       │     │    for metadata           │
        │                       │     └─────────────┬─────────────┘
        │                       │                   │
        │                       ▼                   ▼
        │              [Maker confirms via TUI/Web UI]
        │                                  │
        ▼                                  ▼
[Embedding + label stored in vector DB — system "learns"]
                                  │
                                  ▼
              [Write/update inventory/parts/*.md]
```

### Roles of the Components

- **Vision Language Model (VLM)** = star of the pipeline. Reads markings (`10kΩ`, `L7805CV`, `LM358N`), identifies modules (`Blue Pill with STM32F103`, `DRV8825 driver`). Hit rate on maker-grade parts is estimated at 80-90 % with decent lighting. The VLM is pluggable; two first-class backends are planned:
  - **Claude Opus 4.7 Vision** (Anthropic API) — hosted, top-tier accuracy on dense / hand-written / damaged markings.
  - **Mistral Pixtral** (Pixtral Large via Mistral API, or open-weight **Pixtral 12B** self-hosted via `vllm` / `transformers`) — same multimodal role; the open-weight variant lets the entire pipeline run offline once the embedding DB has warmed up.
- **DINOv2 embeddings** = local cache. Distinguish package types and module shapes (TO-92 vs. TO-220 vs. electrolytic cap vs. film cap). Second photo of an already-seen part type → instant match, no API call.
- **Octopart / Nexar GraphQL API** = metadata enrichment (datasheet, manufacturer, pinout, prices).
- **Resistor colour-band reader** = optional small OpenCV module.
- **Markdown writer** = orchestrates writing/updating `inventory/parts/*.md`.

## Active Learning Without Upfront Training

Instead of training a classifier on fixed classes, DINOv2 is used purely as a feature extractor:

1. First photo of a new part type → compute embedding → search vector DB → nothing similar → full pipeline (Claude + Octopart) takes over.
2. Maker confirms the identification.
3. Embedding is stored with the label in the vector DB.
4. Second photo of the same part type → embedding similar → instant match, no API call.

After 3-5 scans per part type, local recognition becomes faster and cheaper than the Claude pipeline. There is **no** explicit training session.

### Confidence-Based Behaviour

- **Small distance** → confident match, no follow-up.
- **Medium distance** → top-3 candidates for confirmation.
- **Large distance** → unknown, full pipeline runs.

## Directory Layout

```
inventory/                       ← The maker's view (their own bin)
├── README.md                    ← auto-generated index + statistics
├── parts/
│   ├── ic-lm358n.md             ← one file per part type
│   ├── module-blue-pill.md
│   ├── led-5mm-red.md
│   ├── resistor-10k.md
│   └── …
├── images/
│   └── ic-lm358n-001.jpg
└── .embeddings/
    └── vectors.sqlite           ← DINOv2 cache (regenerable)
```

Truth lives in the `.md` files. `.embeddings/vectors.sqlite` is only a cache and can be rebuilt at any time from the images + MDs.

## Example: parts/ic-lm358n.md

```markdown
---
id: lm358n
category: ic
sub_category: opamp
type: lm358n              # matches CircuitSmith component-type
package: DIP-8
manufacturer: Texas Instruments
mpn: LM358N
# Inventory (maker-specific)
quantity: 3
locations:
  - box: 7
    slot: A2
date_added: 2026-05-12
# Electrical properties (compatible with CircuitSmith profile format)
vcc_min: 3.0
vcc_max: 32.0
pins:
  1: { name: "1OUT", side: "right" }
  2: { name: "1IN-", side: "left" }
  # …
metadata:
  keywords: [opamp, dual, low-power, amplifier]
  datasheet: https://www.ti.com/lit/ds/symlink/lm358.pdf
  octopart_url: https://octopart.com/lm358n-...
  photo: ../images/ic-lm358n-001.jpg
---

# LM358N — Dual Operational Amplifier

3 in stock in box 7, slot A2.

## Known uses
- Pre-amp project (2025-03)
- Active filter experiment (2026-01)

## Notes
One of the three has pin 8 slightly bent — use it last.
```

## Integration with CircuitSmith

PartsLedger is the inventory layer; CircuitSmith (= IDEA-027) is the schematic layer. The bridge:

- CircuitSmith gains a `--prefer-inventory` mode: during component selection, it first checks what is actually in stock before drawing from the full library.
- The existing `components/*.py` profiles in CircuitSmith become fallback templates — if the inventory contains an MD file with `type: lm358n`, CircuitSmith uses it; otherwise it falls back to the hardcoded profile.
- BOM generation gets three columns: "needed", "already in stock", "still to order".
- Adapter effort: a ~50-line patch in the CircuitSmith loader that reads `inventory/parts/*.md` and registers them as additional profiles in the `components/` lookup path.

## Data Flows

- **Always local**: DINOv2 inference, sqlite-vec, OpenCV capture, colour-band reader, Markdown writer.
- **VLM call** (only for unknown parts): either Claude API / Mistral API (cloud), **or** self-hosted Pixtral 12B (no network).
- **Metadata enrichment**: Nexar/Octopart API (cloud, optional — can be deferred or skipped; the maker can also fill datasheet links manually later).
- **No server required**: everything is file-based. If you want a web interface on top, run InvenTree/Part-DB alongside.

### Fully Offline Mode

If you self-host Pixtral 12B and skip Nexar enrichment, **the entire pipeline runs offline** after the initial model download. The maker confirms parts locally, the embedding cache grows locally, and inventory commits are pure git operations. No request ever leaves the workstation. This is a real option, not an aspiration — Pixtral 12B is Apache-licensed and runs on a single consumer GPU.

## What We Build vs. What We Use

| Component | Source | Status |
|---|---|---|
| Embedding backbone | `facebookresearch/dinov2` via `torch.hub` | ✅ pretrained |
| Vector DB | `sqlite-vec` (or FAISS) | ✅ stable |
| Camera capture | OpenCV (`cv2.VideoCapture`) | ✅ standard |
| VLM (hosted) | Anthropic SDK (Claude Opus 4.7) | ✅ multimodal |
| VLM (alternative, self-hostable) | Mistral Pixtral — Pixtral Large via API, or Pixtral 12B (open weights, Apache 2.0) via `vllm` | ✅ multimodal |
| Metadata | Nexar GraphQL API (Octopart) | ✅ free tier |
| OCR (optional) | PaddleOCR or Tesseract | ✅ open source |
| Component datasets (fallback) | Roboflow Universe | ✅ CC BY 4.0 |

**We build**: pipeline orchestration, capture loop, confirmation UI, Markdown schema, index generator, CircuitSmith adapter.

## What PartsLedger Is *Not*

- **Not a replacement for InvenTree / Part-DB / Binner**. If you want a web interface, multi-user access, and an audit trail, use one of those tools. PartsLedger is deliberately LLM-native and file-based.
- **Not a competing schema to CircuitSmith** — PartsLedger is a superset of the CircuitSmith component profiles.
- **Not an SMD identification tool**. For SMD marking codes (`A6`, `T4`), a standard webcam is optically insufficient; that would require a USB microscope and a separate SMD-code database — deliberately out of scope.

## Market Gap (as of 2026-05)

- InvenTree issue #623 (photo-based component identification) has been open and unanswered since 2020.
- Existing tools (InvenTree, Part-DB, Binner) use cameras exclusively for barcode scanning of supplier labels.
- Visual component recognition exists only as research/student projects (`nazar`, `Electronic-Component-Sorter`) — no production-ready tools.
- An Aalto Master's thesis (December 2025) confirms: hybrid approaches (VLM + traditional methods) are economically the most viable — exactly the architecture PartsLedger implements.

**Bottom line**: we don't reinvent the wheel — we build the car that bolts the existing wheels together.

## Sibling Projects

- [CircuitSmith](https://github.com/tgd1975/CircuitSmith) (planned) — forges schematics, reads PartsLedger as its preferred component source.
- [AwesomeStudioPedal](https://github.com/tgd1975/AwesomeStudioPedal) — currently hosts IDEA-027, which will move into CircuitSmith.
