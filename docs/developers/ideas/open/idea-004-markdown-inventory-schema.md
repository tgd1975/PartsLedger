---
id: IDEA-004
title: Markdown inventory schema
description: The two-file shape (INVENTORY.md flat index + parts/*.md prose pages), section taxonomy, family-page pattern, table-padding discipline, directory layout. The foundation every other toolchain piece reads and writes.
category: foundation
---

> *Replaces the "Core Idea" + "Directory Layout" + "Example" sections of the
> retired IDEA-001 dossier.* The file format is the only thing every other
> piece of PartsLedger has to agree on — it deserves its own dossier so it
> can be honed independently of the skills, the camera path, or the
> CircuitSmith bridge.

## What this dossier owns

The **shape** and **invariants** of the on-disk inventory:

- `inventory/INVENTORY.md` — flat, sectioned index. Source of truth for
  *"what do I have and how many"*.
- `inventory/parts/<id>.md` — optional, hobbyist-friendly reference pages.
  Source of truth for *"what is this and how do I use it"*.
- The link between the two: the `Part` cell in `INVENTORY.md` becomes a
  Markdown link to the reference page once one exists, so the index doubles
  as a navigable book.

Anything under `inventory/.embeddings/` is a regenerable cache, not part of
the schema.

## Why Markdown, not SQL

- LLMs (Claude in particular) can read the whole inventory with a single
  `cat inventory/INVENTORY.md inventory/parts/*.md`. No ORM, no query
  language, no API wrapper.
- Git is the history. Every stock movement is a commit; `git log
  inventory/INVENTORY.md` shows arrivals and departures with full
  authorship.
- Tool diversity: Obsidian, VS Code, `grep`, the GitHub web UI all work
  unmodified.
- Diff-friendly: a humans-vs-LLM merge is a normal text merge, not a
  schema migration.

This bias toward Markdown-as-database is a project-wide stance; see the
[`feedback_markdown_native_storage`](file:///home/tobias/.claude/projects/-home-tobias-Dokumente-Projekte-PartsLedger/memory/feedback_markdown_native_storage.md)
memory and the broader rationale in
[`CLAUDE.md` § Inventory is the source of truth](../../../../CLAUDE.md#inventory-is-the-source-of-truth).

## `INVENTORY.md` — the flat index

A single Markdown file with one section per part class. Each section is a
GitHub-flavoured table with the columns:

```text
| Part | Qty | Description | Datasheet | Octopart | Notes |
```

Section taxonomy (current, open to revision):

- **MCUs** — programmable chips (PIC, AVR, STM32, ESP32 dev-boards).
- **ICs** — op-amps, comparators, logic, voltage refs, charge pumps.
- **Sensors** — HC-SR04, MPU-6050, DS18B20, photo-resistors, …
- **Modules** — pre-built boards (Blue Pill, WeMos D1, DRV8825, MAX7219).
- **Transistors** — BJTs, FETs, optos in their own bucket because the rest
  of the IC bucket would drown them.
- **Bulk / kits** — generic classes (assorted 1N4148, carbon-film resistor
  set). **Bullet entries, not table rows** — we don't catalogue individual
  values, only the kit's existence.

Row-level rules:

- Datasheet cell links to the manufacturer PDF when one exists; falls back
  to a generic family datasheet (TI/Microchip/ST) when the exact part
  number is generic enough.
- Octopart cell links to `octopart.com/search?q=<part>` (search URL, not a
  specific listing — listings rot).
- Notes cell is free-text and intentionally underspecified. Common uses:
  date-code, source ("from old PSU"), shares-page-with marker for family
  variants.
- Rows are inserted **alphabetically** within their section, with
  table-padding maintained so `markdownlint`'s MD060 stays clean.

Bulk/kits never get reference pages; they're inherently heterogeneous.

## `parts/<id>.md` — the optional reference page

Generated when a part earns one (typically by `/inventory-page` — see
[IDEA-005](idea-005-skill-path-today.md)). The page is **prose for a
hobbyist**, not a machine schema. Section template:

| Section | Purpose |
|---|---|
| Title + one-paragraph overview | What it is, what it's for, package |
| Datasheet + Octopart links | Reused from `INVENTORY.md`, not invented |
| ELI5 | One concrete metaphor (bucket brigade, one-note keyboard, …) |
| At a glance | Headline specs, hedged with `~`, `up to`, `typically` |
| Pinout (DIP-N, top view) | ASCII chip + table — walls must align |
| Sample circuit | Connection list, not ASCII schematic art |
| Variations *(optional)* | Other canonical modes (sine vs triangle, FSK, …) |
| Watch out for | Easy-to-miss constraints, silent-failure modes |
| Pairs naturally with | Real cross-references into the rest of the inventory |

Six real pages live in the tree today and serve as the working spec:
[`7660s.md`](../../../../inventory/parts/7660s.md),
[`pic12f675.md`](../../../../inventory/parts/pic12f675.md),
[`pic16f628.md`](../../../../inventory/parts/pic16f628.md),
[`tl082.md`](../../../../inventory/parts/tl082.md),
[`tl084.md`](../../../../inventory/parts/tl084.md),
[`xr2206cp.md`](../../../../inventory/parts/xr2206cp.md).

## Family pages

When two `INVENTORY.md` rows are revisions or marking variants of the
same chip — `PIC16F628` ↔ `PIC16F628A`, `NE555N` ↔ `NE555P` ↔ `LM555CM`,
`TL082CF` ↔ `TL082CP` — they **share one reference page**.

Rules:

- The page title carries both/all variants: `# PIC16F628 / PIC16F628A — …`.
- A `## Differences` section explains what changed between variants.
- Non-canonical rows in `INVENTORY.md` carry a *"Shares page with …"*
  note in the Notes cell.
- The page filename is the **canonical** member (the older or more
  generic one, e.g. `pic16f628.md`, not `pic16f628a.md`).

## Directory layout

```text
inventory/
├── INVENTORY.md                  ← flat index, source of truth for stock
├── parts/                        ← optional reference pages
│   ├── 7660s.md
│   ├── pic12f675.md
│   ├── pic16f628.md              ← family page (PIC16F628 + PIC16F628A)
│   ├── tl082.md                  ← family page (TL082CF + TL082CP)
│   ├── tl084.md
│   └── xr2206cp.md
└── .embeddings/                  ← future, camera path only — regenerable
    └── vectors.sqlite
```

## Example — an LM358N entry

A single row in `inventory/INVENTORY.md`:

```markdown
| LM358N | 1 | Dual op-amp, single-supply | [LM358](https://www.ti.com/lit/ds/symlink/lm358.pdf) | [search](https://octopart.com/search?q=LM358N) | |
```

If/when `/inventory-page LM358N` runs, a `parts/lm358n.md` is generated and
the Part cell becomes `[LM358N](parts/lm358n.md)`. The page is prose —
ELI5, At-a-glance specs, ASCII pinout, sample inverting-amplifier circuit,
"Watch out for" gotchas, and a "Pairs naturally with" pointer to the
[ICL7660S](../../../../inventory/parts/7660s.md) for ±V rails on a single
supply.

## Invariants enforced elsewhere

- `co-inventory-master-index/SKILL.md` is the runtime guard for
  `INVENTORY.md` edits (table-padding, section placement,
  link-into-parts/).
- `co-inventory-schema/SKILL.md` is the runtime guard for `parts/*.md`
  edits (frontmatter shape, pin-aliasing per IDEA-027, MD-as-source-of-
  truth, master-index linkage).
- The CircuitSmith vocabulary
  ([reference_idea027](file:///home/tobias/.claude/projects/-home-tobias-Dokumente-Projekte-PartsLedger/memory/reference_idea027.md))
  is the upstream for any future frontmatter additions.

## Open questions to hone

- **Machine-readable block in `parts/*.md`.** Today the pages are pure
  prose; CircuitSmith reads `INVENTORY.md` only ([IDEA-009](idea-009-circuitsmith-prefer-inventory-adapter.md)).
  Worth adding a closing fenced block (`yaml`/`toml`) for pin-aliasing,
  `vcc_min`, `pin_count`, etc.? If so, where does the boundary sit between
  prose and structured?
- **Schema versioning.** No `schema_version` field today. Do we need one
  before the camera path starts writing rows en masse?
- **Low-confidence-row marking.** The skill path hedges in prose; the
  camera path will produce rows the maker hasn't confirmed yet. A
  `Confirmed: no` column in Notes? A separate "to confirm" section at
  the top of `INVENTORY.md`?
- **Section taxonomy churn.** Adding a "Connectors" section? "Passives"?
  Where does an SD-card breakout land — Modules or Sensors?
- **Family-page boundary policy.** `LM358` vs `LM2904` — same op-amp
  topology, different industry-temp variant. Family or separate?
- **Filename convention.** Today: kebab-case base part, no manufacturer
  prefix. Survives manufacturer overlap (TI LM358 vs ST LM358)?

## Related

- [IDEA-005](idea-005-skill-path-today.md) — the today-tooling that writes
  the schema by hand.
- [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) — the camera-path
  brain whose output has to round-trip through this schema unchanged.
- [IDEA-009](idea-009-circuitsmith-prefer-inventory-adapter.md) — the
  CircuitSmith adapter that consumes the schema downstream.
- [IDEA-003](idea-003-external-inventory-tool-integration.md) — any
  external-tool integration round-trips against this schema.
