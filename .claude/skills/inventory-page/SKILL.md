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

## Page structure

Use these sections in order. Skip ones that don't apply.

1. **Title** — `# <CANONICAL-ID> — <one-phrase function>`. Use the canonical
   manufacturer name (`ICL7660S`) in the title even when the inventory uses a
   shorter form (`7660S`); the reader should recognise both.

2. **One-paragraph overview** — what the chip is, what it's most often used
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

5. **At a glance** — bulleted list of headline specs: pin count, supply range,
   output current / frequency range / memory, and anything notable. Hedge
   numbers with `~`, `up to`, `typically`.

6. **Pinout (DIP-N, top view)** — ASCII diagram followed by a markdown table.
   - Use a **`text`-fenced** code block for the ASCII (markdown lint requires a
     language).
   - **Pad pin labels so the chip walls (`│`) align vertically.** This is the
     most common first-draft defect — count columns before writing.
   - Pin numbers sit just inside the wall: `label N│   │N label`. Use a U-notch
     at the top: `┌──U──┐`.
   - Table columns: `Pin | Name | Use`. For multi-function pins, list roles
     separated by `/`. Bold any role that is critical or surprising (e.g.
     **input-only**, **ICSPDAT**).

7. **Sample circuit** — heading: `## Sample circuit — <what it does>`. Body is
   a **connection list**, not ASCII schematic art. Be explicit about pin
   numbers, component values, polarity where it matters, and which pins to
   leave open. End with a one-line note on what the user should see at the
   output.

8. **Variations** *(optional)* — short bullets describing other common modes
   (e.g. triangle vs sine output, FSK, sweep, external crystal). Include only
   if the part has more than one canonical use; skip for single-purpose parts.

9. **Watch out for** — bullets covering: easy-to-miss constraints, datasheet
   gotchas, silent-failure modes, configuration that matters. Start each
   bullet with a bolded short tag.

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

3. **Decide which sections apply.** Full structure for chips. For modules with
   on-board labelling, skip the ASCII pinout but include a connector table.

4. **Draft the page** following the structure. Apply sincere language: hedge
   specs, avoid `must / always / never` as rhetorical emphasis, mark estimates
   as estimates. The datasheet is authoritative; this page is a curated entry
   point.

5. **Verify ASCII pinout alignment** before writing. Count characters from the
   left edge to each `│` and confirm they match across all lines of the chip
   body. This is the single most common defect.

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
