---
name: co-inventory-master-index
description: Invariants for inventory/INVENTORY.md — the master ledger. Per-part row schema, category sections, link-into-parts/ rule. Surfaced when INVENTORY.md is about to be edited.
---

# Invariants (checklist, not prose)

## Per-row schema

- [ ] Each row carries the canonical six columns in order:
      `Part | Qty | Description | Datasheet | Octopart | Notes`.
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

## Category sections

- [ ] Sections are H2 headings (`## MCUs`, `## ICs`, `## Sensors`,
      `## Modules`, `## Transistors`, `## Bulk / kits`). The set
      stays small — a new top-level category needs an ADR; sub-
      categorise inside Notes if you need to.
- [ ] A section may be empty (header without a table) while the
      maker hasn't added any parts of that kind yet — that's fine;
      it documents intent.
- [ ] The order of sections is alphabetical except `Bulk / kits`
      which goes last (it's the catch-all and pushes off-bottom).

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
