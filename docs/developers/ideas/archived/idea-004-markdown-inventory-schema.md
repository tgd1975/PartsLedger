---
id: IDEA-004
title: Markdown inventory schema
description: The two-file shape (INVENTORY.md flat index + parts/*.md prose pages), section taxonomy, family-page pattern, table-padding discipline, directory layout. The foundation every other toolchain piece reads and writes.
category: foundation
---

## Archive Reason

2026-05-14 — Promoted to EPIC-002 (markdown-inventory-schema), tasks TASK-014..TASK-018.

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

A single Markdown file with one section per part class — **by default**.
Once a bin grows past the point where one file is comfortable to scroll
or to feed to an LLM in one shot, the maker may split it into several
files (e.g. one per section: `inventory/mcus.md`, `inventory/ics.md`, …),
with `INVENTORY.md` reduced to a master index that links to the per-class
files. The schema of an individual table is identical either way; only
the file boundary moves.

**Whether to split is the maker's call.** Tooling may *suggest* a split
when the file crosses a practical threshold (row count, LLM context
budget, scroll length — exact trigger tuned at implementation), but it
never splits unprompted. A maker who prefers one file at 500 rows keeps
one file at 500 rows; the same maker-discoverability principle that
governs section taxonomy applies here.

Each section is a GitHub-flavoured table with the columns:

```text
| Part | Qty | Description | Datasheet | Octopart | Source | Notes |
```

Section taxonomy — **default offering, not a fixed schema**. The list
below is a sensible starting point; the schema enforces row and table
shape (columns, alphabetisation, family-page conventions), not which
sections exist or what they're called. A maker is free to add sections
("Connectors", "Passives"), rename them, or place a part in whichever
section they find most memorable — if an SD-card breakout lives more
naturally under **Modules** than **Sensors** in this bin, that's where
it goes; a bare BME280 in **Sensors** is equally fine. PartsLedger
doesn't have an opinion. The default list:

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
- Source cell records *who* added the row: `manual` (human-curated —
  `/inventory-add`, hand-edits) or `camera` (visual-recognition pipeline,
  [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md)). It is the
  *only* provenance axis the schema carries; there is no separate
  "confidence" or "to confirm" column — see the confidence policy
  below. The set is intentionally open: a future importer (e.g.
  InvenTree per [IDEA-003](idea-003-external-inventory-tool-integration.md))
  may add its own literal (`imported`) without a schema bump.
- Notes cell is free-text and intentionally underspecified. Common uses:
  date-code, physical origin ("from old PSU"), shares-page-with marker
  for family variants, **pin-compatible-with cross-references for parts
  that are interchangeable but not a family** (e.g. `LM358` ↔ `LM2904`;
  see [Family pages](#family-pages)), and one-line camera-path doubt
  hedges per the confidence policy below.
- Rows are inserted **alphabetically** within their section, with
  table-padding maintained so `markdownlint`'s MD060 stays clean.

**Confidence policy for the camera path.** A row is either confident
enough to commit (it lands like any other row), or it isn't (the
pipeline rescans / re-prompts until it is). There is no third
"added-but-unconfirmed" state — the maker never has to maintain a
"to confirm" backlog. When the pipeline is confident in the part but
wants to flag a specific doubt — e.g. *"silkscreen partially worn,
reads `LM35?`; pin-count + package consistent with LM358"* — it
commits the row and writes the doubt as a one-line hedge in the
Notes cell. The maker's eye on
Notes during normal use is the soft-confirmation path; no separate
review queue accumulates.

Bulk/kits never get reference pages; they're inherently heterogeneous.

## `parts/<id>.md` — the optional reference page

Generated when a part earns one (typically by `/inventory-page` — see
[IDEA-005](idea-005-skill-path-today.md)). The page is **prose for a
hobbyist**, not a machine schema — the audience is the maker who bought
an XR2206CP five years ago, has forgotten why, and wants a one-page
"what is this and how do I use it" answer.

**Filename convention.** The `<id>` is the part's MPN in lower-case
kebab-case (`pic16f628.md`, `tl082.md`, `xr2206cp.md`) — i.e. how the
maker would write the part name when searching their bin, with no
manufacturer prefix. Maker discoverability decides edge cases: if the
file is named the way the maker reads the silkscreen, they'll find
it. Manufacturer disambiguation (TI LM358 vs ST LM358) isn't a
maker-facing problem — to the maker, both are *"an LM358"* — so the
filename stays unqualified. The exception is family pages, which take
the canonical member's name (see [Family pages](#family-pages) below).

The page is *deliberately* not machine-readable. Structured electrical
data CircuitSmith needs (`vcc_min`, `vcc_max`, `pin_count`, `package`,
per-pin `side`/`type`/`direction`) lives in its own component-profile
library — duplicating it here would be lossy and would drag PartsLedger
into a schema-version dependency with CircuitSmith for no maker-facing
benefit. The one narrow integration concern — lifting **pin-aliasing**
out of the ASCII pinout — is owned downstream by
[CircuitSmith IDEA-010](https://github.com/tgd1975/CircuitSmith/blob/main/docs/developers/ideas/open/idea-010-prefer-inventory-adapter.md) and is
handled by parsing the existing prose pinout, not by adding a structured
block here.

Section template — **a recommended scaffold, not a fixed schema**.
Some sections apply to every part; others (Pinout, Sample circuit,
ELI5) shape themselves around the part class. The maker writes what
helps them remember; sections that don't earn their keep on a given
page are omitted, sections that do can be added.

| Section | Purpose | Adaptive? |
|---|---|---|
| Title + one-paragraph overview | What it is, what it's for, package | always |
| Datasheet + Octopart links | Reused from `INVENTORY.md`, not invented | always |
| ELI5 | One concrete metaphor (bucket brigade, one-note keyboard, …) | omit when obvious (a 1N4148 doesn't need an ELI5) |
| At a glance | Headline specs, hedged with `~`, `up to`, `typically` | always — *which* specs matter shifts by class |
| Pinout | ASCII / sketch / polarity-note — shape depends on the part (see worked examples below) | by part class |
| Sample circuit | Connection list, not ASCII schematic art — form varies by part | by part class |
| Variations | Other canonical modes (sine vs triangle, FSK, …) | optional — only if real |
| Watch out for | Easy-to-miss constraints, silent-failure modes | always |
| Pairs naturally with | Real cross-references into the rest of the inventory | always |

**Adapting the template — worked examples.** The six existing pages
in the tree are all 8–16 pin DIP ICs, which is why the *default*
shape of the Pinout entry is a DIP-N ASCII drawing. The template
flexes for other part classes — same maker-discoverability
principle as section taxonomy: write what helps the maker recognise
*their* part next time.

- **NPN transistor (2N3904, BC547, …).** TO-92 package, 3 pins
  (E, B, C). Pinout is a small TO-92 sketch — flat-side-facing-you
  view with `E B C` reading left to right — plus a 3-row pin
  table. No DIP ASCII, no "walls must align" rule. *Sample circuit*
  is a switch driver, LED driver, or common-emitter amp. *Watch
  out for* should flag that TO-92 pinout varies between
  manufacturers and parts — the silkscreen number is the only
  ground truth, and a 2N3904 from one source is *not*
  drop-in-equivalent to a BC547 from another despite both being
  "NPN small-signal".
- **2-pin parts (LEDs, signal diodes, electrolytic caps).** Pinout
  collapses to a one-line polarity note (*"long lead = anode; flat
  side of dome = cathode"*). ELI5 usually omitted. Sample circuit
  is one line (current-limit resistor for an LED, decoupling cap
  on a power rail).
- **Modules (Blue Pill, MAX7219 board).** Pinout is a header
  diagram naming each pin along each edge, not a DIP. *Watch out
  for* often carries level-shifting (3.3 V module driven from a 5
  V MCU) and power-input gotchas (USB vs VIN vs 3V3).
- **Connectors (USB-C, barrel jack).** Pinout is a *"V+ / V- /
  data"* note with a physical-orientation hint where it matters
  (inner-positive vs inner-negative on barrel jacks). ELI5 and
  Variations omitted.

Six real pages live in the tree today and serve as the working spec:
[`7660s.md`](../../../../inventory/parts/7660s.md),
[`pic12f675.md`](../../../../inventory/parts/pic12f675.md),
[`pic16f628.md`](../../../../inventory/parts/pic16f628.md),
[`tl082.md`](../../../../inventory/parts/tl082.md),
[`tl084.md`](../../../../inventory/parts/tl084.md),
[`xr2206cp.md`](../../../../inventory/parts/xr2206cp.md).

## Family pages

When two `INVENTORY.md` rows are revisions or marking variants of the
same chip — `PIC16F628` ↔ `PIC16F628A`, `NE555N` ↔ `NE555P`,
`TL082CF` ↔ `TL082CP` — they **share one reference page**.

Rules:

- The page title carries both/all variants: `# PIC16F628 / PIC16F628A — …`.
- A `## Differences` section explains what changed between variants.
- Non-canonical rows in `INVENTORY.md` carry a *"Shares page with …"*
  note in the Notes cell.
- The page filename is the **canonical** member (the older or more
  generic one, e.g. `pic16f628.md`, not `pic16f628a.md`).

**Family boundary — maker discoverability decides.** Two rows share a
page only when their MPNs share a recognisable base and differ by
suffix, revision marker, or packaging code — i.e. when a maker
glancing at both names instantly sees them as *"the same chip, just
a different version or package"*. Functional equivalence alone is
not enough; the maker has to be able to *see* the relationship in
the MPN itself, otherwise they'll search for the variant they own
and fail to find it. The inventory exists to help the maker locate
*their* part, not to canonicalise electronics history.

- ✅ `PIC16F628` ↔ `PIC16F628A` — revision suffix.
- ✅ `NE555N` ↔ `NE555P` — packaging suffix.
- ✅ `TL082CF` ↔ `TL082CP` — packaging suffix.
- ❌ `NE555N` ↔ `LM555CM` — electrically compatible, but different
  manufacturer prefix and no shared MPN stem; a maker who bought an
  LM555CM won't think to look under NE555.
- ❌ `LM358` ↔ `LM2904` — industrial-temperature variant of the same
  op-amp, but the MPNs share no stem. Separate rows, separate pages.

**Cross-reference pin-compatible non-family parts in Notes.** When two
rows fail the family test but the maker would still treat them as
interchangeable on the bench, each row carries a one-line breadcrumb
in its Notes cell — so the maker holding an LM2904 and wondering *"is
there a chip I'd treat the same way?"* finds the answer without having
to memorise op-amp lore:

```text
| LM358  | … | … | … | … | manual | Pin-compatible with LM2904 (industrial-temp variant) |
| LM2904 | … | … | … | … | manual | Pin-compatible with LM358 (commercial-temp variant)  |
```

For ✅ family cases the *"Shares page with …"* note already plays
this role; the cross-reference rule generalises it to "not a family
but interchangeable".

**The breadcrumb is advisory, not guard-enforced.** The runtime
guard ([co-inventory-master-index](../../../../.claude/skills/co-inventory-master-index/SKILL.md))
does not parse Notes cell content, so an asymmetric edit (LM358's
Notes mentions LM2904 but LM2904's doesn't mention LM358) is *not*
a lint error. A skill that adds one breadcrumb should add the
reciprocal in the same edit; a hand-edit that drops the reciprocal
is a small drift, not corruption. Bidirectional Notes lint would
be too brittle (Notes is free-text and intentionally
underspecified) and would mostly false-positive on phrasing drift.

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
| LM358N | 1 | Dual op-amp, single-supply | [LM358](https://www.ti.com/lit/ds/symlink/lm358.pdf) | [search](https://octopart.com/search?q=LM358N) | manual | |
```

If/when `/inventory-page LM358N` runs, a `parts/lm358n.md` is generated and
the Part cell becomes `[LM358N](parts/lm358n.md)`. The page is prose —
ELI5, At-a-glance specs, ASCII pinout, sample inverting-amplifier circuit,
"Watch out for" gotchas, and a "Pairs naturally with" pointer to the
[ICL7660S](../../../../inventory/parts/7660s.md) for ±V rails on a single
supply.

## `INVENTORY.md` writer contract

Three call-sites in the codebase will mutate `INVENTORY.md`
through Python code once the camera path lands:

- [IDEA-005](idea-005-skill-path-today.md) — `/inventory-add`
  (skill path, today via LLM prompt; will share the same
  underlying writer once factored out).
- [IDEA-007 Stage 4](idea-007-visual-recognition-dinov2-vlm.md#stage-4--pipeline-glue--branching)
  — silent qty++ on every cache hit, new-row insert on every
  first sighting.
- [IDEA-008 Stage 4](idea-008-metadata-enrichment.md#stage-4--standalone-enrichment-orchestrator--writer-integration)
  — extend rows with enriched cells once Nexar / family-datasheet
  metadata is in hand.

All three call **one** function. The function lives at
`src/partsledger/inventory/writer.py` once the
[IDEA-014](idea-014-project-setup-review-vs-circuitsmith.md)
package layout lands; until then it is whatever the first
implementer scaffolds, but the *contract* below is the same.
This section exists so the contract is pinned **before** the
first implementer runs into it.

### Signature

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

- **`part_id`** — the MPN as the maker reads it from the
  silkscreen (e.g. `LM358N`). Case-sensitive; the writer does
  not normalise. Used to locate an existing row and as the
  literal Part-cell text on insert.
- **`qty_delta`** — signed integer. `+N` on capture / add,
  `-N` on undo. The writer does not enforce `qty >= 0` —
  negative final qty is a maker-data smell the next eyeball
  will catch; the writer's job is to apply the delta atomically,
  not to second-guess it.
- **`source`** — required keyword. Per
  [§ `INVENTORY.md` — the flat index](#inventorymd--the-flat-index)
  Source-column policy: any non-empty lowercase token
  (`manual`, `camera`, `imported`, …). Shape-validated by the
  writer (lowercase, non-empty, no whitespace); semantic
  allow-list lives in the runtime-guard skill, not here.
- **`section`** — optional. When omitted, the writer
  enumerates existing `## …` headings and picks one per the
  *maker-choice section taxonomy* rule above; when no heading
  yet exists for the part class, the writer raises so the
  caller can decide whether to fall back to a default H2.
  Section-mapping decisions are caller-owned; the writer
  applies them.
- **`cells`** — optional dict of additional column values
  (`{"Description": "Dual op-amp", "Datasheet": "[LM358](…)",
  "Octopart": "[search](…)", "Notes": ""}`). On insert, missing
  cells default to empty strings; on qty-bump, supplied cells
  **overwrite** the existing values (the enrichment caller
  uses this to fill in cells that were placeholder on the
  initial camera-path write).

`WriteResult` carries the disposition (`inserted`, `bumped`,
`metadata_updated`, `no_op`), the post-write qty, and the
section the row landed in — enough for callers to drive a
viewfinder confirmation flash or a skill-path log line.

### Idempotency

The writer is keyed by `part_id`. Calling it twice with the
same args produces the same end state as calling it once,
except for `qty_delta` which accumulates by design. There is
no de-dup on the basis of *"the same camera frame already
landed here"* — that's the caller's problem (the undo journal
in [IDEA-007 Stage 5](idea-007-visual-recognition-dinov2-vlm.md#stage-5--undo-journal--undo_last)
is how the camera path handles double-fires).

### Atomicity

One call → one file write. The writer reads `INVENTORY.md`,
mutates the in-memory representation, re-pads the affected
table per the markdownlint MD060 invariant, and writes the
whole file back via the atomic-rename pattern (temp file in
the same directory, `os.replace`). A crash mid-write leaves
the file in either the pre-call or post-call state, never
half-written.

Two concurrent callers are not expected at hobbyist scale
(the camera path is one-capture-at-a-time per
[IDEA-006](idea-006-usb-camera-capture.md)), but the
atomic-rename pattern also makes them safe in the sense
that one's write wins cleanly rather than both corrupting
the file.

### Pre-flush invariant check

Before flushing the mutated representation, the writer runs
the same lint pass that `scripts/lint_inventory.py` (per
[Gap 7](#open-questions-to-hone) below) runs as a pre-commit
hook. A failure raises rather than writes a malformed file.
This is what makes the writer safe to call from code paths
where no Claude codeowner skill is in the loop — see
[Gap 7](#open-questions-to-hone) for the broader rationale.

### Error contract

The writer raises on:

- **Malformed pre-state.** `INVENTORY.md` doesn't parse as the
  documented section / table shape. Caller sees the parse error
  with a line number; the writer does not auto-repair.
- **Section unresolvable.** `section=None` and the file has no
  H2 headings yet, or `section="Foo"` but no `## Foo` exists.
  Caller decides whether to create the heading first.
- **Source-shape violation.** `source` empty, contains
  whitespace, or contains uppercase. Same shape rule the
  runtime-guard skill enforces.
- **Lint failure on the post-state.** Pre-flush check rejected
  the mutated representation. Includes the lint diagnostic.

The writer does **not** raise on a negative final qty, on an
unknown section that nonetheless has a matching H2 in the
file (caller's section taxonomy is sovereign), or on a
`cells` dict with extra keys (silently ignored — forward-
compat for future columns).

### Single implementation, three callers

The contract above is one function in one module. The two
skills (`/inventory-add`, the camera-path writer hook) and the
enrichment integrator (`enrich()` in IDEA-008 Stage 4) all
import it. There is **no** lookalike — the failure mode the
gap-1 prose warns against ("three dossiers point at each
other") is avoided by the rule *the first implementer files
the writer at the canonical path; subsequent callers wire to
it*. If a caller's needs grow beyond what `upsert_row` covers
(e.g. bulk-row backfill, split-file mode from
[Stage 3](#stage-3--splitting-support-deferred-until-a-maker-needs-it)),
the writer module grows a sibling function; the existing
signature stays stable.

## Invariants enforced elsewhere

- `co-inventory-master-index/SKILL.md` is the runtime guard for
  `INVENTORY.md` edits **made by Claude** (table-padding, section
  placement, link-into-parts/). It does **not** fire when the
  writer above runs from Python — that case is covered by the
  pre-flush lint per [§ Pre-flush invariant check](#pre-flush-invariant-check),
  and by the standalone `scripts/lint_inventory.py` pre-commit
  hook discussed in [Open questions](#open-questions-to-hone).
- `co-inventory-schema/SKILL.md` is the runtime guard for `parts/*.md`
  edits (frontmatter shape, pin-aliasing per IDEA-027, MD-as-source-of-
  truth, master-index linkage).
- The CircuitSmith vocabulary
  ([reference_idea027](file:///home/tobias/.claude/projects/-home-tobias-Dokumente-Projekte-PartsLedger/memory/reference_idea027.md))
  is the upstream for any future frontmatter additions.

## Execution plan

The IDEA-004 schema additions land in two stages against `main`,
plus an optional third stage if/when a maker chooses to split the
inventory. Each stage is one squashed PR (per the CLAUDE.md
*Branch merges — squash, not fast-forward* rule). The camera path
([IDEA-007](idea-007-visual-recognition-dinov2-vlm.md)) and the
CircuitSmith adapter
([CircuitSmith IDEA-010](https://github.com/tgd1975/CircuitSmith/blob/main/docs/developers/ideas/open/idea-010-prefer-inventory-adapter.md))
are separate efforts and not in scope here.

### Stage 1 — `Source` column + section flexibility

**Goal.** Land the new column and the maker-choice section taxonomy
together. The runtime guard, the row format, and the row-writing
skill must agree on the new shape before any of it ships, so all
of this travels in one squash.

**Changes:**

1. **`inventory/INVENTORY.md`** — add the `Source` column to every
   section's table header; backfill `manual` on every existing row;
   restore table padding so `markdownlint`'s MD060 stays clean.
   At current scale (a handful of rows) this is a one-shot hand
   edit — no script needed. If the file has grown by the time this
   ships, a five-line `awk` / `sed` pipeline suffices; the
   complexity threshold is "more rows than I want to retype",
   not a specific count.
2. **[`co-inventory-master-index/SKILL.md`](../../../../.claude/skills/co-inventory-master-index/SKILL.md)**
   — extend the runtime guard:
   - Recognise the seven-column header
     (`Part | Qty | Description | Datasheet | Octopart | Source | Notes`).
   - Validate `Source` as a non-empty lowercase token. **No
     allow-list** — accept any value matching the lowercase-token
     shape silently. The literal set is intentionally open per
     the row-level rules above, so a future `imported` from
     [IDEA-003](idea-003-external-inventory-tool-integration.md)
     lands without a guard change and without nagging warnings.
     Shape violations (empty cell, whitespace, mixed-case,
     punctuation) error as usual.
   - Stop hard-coding section names. Enumerate `## …` headings
     from the file at lint time; require each row to live under
     *some* H2, not under a specific one.
3. **`/inventory-add` skill** — set `Source: manual` on every row it
   writes. Section placement falls back to the default list only
   when no `## …` heading exists yet; otherwise propose from
   sections already present.
4. **`CHANGELOG.md`** — one bullet under `[Unreleased] / ### Schema`
   naming both schema changes, with the task reference. Rides in
   the same squash per CLAUDE.md § *CHANGELOG updates ride with the
   merge*.

**Validation:**

- The pre-edit `INVENTORY.md` re-validates clean after the backfill.
- A test row added via `/inventory-add` carries `Source: manual`
  and lands under an existing section.
- Renaming a section in `INVENTORY.md` (e.g. `## ICs` → `## Linear
  ICs`) and re-running the guard does **not** error.

**Dependencies.** None — this is the foundation stage.

### Stage 2 — Parts-page template adaptivity

**Goal.** Teach `/inventory-page` to produce part-class-appropriate
Pinout / Sample-circuit / ELI5 sections instead of always defaulting
to a DIP-N ASCII layout, per the worked examples in
[§ `parts/<id>.md`](#partsidmd--the-optional-reference-page) above.

**Changes:**

1. **`/inventory-page` skill** — extend the prompt to reference the
   worked examples (TO-92 for 3-pin small-signal, polarity note
   for 2-pin parts, header diagram for modules, V+/V- note for
   connectors). The skill stays LLM-driven; this is a prompt
   update, not new code.
2. **[`co-inventory-schema/SKILL.md`](../../../../.claude/skills/co-inventory-schema/SKILL.md)**
   — no change required. The schema-side guard enforces
   frontmatter and master-index linkage, not body section names.
3. **`CHANGELOG.md`** — one bullet under `[Unreleased] / ### Tooling`.

**Validation:**

- `/inventory-page 2N3904` produces a TO-92 sketch + 3-row pin
  table, *not* a DIP-N ASCII; *Watch out for* flags the
  manufacturer-varying-pinout gotcha named in IDEA-004's NPN
  example.
- `/inventory-page 1N4148` collapses Pinout to a one-line
  polarity note and omits ELI5.
- Re-running `/inventory-page` on an existing DIP page (e.g.
  `tl082.md`) produces the same section list and Pinout shape
  (DIP-N ASCII top-view) as the existing file — same-class parts
  keep the same template. Body prose may differ where the LLM
  rephrases; that's expected and not a regression.

**Dependencies.** Stage 1 (any new page authored by this skill
also writes a row into `INVENTORY.md`; the row needs the new
`Source` column to exist).

### Stage 3 — Splitting support (deferred until a maker needs it)

**Goal.** Wire up multi-file inventory once a real bin reaches the
size where one file is uncomfortable. Not a speculative ship — only
land when a maker actually accepts the suggestion or asks for it.

**Changes:**

1. **Glob-by-convention reader** in every tool that reads
   `INVENTORY.md` directly today. Glob: `inventory/*.md` minus the
   master file. Front-matter `parts:` manifest reserved as a
   fallback only if a maker has unrelated `.md` files in
   `inventory/`.
2. **`co-inventory-master-index` extension** — when the master
   file contains link-to-per-section-file rows rather than table
   rows, validate the split shape: per-section files share the
   row schema; the master lists all of them; no row appears
   twice across files.
3. **`/inventory-add` suggestion trigger** — nudges the maker
   when the master file passes a practical threshold. Initial
   proposal: 200 rows *or* 30 KB, whichever first; refine on
   real data. Suggestion is advisory; the maker has the final
   call.
   - **Decline-stickiness.** A "no thanks" persists via a single
     HTML comment marker the skill writes into `INVENTORY.md`
     directly below the H1: `<!-- pl: split-suggestion-declined -->`.
     The trigger reads the file before nagging; if the marker is
     present, it stays silent. Marker storage matches the project's
     MD-as-source-of-truth stance (no sidecar files, no hidden
     state). A maker who later wants the suggestion to fire again
     deletes the line by hand; that's the only re-arm path, by
     design.
4. **Documentation** — this dossier's
   "[INVENTORY.md — the flat index](#inventorymd--the-flat-index)"
   section updates to point at the implementation; no design
   changes.

**Validation:**

- A split test bin (three section files + master) round-trips
  through `co-inventory-master-index` cleanly.
- The CircuitSmith adapter, once it exists per
  [CircuitSmith IDEA-010](https://github.com/tgd1975/CircuitSmith/blob/main/docs/developers/ideas/open/idea-010-prefer-inventory-adapter.md),
  reads the split shape correctly via the glob mechanism.
- Threshold-hit fires the suggestion exactly once; a decline
  silences it for that bin.

**Dependencies.** Stage 1.

### Out of scope for this rollout

- The **camera path** ([IDEA-007](idea-007-visual-recognition-dinov2-vlm.md))
  consumes the `Source: camera` literal once it exists, but the
  camera-path implementation is its own epic — not driven by
  IDEA-004.
- The **CircuitSmith adapter**
  ([CircuitSmith IDEA-010](https://github.com/tgd1975/CircuitSmith/blob/main/docs/developers/ideas/open/idea-010-prefer-inventory-adapter.md))
  gains a new column it can ignore. No PartsLedger-side work
  needed for it.

## Out of scope (decided)

Items that have been considered and explicitly rejected, recorded here
so they don't get re-litigated every time someone reads the dossier.
Some entries below restate a resolution that is *also* described in
the live spec sections above (e.g. confidence policy, family-page
boundary, filename convention) — those are intentional cross-links,
not divergent specs. The live spec is the source of truth; this
section records the alternatives considered against it and the
rationale for rejecting them.

- **Machine-readable block in `parts/*.md`.** The reference pages stay
  prose-only. See the rationale in the
  [`parts/<id>.md` section above](#partsidmd--the-optional-reference-page)
  — structured electrical data CircuitSmith needs lives in its own
  `components/*.py` library, and the one narrow integration point
  (pin-aliasing) is owned by [CircuitSmith IDEA-010](https://github.com/tgd1975/CircuitSmith/blob/main/docs/developers/ideas/open/idea-010-prefer-inventory-adapter.md).
- **`schema_version` field.** Not added. The schema is itself a
  versioned document (this dossier, tracked in git); a separate integer
  tag would duplicate that. Consumers like CircuitSmith are better
  served by **shape detection** — *"couldn't find a Datasheet column"*
  tells the user what's wrong; `schema_version: 2, expected 1` only
  tells them something is wrong. At maker scale (~50–200 parts in one
  bin) a breaking change is an afternoon's hand-edit or a one-off
  `sed`; there's no fleet of installs to coordinate. Distinguishing
  camera-written rows from hand-curated ones — the case sometimes
  raised in favour of versioning — is per-row **provenance** instead,
  carried by the `Source: manual | camera` column added above.
- **Low-confidence-row marking.** Not added as a separate column or a
  "to confirm" section. The camera path either commits a row (full
  confidence) or doesn't (rescan / re-prompt until it does) — there
  is no third "added but unconfirmed" state. Specific doubts the
  pipeline wants to flag go in Notes as a one-line hedge
  (*"detected as LM359, likely LM358"*); the maker's eye on Notes
  during normal use does the soft-confirmation. Provenance ("who
  wrote this row") is carried by the `Source` column above. The
  maker never has to maintain a review queue, which would
  inevitably rot.
- **Normative section taxonomy.** Section names and contents are
  maker-choice, not schema. The default list in
  "[INVENTORY.md — the flat index](#inventorymd--the-flat-index)"
  is the starting point PartsLedger offers; the schema enforces
  row/table shape only. This closes the previously-open *"where does
  an SD-card breakout land — Modules or Sensors?"* question — wherever
  the maker decides; both are defensible, and the schema doesn't
  pick a fight.
- **Family-page boundary policy.** Resolved by **maker
  discoverability** (worked examples in
  [Family pages](#family-pages) above): two rows share a page only
  when their MPNs share a recognisable base and differ by
  suffix/revision/packaging code. `LM358` vs `LM2904` are *not* a
  family — same op-amp topology, but the MPNs share no stem and a
  maker who bought one won't find the other. Same logic retires
  `NE555N`/`LM555CM` as a family.
- **Filename convention.** Resolved: lower-case kebab-case MPN, no
  manufacturer prefix (see
  [`parts/<id>.md`](#partsidmd--the-optional-reference-page) above).
  Filename matches how the maker reads the chip's silkscreen.
  Manufacturer overlap (TI LM358 vs ST LM358) isn't a maker-facing
  problem and doesn't justify prefixing.
- **Splitting `INVENTORY.md` across files.** Resolved by **maker
  discretion**: a single flat file is the default, but a maker may
  split into per-section files
  (`inventory/mcus.md`, `inventory/ics.md`, …) with `INVENTORY.md`
  reduced to a master index. See
  "[INVENTORY.md — the flat index](#inventorymd--the-flat-index)"
  above. Tooling may *suggest* a split when the file grows past a
  practical threshold, but never splits unprompted. Implementation
  details (discovery, runtime guard, suggestion trigger) are work
  items under "[Execution plan](#execution-plan)" — not open design
  questions.

## Open questions to hone

- **Schema-invariant enforcement against code-driven writers.**
  The two codeowner skills listed under
  [§ Invariants enforced elsewhere](#invariants-enforced-elsewhere)
  fire when **Claude** is the editor. The camera-path writer
  ([§ `INVENTORY.md` writer contract](#inventorymd-writer-contract)
  above) is Python with no Claude in the loop — the codeowner
  skills are silent on that path. Schema invariants (table padding,
  alphabetical row order, hedge language in Notes, Source-column
  shape, link-into-parts/ correctness) need a **mechanical**
  enforcement layer that doesn't depend on the editor being Claude.

  Candidate answer: a `scripts/lint_inventory.py` script that the
  Python writer calls as its
  [pre-flush invariant check](#pre-flush-invariant-check) and that
  also rides as a pre-commit hook (same shape as `scripts/housekeep.py`
  and the IDEA-005 hedge-language lint). One implementation, two
  invocation contexts. The script's scope is the schema-shape
  invariants enumerated in this dossier; out of scope is anything
  free-text in Notes that the schema deliberately doesn't constrain.

  Sequencing: the lint script needs to exist before
  [IDEA-007 Stage 4](idea-007-visual-recognition-dinov2-vlm.md#stage-4--pipeline-glue--branching)
  can call it from the pre-flush hook. Lands as its own piece of
  work — likely a `scripts/lint_inventory.py` task spawned alongside
  the writer-module task in IDEA-014's Phase 0b layout, or under
  IDEA-007 if the writer module lands there first.

## Related

- [IDEA-005](idea-005-skill-path-today.md) — the today-tooling that writes
  the schema by hand.
- [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) — the camera-path
  brain whose output has to round-trip through this schema unchanged.
- [CircuitSmith IDEA-010](https://github.com/tgd1975/CircuitSmith/blob/main/docs/developers/ideas/open/idea-010-prefer-inventory-adapter.md) — the
  CircuitSmith adapter that consumes the schema downstream.
- [IDEA-003](idea-003-external-inventory-tool-integration.md) — any
  external-tool integration round-trips against this schema.
