---
name: co-inventory-master-index
description: Invariants for inventory/INVENTORY.md — the master ledger. Per-part row schema, category sections, link-into-parts/ rule. Surfaced when INVENTORY.md is about to be edited.
---

# Invariants (checklist, not prose)

## Per-row schema

- [ ] Each row in a standard parts table carries the canonical
      seven columns in order:
      `Part | Qty | Description | Datasheet | Octopart | Source | Notes`.
      No reordering, no hidden columns. CircuitSmith's
      `--prefer-inventory` reader assumes this header.
- [ ] `Part` cell:
      - Markdown link to `parts/<part>.md` *if* a per-part page
        exists. Plain text otherwise.
      - The link target lives at `inventory/parts/<part>.md`
        (relative path from `INVENTORY.md` is `parts/<part>.md`).
- [ ] `Qty` is an integer. Use `0` for parts you've used up but
      want to keep the entry around as a reference. Use a fraction
      like `~10` for bulk parts where exact count would be theatre
      (resistors, headers, jumper wires).
- [ ] `Datasheet` and `Octopart` cells contain links, not raw URLs
      naked in the table — `[datasheet](https://...)` /
      `[octopart](https://...)` keeps the table scannable.
- [ ] `Source` cell records who added the row. Validate as a
      **non-empty lowercase token, no allow-list**. The
      well-known values are `manual` (human-curated or
      `/inventory-add`) and `camera` (visual-recognition pipeline);
      future importers may add their own literal (`imported`, …)
      without a schema bump. Reject empty cells, whitespace-only
      cells, and mixed-case tokens.

## Category sections

- [ ] Sections are H2 headings (`## …`). The skill **does not
      hard-code** a fixed list — enumerate the `## …` headings
      from the file at lint time and treat each one as a legitimate
      bucket. Renaming `## ICs` to `## Linear ICs`, or adding a
      `## Connectors` section, must not trip the lint. Every row
      must live under *some* H2, not under a *specific* one.
- [ ] A section may be empty (header without a table, or a header
      with a placeholder row) while the maker hasn't added any
      parts of that kind yet — that's fine; it documents intent.
- [ ] Section ordering is the maker's call — alphabetical is a
      reasonable default but not enforced.
- [ ] Section-specific tables (e.g. the Transistors DDR/USSR
      table with custom columns like `Type | Equivalent | Package
      | Umax | Imax`, or kit-content tables like `Decade range |
      E12 values`) are legitimate divergences from the canonical
      seven-column row schema. They append `Source` at the end
      for parts tables; pure kit-content tables (no per-part rows)
      do not carry a `Source` column.

## Quantity changes ride here, not in the per-part MD

- [ ] **Stock movements** (using a part, restocking, recounting)
      belong in this file's `Qty` cell. Do not also bump a
      `quantity:` field in the per-part MD — there isn't one.
      The per-part MD is the *reference page*, this is the
      *ledger*. Git history on this file is the stock-movement
      log.
- [ ] When a row's `Qty` drops to `0` and the part is unlikely to
      be restocked, leave it in place rather than deleting — the
      row plus the per-part MD are still useful as documentation.

## Generated vs hand-edited

- [ ] If a future task lands a script that auto-regenerates
      `INVENTORY.md` from the per-part MDs (e.g.
      `scripts/regenerate_inventory_index.py`), this file becomes
      a generated artefact. Until then it is hand-edited — `git
      blame` is the change log.
- [ ] If the file ever becomes generated, add a `<!-- GENERATED
      -->` marker block at the top per the same convention used
      under `docs/developers/tasks/{OVERVIEW,EPICS,KANBAN}.md`.

## Authority

See [`docs/developers/ideas/open/idea-004-markdown-inventory-schema.md`](../../../docs/developers/ideas/open/idea-004-markdown-inventory-schema.md)
§ "`INVENTORY.md` — the flat index" for the master-index shape.

## Downstream consumers

A breaking change to the row schema affects:

- `inventory-add` skill (appends rows + bumps `Qty`).
- `inventory-page` skill (links the `Part` cell when authoring a
  reference page).
- CircuitSmith's `--prefer-inventory` reader (parses this file to
  bias schematic generation toward parts in stock).
- `cat inventory/INVENTORY.md` as a one-shot LLM-readable inventory
  query — the table is the query layer.
