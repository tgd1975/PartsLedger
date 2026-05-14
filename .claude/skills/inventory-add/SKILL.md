---
name: inventory-add
description: Add a component (or multiple) to inventory/INVENTORY.md. Takes a part ID and quantity; fills in description, datasheet, category. Asks for clarification when the part is ambiguous, suspicious, or unidentifiable.
---

# inventory-add

The user invokes this as `/inventory-add <part-id> <qty>`, optionally with more
`<part-id> <qty>` pairs separated by commas (e.g. `/inventory-add TL082CF 3, 7660S 2`).

If `<qty>` is omitted for any part, assume **qty = 1** without asking. Mention the
default briefly in the report so the user can correct it if wrong.

The target file is `inventory/INVENTORY.md` at the repo root. The
sections are **whatever H2 headings the file already contains** —
the canonical defaults are MCUs, ICs, Sensors, Modules / breakouts,
Transistors, Bulk / kits, but the maker is free to rename or add
sections (`## Linear ICs`, `## Connectors`, etc.) without changing
the schema.

Standard parts tables carry the canonical seven columns:
`Part | Qty | Description | Datasheet | Octopart | Source | Notes`.

The Bulk / kits section is a bullet list / kit-content table area
for assortments where individual values aren't catalogued
(resistors, diodes, ceramic & electrolytic capacitors, LEDs,
generic small-signal transistors, etc.).

When the part is a **bulk / kit item** (a generic class like "resistors" or
"1N4148 diodes" rather than a specific marked IC), skip steps 3–6 below and
instead append a bullet to the **Bulk / kits** section with a short
description (assume Conrad-style standard hobbyist assortments unless the
user says otherwise). No datasheet lookup, no table row.

## What to do

For each `<part-id> <qty>` pair:

1. **Identify the part.** Use your own knowledge of common electronic components.
   Produce:
   - The likely canonical part number (e.g. `7660S` → `ICL7660S` if confident).
   - A short description (one phrase, e.g. *"dual JFET-input op-amp"*).
   - The category — one of MCU / IC / Sensor / Module.

2. **Sanity-check before writing.** Stop and ask the user when any of these apply:
   - **Ambiguous** — multiple plausible parts match the ID. List the candidates.
   - **Suspicious** — the part is exotic, very expensive, or unusual to find in a
     hobbyist drawer. Flag it rather than refusing: *"Unusual to have on hand —
     confirm this is the part?"*
   - **Unidentifiable** — no real component matches the ID closely. Ask if it was
     a typo or if it's a vendor-specific marking.
   - **Category unclear** — when you cannot confidently place it in MCU / IC /
     Sensor / Module, ask.

   Hedge identifications using sincere language: *"Likely the X from manufacturer
   Y"*, not *"is X"*. The user is the ground truth, not your guess.

   **Package assumption:** the user's drawer is DIP / through-hole only. Do not
   add SOIC / SMD package qualifiers to descriptions even when the part suffix
   suggests a surface-mount variant in the manufacturer's naming scheme — the
   user's physical part is the ground truth. Focus the description on function.

3. **Find a datasheet URL.** Run a `WebSearch` for the canonical part number plus
   "datasheet". Prefer the manufacturer's site (TI, Analog Devices, ST, NXP,
   etc.) or a clearly authoritative mirror. Do **not** fabricate URLs.

   If a manufacturer-specific URL is not found with confidence, fall back to a
   **typical / equivalent datasheet** for the same generic part family (e.g.
   `CD4018B` from TI for a Toshiba `TC4018BP`, since 4000-series CMOS logic
   is functionally identical across vendors). When you fall back:
   - Put the equivalent's link text and URL in the Datasheet cell.
   - Add a note in the Notes column: *"Generic `<part>` (TI); `<manufacturer>`-specific not found"* (or similar — just make the substitution explicit).

   Leave the Datasheet field blank only if you cannot identify even a generic
   equivalent.

4. **Build the Octopart cell.** Format:
   `[search](https://octopart.com/search?q=<query>)`. The `<query>` is the
   inventory's Part marking by default. Override to the canonical name when the
   marking is junk or a clone (e.g. `TLCS549` → query `TLC549`, `SN7414SN` →
   query `SN7414`, `U74HC14L` → query `74HC14`, `7660S` → query `ICL7660S`).
   URL-encode special chars (`/` → `%2F`). If the part is so obscure that you
   doubt Octopart has any results, leave the cell empty rather than linking to
   a guaranteed-empty search.

5. **Locate the right section** in `inventory/INVENTORY.md`.
   Enumerate the file's `## …` H2 headings first and propose
   from that list. Only fall back to the default category names
   (MCUs / ICs / Sensors / Modules / breakouts) when the file
   has *no* H2 headings yet — i.e. the inventory is brand new.
   Adding a new section without an ADR is fine; renaming an
   existing section is the maker's call.

6. **Update or insert.**
   - If the part is already in that section's table → **bump the existing row's
     Qty** by the new amount (do not add a duplicate row).
   - Otherwise → insert a new row in the **alphabetically correct position**
     within the section's table. Sort key is the displayed Part text (for a
     linked cell `[7660S](parts/7660s.md)`, the key is `7660S`). Digits sort
     before letters (ASCII order). Do not append at the end.
   - **Source cell:** write `Source: manual` on every new row.
     The `/inventory-add` flow is the human-curated path; the
     camera-path pipeline writes `Source: camera` from a separate
     entry point. Never silently mix sources on a single row.

7. **Keep the table aligned.** Markdownlint enforces aligned-style tables (rule
   MD060). When a new row's content makes any column wider than its current
   max, recompute that column's width and repad every row (and the header /
   separator). The cleanest way: generate the rewritten table with a small
   Python snippet that left-justifies each cell with `str.ljust` keyed off the
   max content length per column, and joins with `' | '`.

8. **Disambiguate similar parts.** If the new part is a near-twin of an
   existing row (same function, similar marking — e.g. TLC548 ↔ TLC549,
   NE555N ↔ NE555P, 74HC595 ↔ 74HC165, a marking variant of an existing
   part), add a short distinguishing hint:
   - Prefer the *Description* column for a one-spec difference that fits
     (e.g. *"4 MHz I/O"* vs *"1.1 MHz I/O"*, *"(SIPO)"* vs *"(PISO)"*).
   - Use the *Notes* column for relational facts that don't belong in a spec
     line (e.g. *"Marking variant of TL082CF (same chip)"*, *"Slower sibling
     of TLC548"*).

   The goal: a reader scanning the table should immediately see why two
   similar rows are not duplicates.

9. **Report** per part: category, part number used, qty after the operation
   (new row vs. updated from N to M), and whether a datasheet URL and an
   Octopart link were found.

## What this skill does *not* do

- Does not commit. The user commits when ready.
- Does not invent datasheet URLs. Leaves the field blank if not confident.
- Does not silently choose between ambiguous candidates — always asks.
- Does not create new category sections. If a part does not fit MCU / IC /
  Sensor / Module, ask the user whether to add a new section or place it
  elsewhere.

## Sincere-language note

Hedge identifications: *"likely"*, *"appears to be"*, *"common marking for"*. The
part on the user's bench is real; your identification is a guess until they
confirm.
