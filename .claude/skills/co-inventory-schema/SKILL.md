---
name: co-inventory-schema
description: Invariants for inventory/parts/<part>.md — frontmatter schema (IDEA-004 + IDEA-027), pin-aliasing, MD-as-source-of-truth, master-index linkage. Surfaced when an inventory part-MD is about to be edited.
---

# Invariants (checklist, not prose)

## Frontmatter schema

- [ ] **Required fields** are present and well-typed:
      `part` (string, manufacturer part number),
      `manufacturer` (string),
      `package` (string — DIP-8, TO-220, SOIC-14, etc.),
      `pins` (list of pin objects — see pin-aliasing below),
      `datasheet` (URL or local path),
      `octopart` (Octopart canonical URL).
- [ ] **Category-conditional fields** match the part's nature:
      MCUs/ICs → `pins` array is mandatory and complete (no
      "to-be-filled" placeholders); passives → `value` and
      `tolerance`; modules with onboard regulators → `vcc_range`.
- [ ] **No fields outside the IDEA-027 vocabulary** without an ADR.
      The vocabulary is maintained in the
      `AwesomeStudioPedal` repo's IDEA-027 dossier. Drift here
      breaks CircuitSmith's `--prefer-inventory` reader.

## Pin-aliasing rules (per ADR-0010 in CircuitSmith)

- [ ] Each pin in `pins[]` carries `name` (silicon pin name) and,
      where the dev-board labels it differently, `alias` (e.g.
      ESP32 silicon `IO36` is silk-screened `VP` on the
      NodeMCU-32S — both must be listed so a circuit YAML written
      against the dev-board still resolves to silicon).
- [ ] Pin `type` is one of the IDEA-027 vocabulary terms
      (`POWER_VCC`, `POWER_GND`, `IO`, `I2C`, `SPI`, `ADC`, `DAC`,
      `STRAPPING`, …). Unknown types fall back to `IO` only with a
      comment explaining why.

## MD is source of truth — never write SQLite without an MD update

- [ ] **Forbidden edge** (per `docs/developers/ARCHITECTURE.md`
      § Decoupling seams): code paths that write to
      `inventory/.embeddings/vectors.sqlite` must also write a
      matching `inventory/parts/<part>.md` update in the same
      operation. Editing the MD here is the *trigger* this skill
      surfaces; editing the cache without the MD is the failure
      mode the architecture forbids.
- [ ] The MD entry's image filename (in frontmatter or body) is
      the key the embedding cache uses to find the source frame.
      Renaming an image without an MD update silently drifts the
      cache.

## Master-index linkage

- [ ] If `inventory/INVENTORY.md` already lists this part, the
      `Part` cell links to this file (`[<part>](parts/<part>.md)`).
      Editing the per-part MD without updating the index drifts the
      navigable book; editing the index without a per-part MD
      creates a dangling link.
- [ ] Quantity changes belong in `inventory/INVENTORY.md` (the
      `Qty` cell), not in the per-part MD frontmatter — the per-
      part MD is the *reference page*, the index is the *ledger*.

## Authority

See [`docs/developers/ideas/open/idea-004-markdown-inventory-schema.md`](../../../docs/developers/ideas/open/idea-004-markdown-inventory-schema.md)
for the inventory-MD shape and
[`docs/developers/ARCHITECTURE.md` § Decoupling seams](../../../docs/developers/ARCHITECTURE.md#decoupling-seams)
for the MD-is-truth invariant. The IDEA-027 vocabulary is canonical
in the AwesomeStudioPedal repo.

## Downstream consumers

A breaking change to the frontmatter schema affects:

- `inventory-add` skill (writes new entries).
- `inventory-page` skill (extends entries with reference prose).
- `embed_cache` module (reads images named in frontmatter, lands
  with the pipeline modules).
- CircuitSmith's `--prefer-inventory` reader (cross-repo consumer).
