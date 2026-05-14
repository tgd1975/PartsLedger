---
id: IDEA-008
title: Metadata enrichment — Nexar/Octopart
description: After identification ([IDEA-007]) names the part, this stage fills in the datasheet URL, manufacturer, package, and lifecycle. Optional — the maker can fill datasheets by hand and the project can stay fully offline.
category: camera-path
---

## Archive Reason

2026-05-14 — Promoted to EPIC-007 (metadata-enrichment), tasks TASK-045..TASK-050.

> *Replaces the camera-path "Nexar / Octopart" stage from the retired
> IDEA-001 dossier.* Optional plumbing — none of it gates the camera
> path from being useful — but worth specifying separately so the
> "fully offline" mode in [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md#fully-offline-mode)
> stays a real switch and the API integration is honed before
> implementation.
>
> The retired IDEA-001 also bundled an *OCR* stage here. That work has
> moved upstream into [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md#stage-2--vlm-identification):
> reading a part's identifying surface — whether DIP-package marking
> text or resistor colour bands — is *identification* work, not
> *enrichment*, and the VLM already does both. No separate OCR stage,
> no `pytesseract` / `paddleocr` dependency.

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
- **Description** — short, hedged, single-line: *"Dual op-amp,
  single-supply"*.
- **Notes** — package and (when Nexar reports anything other than
  `Active`) lifecycle.

Manufacturer name comes back from Nexar too but does **not** land as a
new column in `INVENTORY.md` — it stays in the response cache, read by
page generation for the *Source* line on the per-part page (see
[Where this metadata gets used](#where-this-metadata-gets-used)).
Date-code, when readable on the part body, is filled by the VLM in
[IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) — not by this
stage; Nexar doesn't know what the maker is holding.

## Where this metadata gets used

Three consumers, ordered by how dependent they are on enrichment
data. Page generation is the primary one — and the reason this stage
exists at all. Without it, IDEA-008 would be a decoration pass on
INVENTORY.md cells almost nobody reads.

### Primary — parts-page generation

`/inventory-page` ([IDEA-005](idea-005-skill-path-today.md#inventory-page-part-id))
produces a per-part reference page (ELI5 prose, ASCII pinout, sample
circuit). With IDEA-008 enrichment landed, the skill **reuses the
stored metadata instead of repeating its WebSearch dance**:

| Enrichment field | Page-generation use |
|---|---|
| Datasheet URL | Read directly by the LLM — replaces the WebSearch + family-datasheet fallback chain from [IDEA-005](idea-005-skill-path-today.md#inventory-add-part-id-qty-also-batched--part-id-qty). Pinout tables and electrical characteristics fall out of the PDF. |
| Description | Seeds the ELI5 opening (*"single-supply dual op-amp"*). |
| Package (Notes) | Picks the ASCII-pinout template — DIP-8 vs TO-220-3 vs header block. |
| Manufacturer (response cache, not an INVENTORY.md cell) | *Source* attribution on the page. |

**Auto-trigger semantics.** Page generation fires automatically when
a new row lands in INVENTORY.md — both via the camera path and via
`/inventory-add`. Two execution profiles by path:

- **Camera path**: **async background**. The capture loop's
  silent-qty++ promise from
  [IDEA-007 § Pipeline failure modes](idea-007-visual-recognition-dinov2-vlm.md#pipeline-failure-modes--what-doesnt-gate-the-write)
  stays intact; the page appears in `inventory/parts/` whenever the
  LLM finishes reading the datasheet. Maker keeps capturing the
  next part.
- **Skill path**: **synchronous**. `/inventory-add` already blocks
  while the LLM identifies the part and writes the row — chaining
  into `/inventory-page` is the same flow, one step longer.

The trigger mechanism itself is owned by
[IDEA-005](idea-005-skill-path-today.md); this stage just supplies
the inputs.

### Secondary — CircuitSmith via `--prefer-inventory`

[CircuitSmith IDEA-010 § Field mapping](https://github.com/tgd1975/CircuitSmith/blob/main/docs/developers/ideas/open/idea-010-prefer-inventory-adapter.md#field-mapping)
maps `Datasheet URL` → `datasheet_url` and `Description` → hint
only. Package and lifecycle are ignored — CircuitSmith carries its
own component profiles. The enrichment still earns its keep because
without it, CircuitSmith has no idea what the `LM358N` row in
INVENTORY.md actually *is*.

### Tertiary — maker browsing

The inventory MD is grep-able. *"Welche Op-Amps habe ich?"* →
`grep -i op-amp inventory/parts/*.md` works because Description and
Notes both contain searchable prose. Clicking the datasheet URL from
the table is the everyday use.

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

## Failure is not a gate

This stage's failures **do not** roll back the upstream qty++ and
cache learn from [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md).
The recognition pipeline's
[Pipeline failure modes](idea-007-visual-recognition-dinov2-vlm.md#pipeline-failure-modes--what-doesnt-gate-the-write)
spell it out from the upstream side; restating here for findability
when reading IDEA-008 standalone:

- **No `$PL_NEXAR_CLIENT_ID`** (offline mode, no credentials) — this
  stage **silently skips**. The qty++ already happened; the
  datasheet / manufacturer / package cells land empty. Maker fills
  them in later by hand or re-runs enrichment when the key is set.
- **Network unreachable** — same as above. Silent skip, log line,
  no viewfinder verdict.
- **Nexar returns no match and the family-datasheet fallback also
  misses** — the relevant cells land empty as documented in the
  *Fallback path* above. Other cells the API *did* return still
  populate.
- **Nexar returns `Obsolete`** — the part is still written; the
  *Notes* cell carries the obsolescence flag (see open questions
  for the exact UX).

The unifying principle: **the maker's identification work is never
wasted because the API was down**. The inventory MD is the source
of truth; metadata is decoration the maker can repair later. The
camera-path pipeline upstream has no concept of "enrichment failed"
as a recoverable error — it just sees the writer return and moves
on.

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
| Enrichment orchestrator + INVENTORY.md writer wiring | This repo | ⏳ planned |
| Camera-path async dispatch | This repo | ⏳ planned |
| Skill-path sync invocation + page-gen chain | This repo (this dossier) + [IDEA-005](idea-005-skill-path-today.md#planned--auto-trigger-on-row-creation) (the receive side) | ⏳ planned |

## Execution plan

Six stages, each implementable in isolation with explicit validation.
Forward-only dependencies. The whole rollout assumes
[IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) is being built
in parallel — Stage 5 needs IDEA-007's recognition pipeline as the
upstream trigger, and Stage 6's page-generation chain needs
[IDEA-005's matching auto-trigger stage](idea-005-skill-path-today.md#planned--auto-trigger-on-row-creation)
(see *Out of scope for this rollout* below).

### Stage 1 — Nexar GraphQL client + OAuth

**Goal.** Bring up the bare HTTP/GraphQL transport in isolation:
OAuth client-credentials against Nexar's identity endpoint, single
GraphQL POST to the data endpoint, parsed response. Nothing
pipeline-shaped yet.

**Changes:**

1. New module `partsledger/enrichment/nexar.py` — reads
   `$PL_NEXAR_CLIENT_ID` and `$PL_NEXAR_CLIENT_SECRET` per
   [CLAUDE.md § Project env vars](../../../../CLAUDE.md#project-env-vars--use-pl_-never-hard-code-paths).
   Exposes `query_mpn(mpn: str) -> NexarPart | None`. Token caching
   in-memory for the session.
2. `NexarPart` dataclass holding `mpn`, `manufacturer`,
   `datasheet_url`, `category_path`, `lifecycle_status` — exactly the
   fields named in the
   [Primary path field-mapping table](#primary-path--nexar-graphql-api).
3. Secrets discipline mirroring
   [IDEA-007 § Secrets handling](idea-007-visual-recognition-dinov2-vlm.md#secrets-handling):
   bearer token and raw client-secret redacted in every log line,
   error message, and stack trace. A failed auth logs *"auth failed
   against `https://identity.nexar.com`"*, never the credential value.

**Validation:**

- A live call with valid credentials against `LM358N` returns a
  populated `NexarPart` with non-empty `datasheet_url`.
- A call with a junk MPN returns `None` rather than raising.
- A call with `$PL_NEXAR_CLIENT_ID` unset raises
  `EnrichmentDisabledError` cleanly — caller can `except` it
  without parsing a traceback.
- An induced 401 logs the redacted form; no credential string
  appears anywhere in captured logs.

**Dependencies.** None within PartsLedger. `requests` already
present in [`pyproject.toml`](../../../../pyproject.toml#L46).

### Stage 2 — Response cache (SQLite)

**Goal.** Wrap Stage 1 in a per-MPN cache so repeat enrichment of
the same part is instant and survives process restart.

**Changes:**

1. New module `partsledger/enrichment/cache.py` — opens / creates
   `inventory/.embeddings/nexar_cache.sqlite`. Schema:
   `mpn TEXT PRIMARY KEY, payload_json TEXT, lifecycle TEXT,
   cached_at INTEGER` (epoch seconds).
2. API: `get(mpn) -> dict | None`, `put(mpn, payload, lifecycle)`,
   `expire_stale()`. TTL policy from
   [Cache policy](#cache-policy): 30 days for `Active`, never for
   `Obsolete` / `NRND`.
3. Regenerable — `expire_stale()` is the only path that deletes
   rows; never bulk-clear. Same ethos as the embedding cache in
   [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md#vector-db).

**Validation:**

- `put` then `get` round-trips the payload byte-identical.
- `get` for an `Active` row older than 30 days returns `None` and
  the next call re-fetches from Nexar.
- `get` for an `Obsolete` row from any past date still returns the
  cached payload — `lifecycleStatus` is frozen anyway.
- Cache file survives process restart and a fresh module import.

**Dependencies.** None. Stage 1's `NexarPart` is serialised via
`dataclasses.asdict` + `json.dumps` — no schema migration concern.

### Stage 3 — Family-datasheet fallback

**Goal.** Static table that maps MPN prefix → fallback datasheet
URL when Nexar returns nothing. Codifies the logic
[IDEA-005's `/inventory-add` skill](idea-005-skill-path-today.md#inventory-add-part-id-qty-also-batched--part-id-qty)
applies today via `WebSearch`.

**Changes:**

1. New module `partsledger/enrichment/family_datasheets.py` —
   `lookup(mpn) -> str | None` matches the MPN against a
   prefix-keyed dict and returns a known-good manufacturer URL or
   `None`.
2. Initial table seeded from the MPN families already present in
   [`inventory/parts/`](../../../../inventory/parts/): `LM358-`,
   `LM386-`, `TL08x-`, `NE555-`, `L7805-`, `PIC16F62x-`. Extension
   by hand-edit — no dynamic discovery, no scraping.
3. If even the fallback misses, the caller leaves the Datasheet
   cell empty per
   [Fallback path](#fallback-path--generic-family-datasheet).
   Empty is honest; a wrong URL rots without notice.

**Validation:**

- `lookup("LM358N")` returns the TI LM358 datasheet URL.
- `lookup("XYZ123")` returns `None` without raising.
- Module is a plain Python dict, no file I/O — keeps the fallback
  dependency-free and grep-able.

**Dependencies.** None.

### Stage 4 — Orchestrator + INVENTORY.md writer integration

**Goal.** Assemble Stages 1–3 behind a single `enrich(part_id)`
entry point and wire its output into the (planned) INVENTORY.md
writer.

**Changes:**

1. New module `partsledger/enrichment/__init__.py` — exposes
   `enrich(part_id: str) -> EnrichmentResult`. Variants:
   `Enriched(payload)`, `NoEnrichment(reason)`. Reasons enumerate
   the four soft-fail cases from
   [Failure is not a gate](#failure-is-not-a-gate):
   `offline`, `network_unreachable`, `unknown_mpn`,
   `fallback_missed`.
2. Pipeline: `cache.get(mpn)` → on miss, `nexar.query_mpn(mpn)` →
   `cache.put(mpn, payload, lifecycle)` → on no-datasheet,
   `family_datasheets.lookup(mpn)` → assemble result.
3. Writer side: extend the INVENTORY.md row writer (the same one
   [IDEA-007 Stage 4](idea-007-visual-recognition-dinov2-vlm.md#stage-4--pipeline-glue--branching)
   uses for cache-learn writes) to accept an `EnrichmentResult` and
   fill the Description / Datasheet / Notes cells.
4. **Idempotency rule** — the writer never clobbers a non-empty
   cell. If the maker has hand-edited Description, re-running
   `enrich()` leaves it alone. Only empty cells get filled.
5. Manufacturer name lives in the Stage 2 response cache, **not**
   in INVENTORY.md as a column — page generation (Stage 6) reads
   it from the cache directly.

**Validation:**

- Fresh enrichment on `LM358N` populates Description, Datasheet,
  and Notes (package; lifecycle only if not `Active`).
- Re-running `enrich()` on the same row is a no-op — the writer
  finds the cells already populated and exits clean.
- Hand-editing Description, then re-running, preserves the
  hand-edit.
- `$PL_NEXAR_CLIENT_ID` unset → `NoEnrichment(reason='offline')`
  and zero MD writes.
- Forced Nexar miss + family-table miss →
  `NoEnrichment(reason='fallback_missed')` and zero MD writes
  beyond the Description (which is generated from the
  identification result upstream, not from this stage).

**Dependencies.** Stages 1 + 2 + 3. INVENTORY.md writer signature
is shared with IDEA-007 Stage 4 — whichever stage lands second
plugs into the shape already chosen.

### Stage 5 — Camera-path async dispatch

**Goal.** Wire `enrich()` to IDEA-007's recognition pipeline as a
fire-and-forget background job. The capture loop never blocks on
network I/O — the
[silent-qty++ promise](idea-007-visual-recognition-dinov2-vlm.md#the-recognition-pipeline)
stays intact.

**Changes:**

1. New module `partsledger/enrichment/dispatch.py` — exposes
   `dispatch_async(part_id)` that submits `enrich(part_id)` to a
   bounded background worker
   (`concurrent.futures.ThreadPoolExecutor(max_workers=1)`).
   `max_workers=1` is enough at hobbyist cadence and avoids the
   Nexar-rate-limit failure mode.
2. IDEA-007 Stage 4's pipeline hook calls
   `dispatch_async(part_id)` right after the cache-learn step and
   then returns to *ready for next capture* immediately. The
   mermaid edge `LEARN → NX → READY` in
   [§ The recognition pipeline](idea-007-visual-recognition-dinov2-vlm.md#the-recognition-pipeline)
   collapses: NX becomes a non-blocking dispatch and `READY`
   fires on the same tick as `LEARN`.
3. Background-task errors are logged to a session log at
   `inventory/.embeddings/enrichment.log` and otherwise silently
   dropped — they do not surface to the viewfinder. Maker sees
   normal operation; the row's metadata cells just stay empty
   until a successful retry.

**Validation:**

- A capture that triggers a first-sighting row returns control to
  the viewfinder in < 50 ms, irrespective of Nexar latency.
- 60 seconds later (with network up), the row's Description /
  Datasheet / Notes cells are populated.
- A capture during a known-offline session still completes
  silently; `enrichment.log` records *"offline, skipped"*.
- A capture that triggers Nexar's rate-limiter generates one log
  line, no viewfinder warning, no retry storm.

**Dependencies.** Stage 4. IDEA-007 Stage 4 for the pipeline hook
that calls `dispatch_async`.

### Stage 6 — Skill-path sync invocation + page-generation chain

**Goal.** Wire `enrich()` to the synchronous skill path
(`/inventory-add`) and chain page generation per the
[closed Page-generation trigger question](#open-questions-to-hone).

**Changes:**

1. `/inventory-add` skill — after writing a new row, calls
   `enrich(part_id)` **synchronously**. The maker is already
   interactive; one extra Nexar round-trip (~300 ms) is fine.
2. After enrichment returns, the skill chains into
   `/inventory-page <part-id>` synchronously. Page-gen lands the
   per-part reference page using the just-enriched metadata
   (datasheet URL + description + package from INVENTORY.md,
   manufacturer from the Stage 2 cache).
3. Camera path (Stage 5) emits the same chain async: once
   `dispatch_async` resolves and `enrich()` returns `Enriched(...)`,
   the dispatcher queues a page-gen job in the same background
   worker. The page-gen worker reads INVENTORY.md + the response
   cache, generates the page, writes it. No viewfinder feedback.
4. Page-generation mechanism itself is owned by
   [IDEA-005](idea-005-skill-path-today.md#planned--auto-trigger-on-row-creation)
   — this stage delivers only the dispatch glue (the
   `/inventory-page <part-id>` invocation). IDEA-005's matching
   stage owns the page-writing.

**Validation:**

- `/inventory-add LM358N 1` against an empty inventory: row lands,
  enrichment runs, page-gen runs, `inventory/parts/lm358n.md`
  exists with content sourced from the Nexar-supplied datasheet.
- `/inventory-add LM358N 1` against an existing row (qty bump
  only): no re-enrichment, no page-gen, qty cell incremented.
- Camera-path first-sighting: row lands silently with `qty: 1`,
  viewfinder returns to *ready* immediately, page appears in
  `inventory/parts/` within ~10–30 s (LLM page-gen latency).
- Camera-path repeat sighting: silent `qty++`, no enrichment, no
  page-gen — both already done on first sighting.

**Dependencies.** Stage 4 and
[IDEA-005's auto-trigger execution-plan stage](idea-005-skill-path-today.md#planned--auto-trigger-on-row-creation).
Without IDEA-005's stage, the chain dispatches into a no-op
skill; with it, the page lands.

### Out of scope for this rollout

- **Page-generation skill internals** — owned by
  [IDEA-005](idea-005-skill-path-today.md#planned--auto-trigger-on-row-creation).
  This stage contracts only the *dispatch* edge; the *receive*
  edge (reading metadata, writing the page) lands in IDEA-005's
  own execution plan.
- **VLM date-code reading** — owned by
  [IDEA-007 § Stage 2](idea-007-visual-recognition-dinov2-vlm.md#stage-2--vlm-identification).
  IDEA-008 does not parse the part body.
- **Lifecycle UX warnings** — explicitly closed in
  [Open questions § Obsolete-part handling](#open-questions-to-hone).
  Lifecycle lands as a neutral Notes cell, no warning emoji, no
  refuse-to-add.
- **Cache rebuild / clear policy** — closed at *Cache TTL*: an
  implementation detail revisited only if cache-hit rates surface
  a real issue.
- **Enrichment test fixtures** (mocked Nexar responses, recorded
  datasheets) — designed at task time. Each stage above names
  what it validates against; the fixture corpus is implementation
  work, not dossier work.

### Implementation order suggestion

Stages 1, 2, 3 are independent and can land in parallel PRs.
Stage 4 sequences after them. Stage 5 needs Stage 4 + IDEA-007
Stage 4 (whichever lands second wires the hook). Stage 6 needs
Stage 4 + IDEA-005's matching auto-trigger stage. A two-PR
rollout is reasonable: **PR-A bundles 1+2+3+4** (standalone
enrichment, testable in isolation), **PR-B bundles 5+6** (the
dispatch glue, once IDEA-007 and IDEA-005 have their matching
stages).

## Open questions to hone

- ~~**Nexar vs Octopart vs Mouser direct.**~~ *Closed 2026-05-14.*
  **Nexar stays the only path**, and pricing / stock data is
  explicitly out of scope. The maker has no interest in either — the
  inventory is *"do I own one?"*, not *"can I still order one?"*.
  Nexar is the publisher-blessed GraphQL endpoint, covers all four
  cells this stage writes (datasheet, manufacturer, package,
  lifecycle), and integrates as one HTTP client. Mouser's fatter
  API and Octopart's web-search fallback both add surface area
  without buying anything the maker wants.
- ~~**OCR vs VLM-as-OCR.**~~ *Closed 2026-05-14.* **VLM-as-OCR, no
  classical OCR dependency**, and the question moves out of this
  dossier entirely — reading the part's identifying surface (DIP
  marking text *or* resistor colour bands) is *identification* work,
  owned by [IDEA-007 § Stage 2 — VLM identification](idea-007-visual-recognition-dinov2-vlm.md#stage-2--vlm-identification).
  Claude Opus Vision and Pixtral both read resistor bands well enough
  for standard E-series values, so no `pytesseract` / `paddleocr` /
  `cv2` colour-segmentation fork is needed. IDEA-008 only sees the
  resolved part-ID and proceeds with metadata enrichment.
- ~~**Cache TTL.**~~ *Closed 2026-05-14.* **Implementation detail.**
  The 30-days-active / never-obsolete default in
  [Cache policy](#cache-policy) is a reasonable starting point;
  edge cases like `Active → NRND` mid-window get refined at
  implementation time once there's real cache-hit data to look at.
  Not a dossier-level concern.
- ~~**Obsolete-part handling.**~~ *Closed 2026-05-14.* **Neither
  refuse nor flag with a warning.** The maker's view: *"my hoard,
  my precious — just because it's obsolete from a product manager
  perspective doesn't make the part obsolete; if it's in my
  inventory and I can use it, I will use it"*. So no warning emoji,
  no UX special-casing, no refuse-to-add. The `lifecycleStatus`
  field still lands as a neutral one-liner in the *Notes* cell
  (per the [Primary path](#primary-path--nexar-graphql-api)
  field-mapping table) when Nexar reports anything other than
  `Active` — useful as factual reference if the maker later goes to
  *re*-order, irrelevant to day-to-day use.
- ~~**Image upload.**~~ *Closed 2026-05-14.* **No.** PartsLedger
  stores zero images — not downloaded from Nexar, not retained from
  the capture pipeline. The capture frames from
  [IDEA-006](idea-006-usb-camera-capture.md) feed the
  [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) recognition
  pipeline and are dropped afterwards (the embedding lives on, the
  source image does not). Consistent with the MD-as-source-of-truth
  ethos: an image directory under `inventory/parts/<id>/` would be
  one more thing to back up and one more way the inventory drifts
  from its regenerable artefacts. The `bestImage { url }` field
  is removed from the GraphQL query above.
- ~~**Multi-MPN responses.**~~ *Closed 2026-05-14.* **Pick top-1
  from Nexar's relevance ranking; no maker dialog.** By the time
  this stage runs, [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md)
  has already produced a canonical part-ID — the VLM read the
  marking text and disambiguated LM358N from LM358P upstream. If
  Nexar still returns multiple candidates for that canonical MPN,
  that's a metadata-decoration ambiguity not worth pulling the
  maker back into a TUI for. The query already uses `limit: 1`;
  Nexar's relevance ranking decides. Wrong manufacturer in the
  *Notes* cell is a hand-edit away — wrong part-ID would have been
  caught by [IDEA-007's tight-band ambiguity refinement](idea-007-visual-recognition-dinov2-vlm.md#the-recognition-pipeline)
  long before reaching here.
- ~~**Page-generation trigger.**~~ *Closed 2026-05-14.*
  **Auto-on-row-creation.** As soon as a new row lands in
  `INVENTORY.md` — whether via the camera path or `/inventory-add` —
  page generation fires. Two execution profiles per path
  (async background for the camera path, synchronous for the skill
  path) are documented in
  [Where this metadata gets used § Auto-trigger semantics](#primary--parts-page-generation).
  The trigger mechanism itself lives in
  [IDEA-005](idea-005-skill-path-today.md) — that dossier needs a
  matching execution-plan stage to wire `/inventory-add` to
  `/inventory-page` and to expose an entry-point the camera path can
  call.
- ~~**Offline-mode UX.**~~ *Closed 2026-05-13.* **Silent skip** is
  correct. No one-time prompt, no viewfinder verdict. Pulling the
  maker into a *"you're running offline; fine?"* dialog on the
  first capture of every session would punish the deliberately
  offline maker (see
  [IDEA-010 § Fully offline mode](idea-010-local-vlm-hosting.md#fully-offline-mode--when-this-matters)).
  The log line is the receipt; the empty cells are the reminder.

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
