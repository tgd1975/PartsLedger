---
id: IDEA-009
title: CircuitSmith --prefer-inventory adapter
description: The bridge that lets CircuitSmith bias its component selection toward parts the maker already owns. Lives in the CircuitSmith repo, depends on the PartsLedger MD schema ([IDEA-004]). BOM gets three columns — needed / in stock / to order.
category: integration
---

> *Replaces the "Integration with CircuitSmith" section of the retired
> IDEA-001 dossier.* The smallest piece of the toolchain in code terms
> (~50 LOC loader patch on CircuitSmith's side), but the only one that
> reaches outside the repo — worth honing in isolation so the contract
> between the two projects is explicit.

## Status

⏳ **Planned in both repos.** PartsLedger doesn't ship the adapter
itself; it ships the schema the adapter reads ([IDEA-004](idea-004-markdown-inventory-schema.md)).
CircuitSmith is a planned sibling — see the
[CircuitSmith project memory](file:///home/tobias/.claude/projects/-home-tobias-Dokumente-Projekte-PartsLedger/memory/project_circuitsmith.md).

## What this dossier owns

The **contract** between PartsLedger (the inventory) and CircuitSmith
(the schematic forge). Explicit framing because both repos need to
agree on it:

- Direction of data flow.
- Which files are read, in what order, with what tolerance.
- How CircuitSmith's existing component-profile vocabulary
  ([reference_idea027](file:///home/tobias/.claude/projects/-home-tobias-Dokumente-Projekte-PartsLedger/memory/reference_idea027.md))
  maps onto PartsLedger's inventory shape.
- What the BOM output looks like with the adapter active.

The **code** that implements the contract lives in CircuitSmith. This
dossier defines the protocol; CircuitSmith's own dossier (when it
exists) defines the implementation.

## Direction — one-way only

```text
PartsLedger              CircuitSmith
  INVENTORY.md  ───────►  --prefer-inventory mode
  parts/*.md    ───────►  (read-only consumer)
```

PartsLedger's MDs are **read** by CircuitSmith. CircuitSmith does **not**
write back into the inventory. Two reasons:

1. **PartsLedger has prose, CircuitSmith has profiles.** PartsLedger's
   reference pages are hobbyist prose; CircuitSmith's component
   profiles are SPICE-style structured data. The schemas don't
   round-trip without lossy parsing.
2. **Source-of-truth invariant.** The
   [`co-inventory-master-index`](../../../../.claude/skills/co-inventory-master-index/SKILL.md)
   guard says only the human and the inventory skills write to
   `INVENTORY.md`. CircuitSmith automating writes would violate that
   invariant.

If CircuitSmith *wants* to push enrichments back (e.g. a SPICE-derived
`vcc_min`), the path is the same as any other contributor: emit a diff
or a suggestion, let the maker apply it via `/inventory-add` or by hand.

## The contract

### What CircuitSmith reads

In order of priority:

1. **`inventory/INVENTORY.md`** — must read. The Part column + Qty
   column give CircuitSmith the "what is in stock and how many" view.
2. **`inventory/parts/<id>.md` Pinout tables** — best-effort. If a
   page exists and contains a Pinout section (recognisable by the DIP-N
   ASCII block + a pin/function table), CircuitSmith lifts the
   pin-aliasing into its component-profile layer.
3. **Everything else** — ignored. Prose, ELI5, sample circuits,
   "Pairs naturally with" — all human-oriented and out of scope for
   the adapter.

### Field mapping

| PartsLedger | CircuitSmith profile field |
|---|---|
| `INVENTORY.md` Part column (e.g. `LM358N`) | `mpn` |
| `INVENTORY.md` Qty | `inventory.qty` |
| `INVENTORY.md` Description | (hint only — overridden by profile if present) |
| `INVENTORY.md` Datasheet URL | `datasheet_url` |
| `parts/<id>.md` Pinout table | `pin_aliases` (per [IDEA-027 vocabulary](file:///home/tobias/.claude/projects/-home-tobias-Dokumente-Projekte-PartsLedger/memory/reference_idea027.md)) |

Fields CircuitSmith already had (`vcc_min`, `vcc_max`, `pin_count`,
`package`) stay in the CircuitSmith repo's `components/*.py` — the
adapter does **not** invent them.

### Family-page handling

When `INVENTORY.md` has two rows that "Share page with …" (e.g.
`PIC16F628` and `PIC16F628A`), the adapter treats them as **two distinct
MPNs** with stock summed at family level for the *"in stock"* check, but
keeps the rows separate in the BOM output. The maker still chooses
which variant the schematic targets.

## What the maker sees — BOM with `--prefer-inventory`

CircuitSmith's BOM gets three columns instead of two:

```text
| Designator | Part        | Needed | In stock | To order |
|------------|-------------|--------|----------|----------|
| U1         | LM358N      | 1      | 1        | 0        |
| U2         | TL082CP     | 2      | 1        | 1        |
| R1..R8     | 10kΩ 1/4W   | 8      | (bulk)   | 0        |
```

Bulk/kits show as `(bulk)` in the *In stock* column rather than a
numeric count — the inventory doesn't track individual values inside a
resistor kit (see [IDEA-004 § INVENTORY.md](idea-004-markdown-inventory-schema.md#inventorymd--the-flat-index)).

## What we build vs. what we use

| Component | Source | Status |
|---|---|---|
| Inventory loader (~50 LOC) | CircuitSmith repo | ⏳ planned |
| Pin-aliasing lifter | CircuitSmith repo, reads PartsLedger Pinout tables | ⏳ planned |
| BOM column extension | CircuitSmith repo | ⏳ planned |
| MD schema | This repo, [IDEA-004](idea-004-markdown-inventory-schema.md) | ✅ stable |
| Pin-aliasing vocabulary | AwesomeStudioPedal repo (IDEA-027) | ✅ stable |

PartsLedger ships nothing for this; it's a CircuitSmith-side change.
This dossier exists so the contract is documented in *both* repos when
implementation lands.

## Open questions to hone

- **Pinout-table parser robustness.** The ASCII-DIP + table pattern is
  consistent across the six existing pages, but it's a convention, not
  a spec. Worth tightening into a regex CircuitSmith can rely on, or
  adding a `<!-- pin-aliases: yaml -->` machine-readable block per
  [IDEA-004 open questions](idea-004-markdown-inventory-schema.md#open-questions-to-hone)?
- **Quantity reservation.** During BOM composition, if two designs are
  open and both want the single LM358N, who reserves it? Probably
  out-of-scope (the maker resolves by hand), but worth naming.
- **Family-page semantics in BOM.** Family-summed stock for
  feasibility check, per-row in the BOM — is that the right balance?
  Or always per-row?
- **Adapter discovery.** How does CircuitSmith find the PartsLedger
  repo? `$PL_INVENTORY_PATH` env var (see
  [CLAUDE.md § Project env vars](../../../../CLAUDE.md#project-env-vars--use-pl_-never-hard-code-paths)),
  CLI flag, config file? Probably env var with CLI override.
- **Versioning.** What happens when PartsLedger's schema gains a
  `schema_version` ([IDEA-004 open questions](idea-004-markdown-inventory-schema.md#open-questions-to-hone))
  and CircuitSmith pins a version it understands? Add to the contract
  now, before either side has a v2.
- **Round-trip enrichment path.** Even though writes are one-way, a
  CircuitSmith *suggestion* mode ("I derived vcc_min=3.0 V from
  profile; want me to add a Notes line in INVENTORY.md?") might be
  useful. Worth specifying?

## Related

- [IDEA-004](idea-004-markdown-inventory-schema.md) — defines what the
  adapter reads.
- [IDEA-003](idea-003-external-inventory-tool-integration.md) — the
  InvenTree integration; if InvenTree becomes a parallel inventory
  source, CircuitSmith should be able to read it via the same adapter
  pattern.
- `reference_idea027` (memory) — the canonical pin-aliasing vocabulary
  CircuitSmith carries upstream.
