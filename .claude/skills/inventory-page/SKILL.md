---
name: inventory-page
description: Generate a one-page "what is this / how do I use it" reference for a component already in inventory/INVENTORY.md, and link the part name in the inventory table to the new page. Pages live in inventory/parts/.
---

# inventory-page

The user invokes this as `/inventory-page <part-id>` (one part per invocation).

Goal: produce a concise, hobbyist-friendly reference page for a part already in
`inventory/INVENTORY.md`, and link the inventory row's Part cell to the new page
so the inventory becomes a navigable index.

## Where pages live

- Path: `inventory/parts/<part-id-lowercased>.md`.
- Filename rule: lowercase the part ID, keep alphanumerics, strip slashes and
  other punctuation. Examples: `PIC12F675` → `pic12f675.md`,
  `7660S` → `7660s.md`, `74HC595N` → `74hc595n.md`.

## Preconditions

- The part must already exist as a row in `inventory/INVENTORY.md`. If not, stop
  and tell the user to add it first via `/inventory-add`.
- If a page already exists at the target path, **do not overwrite blindly**.
  Tell the user the page exists and ask whether to regenerate (offer to show
  the existing page first).
- This skill is for individually-catalogued parts (chips, MCUs, modules). It is
  not the right tool for bulk / kits entries; those don't get pages.

## Family pages (multiple variants → one page)

When the user has multiple rows in `INVENTORY.md` that are revisions or marking
variants of essentially the same chip (e.g. `PIC16F628A` and `PIC16F628-20I/P`,
or `NE555N` / `NE555P` / `LM555CM`), prefer **one family page** over multiple
near-duplicate pages.

- Name the page after the family without the suffix: `pic16f628.md`,
  `ne555.md`. Two-line title: `# PIC16F628 / PIC16F628A — …`.
- Both/all inventory rows link to the same page; add a short Notes-cell hint
  like *"Shares page with PIC16F628A (family)"* on the non-canonical rows.
- List both/all datasheets and both/all Octopart links in the page header.
- Add a `## Differences: X vs. Y` section near the bottom (after Variations,
  before Watch out for) with a comparison table — what changed between
  revisions, practical implications for hobbyist use.
- The Pinout / Sample circuit / Programming sections cover the shared
  behaviour. Note variant-specific quirks inline where they matter (e.g.
  "pre-A needs an external crystal").

Suggest a family page when you see two or more inventory rows whose
descriptions are obviously of the same chip with a revision/marking
difference. Ask the user before merging if it's borderline.

**Proactive sibling check (IDEA-005 § Stage 2).** Before drafting a
fresh page, call the mechanical heuristic against the parts/
directory:

```python
from partsledger.inventory.family import find_sibling_pages
matches = find_sibling_pages(new_mpn, "inventory/parts")
```

When `matches` is non-empty, propose *"join the existing
`<sibling>.md` as a family page"* rather than creating a new file.
Advisory only — the maker decides. The heuristic implements the
length-gate + suffix-only-divergence rules from IDEA-005; if a
candidate is a real family member the regex misses, the maker can
still ask for the merge by hand.

## Page structure

Use these sections in order. **Section list and shape are
part-class-adaptive** — pick the variant that fits the part. The four
classes the skill recognises are:

- **DIP-N IC** (the default — chips like TL082, NE555, PIC16F628,
  XR2206). Full DIP ASCII pinout + pin table; full ELI5.
- **NPN/PNP transistor** (TO-92, TO-126, TO-220 leaded transistors —
  2N3904, BC547, KT3102, …). TO-92 sketch + 3-row pin table; no DIP
  ASCII; manufacturer-varying-pinout flag in *Watch out for*.
- **2-pin part** (LEDs, signal diodes, electrolytic caps — 1N4148,
  1N5404, generic LEDs). Pinout collapses to a one-line polarity
  note. ELI5 typically omitted. Sample circuit one line.
- **Module / breakout** (STM32 Blue Pill, MAX7219 board, sensor
  breakouts). Pinout is a header diagram naming each pin along each
  edge of the board, not a DIP ASCII. Level-shifting and power-input
  gotchas typically flagged in *Watch out for*.
- **Connector** (USB-C, barrel jack, JST-XH). Pinout is a V+ / V- /
  data note with a physical-orientation hint where it matters.

When in doubt, pick from the INVENTORY.md section the part lives in:
ICs / MCUs → DIP-N; Transistors → transistor; Modules / breakouts →
module; Bulk / kits → Loose / discrete → 2-pin or connector,
depending on the part.

Sections in order — apply the variant from your class pick. Skip
sections that don't apply.

1. **Title** — `# <CANONICAL-ID> — <one-phrase function>`. Use the canonical
   manufacturer name (`ICL7660S`) in the title even when the inventory uses a
   shorter form (`7660S`); the reader should recognise both.

2. **One-paragraph overview** — what the part is, what it's most often used
   for, package and pin count. Two to four sentences.

3. **Datasheet + Octopart links** — two adjacent lines:
   - `Datasheet: [<short-name>](<url>)` — reuse the URL from `INVENTORY.md`; do
     not invent a different one.
   - `Octopart: [<canonical-id>](https://octopart.com/search?q=<canonical-id>)`
     — a search URL built from the canonical part ID in the page title.
     Octopart surfaces production status, current pricing, and stock across
     distributors. The search URL works without knowing the direct product-page
     slug, so it's the safe default. Use the canonical ID (e.g. `ICL7660S`),
     not the inventory shorthand (`7660S`), so the search lands on the right
     family page.

4. **ELI5** — plain-language explanation built around one concrete metaphor
   (bucket brigade, one-note keyboard, tiny computer-on-a-chip). Two to four
   short paragraphs. Optionally followed by a "what it can do / what it can't"
   bullet pair. The ELI5 is allowed to be more confident than the technical
   sections — metaphors are explicitly approximate.
   - **2-pin parts** (diodes, LEDs, caps): omit this section unless
     the part has a non-obvious behaviour worth explaining. A 1N4148
     does not need an ELI5; a Zener at a non-standard breakdown
     voltage might.

5. **At a glance** — bulleted list of headline specs: pin count, supply range,
   output current / frequency range / memory, and anything notable. Hedge
   numbers with `~`, `up to`, `typically`.

6. **Pinout** — shape depends on class:

   - **DIP-N IC** — `### Pinout (DIP-N, top view)`. ASCII diagram
     followed by a markdown table.
     - Use a **`text`-fenced** code block for the ASCII (markdown
       lint requires a language).
     - **Pad pin labels so the chip walls (`│`) align vertically.**
       This is the most common first-draft defect — count columns
       before writing.
     - Pin numbers sit just inside the wall: `label N│   │N label`.
       Use a U-notch at the top: `┌──U──┐`.
     - Table columns: `Pin | Name | Use`. For multi-function pins,
       list roles separated by `/`. Bold any role that is critical
       or surprising (e.g. **input-only**, **ICSPDAT**).

   - **NPN/PNP transistor** — `### Pinout (TO-92, flat side facing
     you)`. Small TO-92 sketch followed by a 3-row pin table.
     - The sketch is a **`text`-fenced** code block showing the flat
       side with the leads pointing down and the labels `E B C` (or
       the part-specific order) reading left to right under the
       leads.
     - Table columns: `Pin | Name | Use`. Three rows for a BJT
       (Emitter, Base, Collector); JFETs / MOSFETs use the
       Source / Gate / Drain naming.
     - **No DIP ASCII** and no walls-must-align rule.
     - In *Watch out for*, flag that **TO-92 pinout varies between
       manufacturers** (e.g. 2N3904 EBC vs BC547 CBE vs BC547 EBC
       depending on the maker) — always cross-check against the
       datasheet for the *specific* marking before wiring up.

   - **2-pin part** (diodes, LEDs, electrolytic caps) —
     `### Polarity`. **One-line note** describing which lead is the
     cathode / anode (or +/-) and how to identify it physically
     (banded end, shorter lead, marked stripe on the can). No
     ASCII, no table.

   - **Module / breakout** — `### Pinout (header diagram)`. A
     **`text`-fenced** sketch that names each pin along each edge of
     the board, in the order they physically appear. Optionally a
     supporting table for the less-obvious pins.

   - **Connector** — `### Pinout (V+ / V- / data note)`. A short
     note listing each contact with its role (V+, V-, D+, D-,
     CC1/CC2 for USB-C; tip / ring / sleeve for a barrel jack).
     Include a physical-orientation hint where it matters
     (USB-C is reversible; a barrel jack is not).

7. **Sample circuit** — heading: `## Sample circuit — <what it does>`. Body is
   a **connection list**, not ASCII schematic art. Be explicit about pin
   numbers, component values, polarity where it matters, and which pins to
   leave open. End with a one-line note on what the user should see at the
   output.
   - **2-pin parts**: this section collapses to **one line** —
     e.g. *"In series with a 330 Ω resistor across a 5 V supply, banded
     end to ground, the LED lights."*

8. **Variations** *(optional)* — short bullets describing other common modes
   (e.g. triangle vs sine output, FSK, sweep, external crystal). Include only
   if the part has more than one canonical use; skip for single-purpose parts.

9. **Watch out for** — bullets covering: easy-to-miss constraints, datasheet
   gotchas, silent-failure modes, configuration that matters. Start each
   bullet with a bolded short tag. Class-specific flags worth carrying
   by default:
   - **Transistor:** *"Pinout varies between manufacturers"* — the
     same generic part (e.g. BC547) is shipped with different lead
     orders by different makers; always check the datasheet for the
     *specific* marking before wiring up.
   - **Module:** level-shifting requirements (3.3 V vs 5 V logic),
     power-input gotchas (VIN regulator vs 3V3 direct), and any
     onboard pull-ups / pull-downs that surprise.

10. **Pairs naturally with** — bullets relating this part to other items in
    `inventory/INVENTORY.md`. Use real part numbers from the inventory. Be
    honest when the pairing is weak — say so rather than inventing a connection.

## What to do

1. **Verify the part is in INVENTORY.md.** Read the file, find the row, capture
   the canonical ID, the description, and the datasheet URL. If absent: stop
   and tell the user to run `/inventory-add` first.

2. **Identify the canonical form.** The inventory may use a shortened or
   marking-variant ID; the page title should use the manufacturer's canonical
   form when that is the more recognised name.

3. **Pick the part class** from the five above (DIP-N IC, transistor,
   2-pin, module, connector). The INVENTORY.md section the part lives
   in is the strongest signal; the description is the next one. If
   the class is genuinely ambiguous (e.g. an optocoupler in a DIP
   package), default to the variant that matches the package most
   closely — a DIP-8 optocoupler gets the DIP ASCII even though its
   internals are a phototransistor pair.

4. **Draft the page** following the structure, applying the
   class-specific variant for the Pinout / ELI5 / Sample circuit /
   Watch out for sections. Apply sincere language: hedge specs,
   avoid `must / always / never` as rhetorical emphasis, mark
   estimates as estimates. The datasheet is authoritative; this
   page is a curated entry point.

5. **For DIP-N parts, verify ASCII pinout alignment** before
   writing. Count characters from the left edge to each `│` and
   confirm they match across all lines of the chip body. This is
   the single most common defect for DIP pages; the other classes
   are not subject to this rule.

6. **Write the page file** to `inventory/parts/<id-lower>.md`.

7. **Update `inventory/INVENTORY.md`** to link the Part column for that row:
   - Replace the bare part name with `[<part-name>](parts/<id-lower>.md)`.
   - **Repad the entire affected table.** Markdownlint enforces the "aligned"
     table style (rule MD060) — leaving the new linked row wider than its
     neighbours produces warnings. Recompute column widths from the max content
     across all rows and rewrite every row to match. The cleanest way is to
     generate the new table with a small Python snippet that left-justifies each
     cell to the max width of its column (`str.ljust`) and joins with `' | '`.
   - Leave the Datasheet and Octopart columns alone; those still point at the
     manufacturer PDF and the Octopart search respectively.

8. **Report**: page path, sections included, sections skipped (with reason),
   and that the inventory row was linked.

## What this skill does *not* do

- Does not commit. The user commits when ready.
- Does not generate pages for parts not in `INVENTORY.md`.
- Does not invent specs, pinouts, or behaviours not in the datasheet. If a
  detail isn't known with confidence, mark it as "verify against datasheet"
  in the page rather than guessing.
- Does not draw ASCII schematic art for the sample circuit — connection lists
  are clearer than mangled ASCII.
- Does not overwrite existing pages without asking.

## Sincere-language note

The page synthesises the datasheet; it does not replace it. Anywhere a number,
a pin behaviour, or a config recommendation could be wrong, hedge or qualify.
The ELI5 section may use confident metaphors (the metaphor itself signals
"approximate"), but the technical sections should match the calibrated tone of
the rest of the repo.
