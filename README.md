# PartsLedger

> *PartsLedger keeps the record. [CircuitSmith](https://github.com/tgd1975/CircuitSmith) reads it before forging.*

An **LLM-native inventory for your parts bin**. Point a USB camera at a component → automatic identification → entry as a Markdown file. With every use, local recognition becomes faster and cheaper — without ever training a model explicitly.

## Status

🚧 **Concept stage** — the repo currently contains only the concept docs. Code to follow.

The full architecture and rationale live in **[concept.md](concept.md)**.

## Who is it for?

- You're a maker and your bin is full of modules, dev-boards, through-hole ICs, resistors, LEDs.
- You want to know what you **actually** have — queryable by you **and** by Claude, when it designs your next circuit.
- You don't want a web frontend with user management; you want files you can browse with `grep`, Obsidian, or GitHub.
- You don't want to label 200 photos before anything works.

## Core Idea

Inventory = a directory of Markdown files with YAML frontmatter, one file per part type:

```
inventory/
├── README.md                  ← auto-generated: overview + statistics
├── parts/
│   ├── ic-lm358n.md
│   ├── module-blue-pill.md
│   ├── resistor-10k.md
│   └── …
├── images/
└── .embeddings/
    └── vectors.sqlite         ← regenerable cache
```

Why Markdown instead of SQL: LLMs read `cat inventory/parts/*.md` directly — no ORM, no API wrapper. Git is the history. The schema is compatible with the sibling skill [CircuitSmith](https://github.com/tgd1975/CircuitSmith), which prefers parts you actually own when designing a schematic.

## Architecture (in brief)

```
USB camera ──► DINOv2 embedding ──► Search vector DB
                                          │
                                ┌─────────┴─────────┐
                                ▼                   ▼
                       Known → done.        Unknown → Claude Opus 4.7 Vision
                                                   + Nexar/Octopart metadata
                                                   + user confirmation
                                                   → new parts/*.md
                                                   → cache embedding
```

Active learning without upfront training: the first photo of a new type runs the full pipeline; from the second photo onwards, the local embedding lookup suffices. Details, example frontmatter, component table, and boundaries are in **[concept.md](concept.md)**.

## Target Audience & Scope

✅ Through-hole, modules (Blue Pill, ESP32, WeMos D1 Mini, DRV8825, HC-SR04 …), dev-boards, DIP/TO-220/SOIC ICs, resistors, capacitors, LEDs.

❌ SMD micro-parts with 2-3-character marking codes (SOD-323 diodes etc.) — a standard webcam can't resolve them optically. Deliberately out of scope.

❌ No web UI, no multi-user mode, no audit trail. If you need those, use [InvenTree](https://inventree.org/) or [Part-DB](https://github.com/Part-DB/Part-DB-server) — happily side-by-side.

## Planned Components

| Job | Library / service |
|---|---|
| Camera capture | OpenCV |
| Local embedding | DINOv2 (via `torch.hub`) |
| Vector DB | sqlite-vec |
| Part identification — hosted VLM | Anthropic SDK — Claude Opus 4.7 Vision |
| Part identification — alternative VLM | Mistral Pixtral (API) or Pixtral 12B (open weights, self-hosted) |
| Metadata enrichment | Nexar GraphQL API (Octopart) |
| OCR (optional) | PaddleOCR or Tesseract |

## Roadmap

- [x] Concept & schema sketch ([concept.md](concept.md))
- [ ] Markdown schema as a formal spec (frontmatter, CircuitSmith-compatible)
- [ ] Python skeleton: USB camera + DINOv2 + sqlite-vec
- [ ] Claude Vision integration for unknown parts
- [ ] Confirmation UI (TUI or web)
- [ ] Nexar/Octopart enrichment
- [ ] Index generator (`inventory/README.md` with statistics)
- [ ] CircuitSmith adapter (`--prefer-inventory` mode)

## Sibling Projects

- **[CircuitSmith](https://github.com/tgd1975/CircuitSmith)** *(planned)* — forges schematics, reads PartsLedger as its preferred component source.
- **[AwesomeStudioPedal](https://github.com/tgd1975/AwesomeStudioPedal)** — currently hosts `IDEA-027`, the draft of the circuit skill that will move into CircuitSmith.

## License

[MIT](LICENSE) © 2026 tgd1975
