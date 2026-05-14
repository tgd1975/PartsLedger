---
id: IDEA-003
title: External inventory tool integration
description: Add an interface to an existing electronics inventory tool (InvenTree / PartKeepr / Partsbox) for import, export, or sync of parts data.
category: integration
---

There are mature, dedicated inventory tools for electronics components
already in use by the maker community. PartsLedger's value lies in being
*markdown-native* and *LLM-first*, but it does not have to replace these
tools — it can bridge to them. This idea explores **which** external tool
to integrate with first, and **in which direction** the data should flow.

## Motivation

- **Onboarding from existing inventories.** Users (including the
  author) may already have a populated InvenTree/PartKeepr instance.
  Manually re-photographing every part to seed PartsLedger is a
  non-starter.
- **UI / multi-user access.** Markdown is great for LLMs and
  diff-friendly history, but poor for "give me a stock count across
  10 locations" or "let my workshop colleague check inventory from
  their phone". A real inventory tool covers that gap.
- **Stock management.** Quantities, locations, supplier links, BOM
  consumption — solved problems in InvenTree, out of scope for
  PartsLedger's MD core.

## Candidates and reasoning

### Option A — InvenTree (recommended starting point)

[inventree.org](https://inventree.org)

**Why it fits:**

- **Stack match.** Python/Django backend; PartsLedger is already
  Python-heavy (PyTorch, OpenCV, sqlite-vec). A client lives naturally
  next to the existing pipeline code.
- **Comprehensive REST API.** Parts, categories, stock locations,
  suppliers, manufacturer parts, attachments, custom parameters — all
  exposed and well-documented.
- **Custom parameters.** InvenTree supports arbitrary
  `Parameter`/`ParameterTemplate` pairs per part. The CircuitSmith
  component-profile fields (`vcc_min`, `pin_count`, `vf_typ_ma`, …) can
  round-trip as parameters without schema changes on the InvenTree side.
- **Active and self-hostable.** Strong community, frequent releases,
  Docker deployment, no SaaS lock-in.
- **Attachments.** Native support for attaching images and datasheets
  per part — direct counterpart to PartsLedger's `images/` and
  `datasheet.pdf`.

**Drawbacks:**

- Heavier dependency: requires a running InvenTree instance somewhere
  (Docker + Postgres or SQLite).
- Field-mapping discipline needed — InvenTree's part model is
  relational; PartsLedger's frontmatter is intentionally loose.
  Round-tripping requires a documented mapping.

### Option B — PartKeepr

[partkeepr.org](https://partkeepr.org)

**Why it could fit:**

- Long-standing project, widely deployed in maker spaces.
- REST API available.

**Drawbacks:**

- PHP/Symfony stack — alien to PartsLedger's Python toolchain.
- Development cadence has slowed considerably; InvenTree has largely
  absorbed its mindshare.
- API less ergonomic than InvenTree's; documentation thinner.

### Option C — Partsbox

[partsbox.com](https://partsbox.com)

**Why it could fit:**

- Polished UI, well-regarded API, good mobile support.

**Drawbacks:**

- **Commercial SaaS** — cloud-only, subscription-based. Conflicts with
  PartsLedger's "inventory is the source of truth, locally owned"
  posture (see [CLAUDE.md](../../../../CLAUDE.md#inventory-is-the-source-of-truth)).
- No self-hosting path; lock-in risk if the service changes pricing or
  shuts down.

### Option D — distributor catalog APIs (Nexar/Octopart, Mouser, Digi-Key)

Already used in PartsLedger's identification pipeline (see
[IDEA-008](idea-008-metadata-enrichment.md)). These are **catalogs**, not
**personal inventories** — they answer "what is this part" but not
"how many do I own and where is it". Out of scope for this idea; listed
to make the distinction explicit.

### Recommendation

**Start with InvenTree.** Stack alignment, parameter-flexible schema,
self-hostable, active community. PartKeepr and Partsbox can be added
later behind the same interface if there is demand.

## Direction of data flow

Three plausible scopes, in increasing order of complexity:

### Scope 1 — Import (InvenTree → PartsLedger)

Pull existing parts (including images, datasheets, parameters) from a
running InvenTree instance and write them as
`inventory/parts/<part>.md` files. One-shot or repeatable.

- **Pros:** Easiest to implement. Solves the "I already have an
  InvenTree, seed PartsLedger from it" use case directly. Read-only on
  the InvenTree side — no risk of corrupting the source.
- **Cons:** No way to push enrichments (Claude-Vision-derived
  descriptions, CircuitSmith profile fields) back.

### Scope 2 — Export (PartsLedger → InvenTree)

Push PartsLedger MDs into InvenTree as parts, with parameters mapped
from the frontmatter. Enables UI / mobile access and multi-user
stock-tracking on top of the LLM-curated catalog.

- **Pros:** Gives PartsLedger a UI and a stock-management story
  without rebuilding those features. MD remains the source of truth;
  InvenTree becomes a downstream view.
- **Cons:** Conflict resolution if InvenTree-side edits happen
  (stock counts will, by design). Need to decide which fields are
  one-way (frontmatter → InvenTree) and which InvenTree owns (stock,
  location).

### Scope 3 — Bidirectional sync

Full round-trip with conflict detection. Last-write-wins, per-field
ownership rules, or operational-transform-style merging.

- **Pros:** Most flexible long-term story.
- **Cons:** Significantly higher implementation cost. Conflict
  semantics are subtle. Probably premature before scopes 1 and 2 have
  been used in anger.

### Recommendation

**Build Scope 1 first** (import), then **Scope 2** (export with clear
field-ownership rules: PartsLedger owns identification/spec fields,
InvenTree owns stock/location). Defer Scope 3 until concrete
multi-editor pain emerges.

## Open questions

- Where should the InvenTree connection config live? Likely a new
  `$PL_INVENTREE_URL` / `$PL_INVENTREE_TOKEN` pair in
  [.envrc](../../../../.envrc.example), consistent with the existing
  `$PL_NEXAR_*` pattern.
- How are CircuitSmith component-profile fields mapped to InvenTree
  `Parameter` templates? Define a canonical template set
  (`vcc_min`, `pin_count`, `package`, …) that the integration
  auto-creates if missing.
- Granularity of import: every part, or filtered by category /
  location? Filtering keeps the first import scoped and reviewable.
- Image and datasheet handling: copy bytes into
  `inventory/parts/<part>/images/` and `datasheet.pdf`, or store
  InvenTree URLs as references? Bytes are safer (offline, source-of-
  truth principle); URLs are smaller.
- DINOv2 re-embedding policy after import: re-embed all imported
  images, or only those without an existing entry in
  `inventory/.embeddings/vectors.sqlite`?
- Does the integration belong inside PartsLedger, or as a small
  separate CLI (`pl-invtree import`, `pl-invtree export`) that depends
  on the PartsLedger MD schema? Probably the latter — keeps the core
  pipeline thin.

## Related

- [IDEA-004](idea-004-markdown-inventory-schema.md) — defines the MD
  schema that any external integration must round-trip against.
- [CircuitSmith IDEA-010](https://github.com/tgd1975/CircuitSmith/blob/main/docs/developers/ideas/open/idea-010-prefer-inventory-adapter.md)
  — the CircuitSmith bridge; the same parameter vocabulary
  (IDEA-027) should drive the InvenTree parameter-template mapping.
