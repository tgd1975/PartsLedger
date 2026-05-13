---
id: IDEA-008
title: Metadata enrichment — Nexar/Octopart + optional resistor-band OCR
description: After identification ([IDEA-007]) names the part, this stage fills in the datasheet URL, manufacturer, package, lifecycle, and (optionally) reads colour bands on resistors. Optional in both senses — the maker can fill datasheets by hand and the project can stay fully offline.
category: camera-path
---

> *Replaces the camera-path "Nexar / Octopart" and "OCR" stages from the
> retired IDEA-001 dossier.* Optional plumbing — none of it gates the
> camera path from being useful — but worth specifying separately so the
> "fully offline" mode in [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md#fully-offline-mode)
> stays a real switch and the API integration is honed before
> implementation.

## Status

⏳ **Planned.** Auth env vars already reserved:
`$PL_NEXAR_CLIENT_ID` and `$PL_NEXAR_CLIENT_SECRET` (see
[`.envrc.example`](../../../../.envrc.example) and
[CLAUDE.md § Project env vars](../../../../CLAUDE.md#project-env-vars--use-pl_-never-hard-code-paths)).

## What this stage does

Given a confirmed part-ID from [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md),
fill in the metadata cells on the new `INVENTORY.md` row
(see [IDEA-004 § `INVENTORY.md`](idea-004-markdown-inventory-schema.md#inventorymd--the-flat-index)):

- **Datasheet** — manufacturer PDF URL (or family-datasheet fallback).
- **Octopart** — `octopart.com/search?q=<part>` (cheap, stable).
- **Description** — short, hedged, single-line: *"Dual op-amp,
  single-supply"*.
- **Notes** — package, lifecycle (`active` / `obsolete` / `NRND`),
  date-code if visible.

The colour-band OCR fork is **independent** of the API call: it runs
only for resistors, before the API call, and feeds the value into the
identification round-trip.

## Primary path — Nexar GraphQL API

Nexar is the Octopart owner's developer API. Single GraphQL endpoint;
free tier covers hobbyist usage.

```graphql
query Part($q: String!) {
  supSearchMpn(q: $q, limit: 1) {
    results {
      part {
        mpn
        manufacturer { name }
        bestDatasheet { url }
        bestImage { url }
        category { path }
        lifecycleStatus
      }
    }
  }
}
```

Fields lifted into the inventory:

| Inventory cell | Nexar field |
|---|---|
| Description | `category.path` → first segment + hedged adjective |
| Datasheet | `bestDatasheet.url` |
| Notes (package) | best-effort from category / description |
| Notes (lifecycle) | `lifecycleStatus`, only if not `Active` |

**Auth:** OAuth client credentials, refreshed per session. Token caching
in `inventory/.embeddings/` (or another regenerable location).

## Fallback path — generic family datasheet

If Nexar returns no datasheet (rare, but happens for old or rebadged
parts), fall back to the family datasheet logic the skill path already
uses (see [IDEA-005](idea-005-skill-path-today.md)): TI for op-amps,
Microchip for PICs, etc.

If even the fallback misses, leave the cell **empty** rather than
inventing a URL. Empty is honest; a wrong URL rots without notice.

## Optional fork — resistor colour-band OCR

Through-hole resistors are the one part type where visual marking text
(*"the L7805CV"*) is replaced by a colour code. Three OCR routes:

| Route | Library | Notes |
|---|---|---|
| OpenCV + heuristic | `cv2` only | Hand-rolled colour segmentation; works for high-contrast 4-band parts in good lighting |
| Tesseract | `pytesseract` | Cheap but bad at band-on-cylinder geometry — usually wrong |
| PaddleOCR | `paddleocr` | More robust but heavyweight (~1 GB model) |
| **VLM-as-OCR** | reuse IDEA-007 VLM | Let the VLM read the bands — no extra dependency |

The VLM-as-OCR route is the dark-horse: Claude Opus Vision and Pixtral
both read resistor bands well enough to identify standard E96 values.
This collapses the OCR stage into the identification stage and saves an
entire dependency.

Worth honing: do we need a separate OCR stage at all, or is the VLM
sufficient?

## Cache policy

API responses cache to disk (`inventory/.embeddings/nexar_cache.sqlite`
or similar) keyed by MPN. TTL: 30 days for `Active` parts, never for
`Obsolete` (the metadata is frozen anyway). Cache is regenerable — same
ethos as the embedding cache.

## What we build vs. what we use

| Component | Source | Status |
|---|---|---|
| Nexar GraphQL client | This repo | ⏳ planned |
| Family-datasheet fallback table | This repo | ⏳ planned |
| Response cache | `sqlite3` (stdlib) | ⏳ planned |
| Resistor OCR — VLM route | Reuse IDEA-007 backend | ⏳ planned |
| Resistor OCR — classical route | OpenCV + optional PaddleOCR | ⏳ planned, possibly skipped |

## Open questions to hone

- **Nexar vs Octopart vs Mouser direct.** Nexar is the
  publisher-blessed path; Mouser's API is fatter (pricing, stock) but
  vendor-specific. Worth pulling pricing/stock, or out of scope?
- **OCR vs VLM-as-OCR.** Strong lean toward letting the VLM read
  colour bands and dropping the classical OCR dependency entirely. Any
  case where classical is meaningfully better?
- **Cache TTL.** 30 days for `Active`, never for `Obsolete` — reasonable
  default, but probably wrong for cases like a chip moving from
  `Active` to `NRND` mid-window.
- **Obsolete-part handling.** When the API says `Obsolete`, do we mark
  the row with a warning emoji / a Notes flag? Refuse to add it (the
  maker probably still has the part on the bench)?
- **Image upload.** Nexar offers `bestImage.url`. Worth downloading the
  manufacturer's product photo into `inventory/parts/<id>/images/` as a
  fallback when the maker hasn't captured one?
- **Multi-MPN responses.** `supSearchMpn` sometimes returns multiple
  candidates for ambiguous queries (`LM358` → LM358N, LM358P, LM358CN
  …). Pick the first, or surface the disambiguation back to the maker
  via the same TUI as the DINOv2 top-3?
- **Offline-mode UX.** When `$PL_NEXAR_CLIENT_ID` is unset, the
  pipeline silently skips this stage — the maker fills datasheets later
  by hand. Is silent the right behaviour, or a one-time "you're running
  offline; fine?" prompt?

## Related

- [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) — upstream
  identification; the offline-mode story is shared with this stage.
- [IDEA-004](idea-004-markdown-inventory-schema.md) — defines which
  inventory cells this stage writes.
- [IDEA-005](idea-005-skill-path-today.md) — the skill path already
  does a hand-rolled `WebSearch` for datasheets; this stage replaces
  that step when the camera path is in use.
- [IDEA-003](idea-003-external-inventory-tool-integration.md) — an
  InvenTree-seeded inventory might already have datasheets in
  attachments; this stage should respect existing data and not
  overwrite.
