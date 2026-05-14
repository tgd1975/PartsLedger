---
id: TASK-047
title: Implement src/partsledger/enrichment/family_datasheets.py — MPN-prefix → URL table
status: open
opened: 2026-05-14
effort: Small (<2h)
complexity: Junior
human-in-loop: No
epic: metadata-enrichment
order: 3
prerequisites: [TASK-022]
---

## Description

Static MPN-prefix → fallback datasheet URL table for when Nexar
returns nothing (IDEA-008 Stage 3). Codifies the logic that
IDEA-005's `/inventory-add` skill applies today via `WebSearch`.

New module `src/partsledger/enrichment/family_datasheets.py` exposes
`lookup_family(mpn: str) -> str | None`. The implementation is a
plain Python dict mapping MPN prefix → known-good manufacturer
datasheet URL. No file I/O, no scraping, no dynamic discovery —
keeps the fallback dependency-free and grep-able.

Initial seed entries from the MPN families already present in
`inventory/parts/`: `LM358`, `LM386`, `TL08x` (TI op-amps), `NE555`
(timers), `L7805` (regulators), `PIC16F` (Microchip MCUs).
Extension by hand-edit of the dict — no upgrade path needed.

If even this fallback misses, the caller leaves the Datasheet cell
empty per IDEA-008's *Fallback path* — empty is honest, a wrong URL
rots without notice.

## Acceptance Criteria

- [ ] `lookup_family("LM358N")` returns the TI LM358 datasheet URL.
- [ ] `lookup_family("PIC16F628A")` returns the Microchip PIC16F62x
      family datasheet URL.
- [ ] `lookup_family("XYZ123")` returns `None` without raising.
- [ ] Module has no file I/O — the table is a module-level dict, not
      loaded from JSON or YAML.

## Test Plan

**Host tests (pytest)** under `tests/enrichment/test_family_datasheets.py`:

- Parametrised lookup tests covering each seed family: `LM358`,
  `LM386`, `TL08x`, `NE555`, `L7805`, `PIC16F`.
- Unknown-prefix returns `None`.
- Empty-string MPN returns `None`.
- Prefix matching is case-insensitive (`lm358n` → same URL as
  `LM358N`).

No mocking needed; the module is pure data.

## Prerequisites

- **TASK-022** — `src/` layout is in place so the module lands under
  `src/partsledger/enrichment/`.

## Notes

- URLs must be manufacturer-direct (ti.com, microchip.com,
  st.com, …) — no aggregator links that rot.
- Extension policy: when the maker adds a new part family to
  inventory, the dict is hand-edited in the same change. No dynamic
  scraping.
