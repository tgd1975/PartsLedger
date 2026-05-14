---
id: IDEA-013
title: Capture setup and color calibration
description: Photo capture quality across every vision pipeline — bench setup tiers from makeshift to studio, plus a printed calibration card and persistent color profile consumed by the camera path ([IDEA-006-008]) and the resistor reader ([IDEA-011]).
category: foundation
---

Every vision pipeline in this project — the [IDEA-006] viewfinder, the
[IDEA-007] DINOv2 + VLM identification, the [IDEA-011] resistor color-band
decoder — gets dramatically more reliable when the input image is taken
under consistent, diffuse light against a neutral background and white-
balanced against a known reference. This dossier owns that
**photographic-input-quality** story so the downstream pipelines don't
each re-invent it.

Two halves:

1. **Capture setup** — what the maker's bench looks like, from a phone
   on a stack of books to a small lightbox rig.
2. **Color calibration** — a printed reference card plus a one-shot
   calibration workflow that produces a persistent color profile every
   pipeline can load.

## Motivation

Three concrete problems this addresses, in increasing order of "without
this, the pipeline is brittle":

- **DINOv2 similarity drift across days** ([IDEA-007]). The same
  resistor photographed under a warm kitchen bulb and under cool
  fluorescent office light yields embeddings that differ enough to push
  a true match out of the tight band into the loose band, triggering
  spurious VLM calls and U-undo churn.
- **VLM color-name confusion**. Pixtral / Claude Vision read color band
  values from the image text, but ambiguous red/orange/brown and faded
  gold/silver tolerance bands are exactly the cases the model gets
  wrong — and exactly the cases that go away when the white balance is
  correct.
- **Resistor color-band decoder ([IDEA-011]) accuracy floor**. The
  decoder is a colour classifier with five-to-ten possible classes per
  band; under uncontrolled lighting its precision collapses regardless
  of how good the body-segmentation and band-localisation are.

Solving capture quality once, here, lifts the floor for every consumer.

## Setup tiers

The same maker uses different setups in different contexts — the
off-bench case from [IDEA-011] is a phone in a junk drawer, the
on-bench case from [IDEA-006] is the USB webcam. This dossier
documents each tier explicitly so the maker can pick the cheapest one
that meets their accuracy needs, and so the rest of the project can
state which tier each pipeline assumes as its baseline.

### Tier 0 — makeshift (zero budget)

What it is: phone on a stack of books, ambient room light, white
printer paper as a backdrop, hand holding the part if needed.

Cost: zero.

Good enough for:

- One-off identification of a part you already half-recognise, where
  the goal is "confirm 4k7 vs 47k", not "feed this into a database".
- The off-bench / workshop-visitor case from [IDEA-011].

Failure modes:

- Mixed lighting (overhead bulb + window daylight) produces split
  white balance across the frame — the calibration profile from a
  single corner won't generalise. Curtain the window or turn off the
  overhead.
- Phone-camera HDR aggressively re-tonemaps, killing the band-color
  signal. Disable HDR if the phone lets you; otherwise photograph in
  RAW.
- Soft shadows from a single overhead source crush red and brown into
  the same value. A second light source — even a desk lamp — fixes
  this more than any software does.

### Tier 1 — improvised bench (≈€20-50)

What it is: USB webcam on a desk mount or gooseneck, one or two desk
lamps with diffuser (a sheet of baking paper over the bulb is fine),
neutral grey or matte-white poster board as a backdrop, part on the
backdrop.

Cost: webcam already on hand for [IDEA-006]; add a €15 gooseneck mount
and a €10 desk lamp.

Good enough for:

- The default PartsLedger bench setup from [IDEA-006] — DINOv2
  embeddings stable across sessions, VLM identification reliable.
- Resistor color-band decoding ([IDEA-011]) with reasonable precision
  even without a calibration card.

Trade-offs:

- The webcam's fixed focus distance constrains how close you can put
  the part — typically 5-15 cm of usable depth-of-field. Plan the
  mount geometry around this.
- Single light source still produces directional shadows on cylindrical
  parts (resistor bodies, capacitor cans). Adding the second lamp is
  the biggest single quality jump on this tier.

### Tier 2 — small studio (≈€50-200)

What it is: small foldable lightbox or softbox tent (~30 cm cube),
dual diffused LED panels at fixed colour temperature (5500 K typical),
camera mounted to the lightbox's top port at a fixed distance, neutral
backdrop included with the box, optional cross-polarisation filter for
shiny / reflective parts (SMD pads, metallised film caps).

Cost: €40-80 for a basic lightbox kit; €30-100 for better LED panels;
optional €30 polarising filter set.

Good enough for:

- Anything in the project, with predictable quality.
- Photographing parts for the [IDEA-005] manual `/inventory-page`
  flow at a quality that makes the parts page look like product
  photography rather than a snapshot.
- Future archival captures of the whole bin where consistency across
  hundreds of photos matters.

Diminishing returns: once you're at Tier 2, the limiting factor
becomes the camera itself, not the lighting. A 2K USB webcam at this
tier is light-starved on small parts; a phone in this tier with HDR
disabled and a tripod outperforms the webcam.

### What the maker actually needs

Most makers will live in Tier 1 with occasional Tier 0 detours. Tier 2
is for someone who's already enjoying the project enough to spend
money on it; the project should not require it.

The capture card from the next section is what closes most of the
Tier 0 → Tier 1 gap without buying anything new — it normalises
out the lighting tier the photo was taken at.

## Color calibration

A small printed reference card (known colour swatches plus a neutral
grey patch and a pure-white patch) photographed in the same lighting
as the parts, used to compute a per-camera, per-lighting colour
transform that the vision pipelines apply to every subsequent image
until re-calibrated.

### Card design

In scope for a first cut:

- 6 colour swatches matched to the resistor color-band palette
  (red, orange, brown, yellow, green, blue) — these are the cases
  [IDEA-011] needs disambiguated.
- 1 neutral grey patch for white-balance correction.
- 1 pure-white patch for exposure normalisation.
- 1 pure-black patch for black-point.
- A QR or AprilTag fiducial in a corner so the calibration tool can
  auto-detect the card's position and orientation in a photo.

Shipped as a print-ready PDF in the project (or in the [IDEA-011]
sub-package) at a fixed physical size (e.g. credit-card-sized — fits
on the bench, fits in a wallet for off-bench use). The PDF includes
print instructions: matte paper, no glossy finish (kills the white
balance), no scaling.

### Workflow

1. Maker prints the card once. Keeps it on the bench (or in their
   wallet for off-bench).
2. Whenever lighting changes (new bench, different time of day, new
   bulb), maker runs the calibration step: places the card in the
   capture area, snaps one photo, runs `calibrate` (CLI flag or skill).
3. The tool detects the card via its fiducial, samples each swatch,
   solves for a colour transform (matrix + per-channel white-balance
   gain), and writes the resulting profile to a persistent location.
4. Subsequent captures from any pipeline auto-load the latest profile
   and apply the transform before classification / embedding /
   VLM-call.
5. Maker re-calibrates when the report says so — see *staleness
   detection* below — or whenever they notice colour drift.

### Persistence

Profile lives in a tool-managed location (see open question
*Profile storage location*). Persists across sessions. Re-calibration
overwrites; no profile history.

The profile is **per-bench / per-lighting-setup**, not
per-part. A maker with both a Tier 1 webcam bench and a Tier 0
phone-on-books rig has two profiles and the active profile is
selected by which camera the capture came from.

### Consumers

- **[IDEA-006] camera-path viewfinder**: applies the profile to
  every incoming frame before passing it down to [IDEA-007].
- **[IDEA-007] DINOv2 + VLM identification**: works on already-
  corrected frames; embedding cache stays valid across sessions
  because the lighting variation is normalised out.
- **[IDEA-011] resistor decoder**: applies the profile to the input
  photo before band classification; this is the biggest single
  precision win for that tool.
- **[IDEA-005] manual `/inventory-page` photos**: optional — the
  maker can apply the profile via a `--calibrate` flag on the
  capture-helper script if they care about consistency across
  parts pages.

The contract is one-way: pipelines *consume* the profile, never
write to it. The only writer is the `calibrate` step.

## Open questions

- **Profile storage location.** Three plausible homes: (a)
  `$PL_INVENTORY_PATH/.calibration/` — sibling to `.embeddings/`,
  travels with the inventory tree, but couples the calibration to a
  PartsLedger inventory which the [IDEA-011] sub-package's off-bench
  user might not have; (b) the platform user-config dir
  (`~/.config/partsledger/calibration/` on Linux, equivalents
  elsewhere) — independent of inventory, but invisible to the maker;
  (c) both, with the user-config copy as fallback when no inventory
  is configured. Lean: (c).
- **Per-camera profiles.** The profile needs to be selected by
  *which camera produced the photo* (Tier 1 webcam vs Tier 0 phone
  vs Tier 2 studio rig), not just "the latest". The camera-selection
  wizard in [IDEA-006] already names cameras by friendly name —
  reuse that naming as the profile key. For off-bench / [IDEA-011]
  use where the wizard isn't involved, the profile key needs another
  source (EXIF camera model? user-prompted on first use?).
- **Staleness detection.** Should the tool warn when a calibration
  profile is older than N days, or when a new incoming image's
  white-balance differs sharply from the profile's reference white?
  The latter is more useful (responds to actual drift, not calendar
  time) but requires a per-frame check that adds cost. Probably
  worth it.
- **Card colour fidelity vs printer accuracy.** A consumer inkjet
  print of "red" isn't exactly the manufacturing red of a resistor
  band. The calibration card normalises *the photo's* perception of
  the card, but the resistor band itself is a different physical
  pigment. Open question whether a single colour transform from card
  → reference is sufficient or whether [IDEA-011] needs a second
  calibration pass against a known-value resistor as ground truth.
- **Photographing the card alongside every batch.** An alternative
  to persistent profiles: require the card to be in every capture
  frame, so calibration is per-photo and never goes stale. Cheaper
  to implement, more friction for the maker. Discuss.
