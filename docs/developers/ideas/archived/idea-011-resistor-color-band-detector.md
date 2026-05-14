---
id: IDEA-011
title: Resistor color band detector (spinoff tool)
description: Spinoff tool — identify resistor values from photo color bands and verify uniform value across image. Covers the off-bench / no-VLM-setup case that PartsLedger's camera path ([IDEA-007]) deliberately doesn't.
category: tooling
---

## Archive Reason

2026-05-14 — Promoted to EPIC-008 (resistor-reader), tasks TASK-051..TASK-056.

A small standalone utility — sibling to CircuitSmith rather than core to it —
that takes a photograph of one or more through-hole resistors and reports the
nominal resistance value of each, plus a sanity flag if the image is supposed
to contain a uniform batch but doesn't.

## Motivation

Two use cases neither covered by PartsLedger's camera path:

1. **Off-bench / no-setup workflow.** A maker with their phone in front of
   a junk drawer, a workshop visitor at someone else's bench, a teaching
   context — anywhere the USB-webcam + VLM + inventory setup isn't installed.
   A phone photo → value-report tool has zero setup cost and zero network
   dependency.
2. **Bench-side batch sanity check.** A bag of resistors sold or kitted as
   one value but actually mixed. PartsLedger's camera path is
   one-part-per-capture by contract
   ([IDEA-006 § Capture contract](idea-006-usb-camera-capture.md#capture-contract--one-object-per-photo)),
   so "are these 20 all the same?" would need 20 separate captures. This
   tool reads them all from one photo and reports `uniform` / `mixed`.
   Catching a mixed batch visually before they go into a board is much
   cheaper than debugging the assembled circuit.

PartsLedger's
[VLM in IDEA-007](idea-007-visual-recognition-dinov2-vlm.md#stage-2--vlm-identification)
covers the on-bench, in-inventory case — colour bands are read inline as
part of identification, no separate tool needed there. This dossier exists
for the cases the PartsLedger camera path deliberately *can't* serve. The
colour-band code is unambiguous in theory but painful in practice — small
bands, poor lighting, ambiguous red/orange/brown, faded gold/silver
tolerance bands — and worth a standalone tool when the full PartsLedger
stack isn't on hand.

## Two modes

The tool ships in two flavours sharing the same decoding core:

1. **Still-image mode (V1).** User takes a photo on demand (phone, webcam,
   scanner), feeds it to the tool, gets a report. Single-shot, batch-friendly,
   no realtime constraint. Classical CV is probably sufficient here — the
   pipeline can afford to be slow and thorough on one frame.
2. **Live-view mode (V2).** A camera feed (laptop webcam, phone-as-webcam,
   Pi camera) is processed in realtime with an on-screen overlay showing the
   decoded value next to each visible resistor. Useful at the bench: pick up
   a resistor, hold it to the camera, see the value. The realtime constraint
   (≥10 fps on commodity hardware) and the need to handle motion blur and
   varying focus distance push this toward a small trained detector + band
   classifier rather than pure HSV thresholding — i.e. **PyTorch is
   probably unavoidable** for V2, whereas V1 can stay dependency-light.

V1 should ship first; V2 is a separate effort built on V1's decoding
primitives.

## Scope (rough)

In scope (V1, still-image):

- Single image input (phone photo, scanner, etc.) containing one or more
  through-hole axial resistors.
- 4-band and 5-band color codes; ±tolerance band detection.
- Per-resistor output: nominal value, tolerance, confidence score.
- Batch-uniformity check: report `uniform` / `mixed` plus which resistors
  deviate.

In scope (V2, live-view), additionally:

- Webcam / video-stream input at ≥10 fps on commodity laptop hardware.
- On-screen overlay: bounding box + decoded value per visible resistor.
- Stable decoding across frames (no flicker between candidate values when
  the resistor is held still).

Out of scope (for both versions, first cut):

- SMD resistors (numeric markings, completely different problem).
- AR / phone-app packaging — V2 is desktop-first.
- Integration with PartsLedger as a write-path (inventory entry stays manual
  for now; this tool just *reports* the value).

## Rough approach

Two halves, roughly independent:

1. **Resistor localisation.** Segment the image into bounding boxes around
   each resistor body.
   - V1: classical CV (HSV thresholding on the typical beige/blue body,
     contour finding) probably works on a still photo with reasonable
     framing.
   - V2: a small trained detector (YOLO-nano, MobileNet-SSD, or similar)
     run via PyTorch — the realtime + cluttered-bench + motion-blur
     combination makes the classical approach too brittle.
2. **Band reading.** Within each resistor's box, find the band positions
   along the body axis, sample each band's dominant colour, and classify
   against the EIA colour table. Orientation ambiguity (which end is band 1?)
   is resolved by checking which decoding produces an E-series-compliant
   value; ties get flagged as low-confidence. This stage is shared between
   V1 and V2 — same decoder, different upstream localisation.

Once each resistor has a decoded value + confidence, the uniformity check is
trivial: cluster the values, flag any cluster smaller than `n - 1`. (In V2,
this becomes "are all *currently visible* resistors the same value?".)

## Open questions

- ~~**Spinoff repo or sub-package?**~~ *Closed 2026-05-14.* **Sub-package
  inside PartsLedger.** The CV stack (OpenCV today, PyTorch for V2, the
  DINOv2 work from [IDEA-007]) already lives here, so a `resistor_reader/`
  sub-package re-uses the same dependency set instead of duplicating it in
  a sibling repo. Distribution shape **also closed 2026-05-14**: shipped
  as an optional extra on the PartsLedger distribution — `pip install
  partsledger[resistor-reader]` pulls the core inventory machinery plus
  the resistor decoder; `pip install partsledger` alone leaves the
  heavier CV deps out. A separately-named distribution from the same
  source tree was considered and rejected: it would mean two PyPI
  publications for one source tree, more release ceremony, and a
  CircuitSmith dependency that has to choose between the two names.
  Extras keep one distribution, one publish step, and let off-bench /
  standalone callers — and CircuitSmith via its existing PartsLedger
  dependency for `--prefer-inventory` — pull just the decoder without
  the rest of the inventory machinery. Phone-only distribution (web
  app, mobile bundle) stays out of scope; off-bench desktop use is
  the supported case. Sequencing consequence: implementation work
  here is gated on [IDEA-014](idea-014-project-setup-review-vs-circuitsmith.md)'s
  Phase 0b landing first (the `src/partsledger/` layout has to exist
  for `resistor_reader/` to live inside it). See
  [IDEA-012 § Phase 6](idea-012-integration-pass.md#phase-6--sibling-tool-idea-011).
- ~~**Calibration card?**~~ *Closed 2026-05-14 — split out.*
  **Owned by [IDEA-013](idea-013-capture-setup-and-color-calibration.md).**
  The calibration story is cross-cutting (DINOv2 drift in [IDEA-007],
  VLM colour-name confusion, this decoder) and got promoted to its own
  dossier alongside the broader capture-setup / lighting-tier guide.
  This decoder is a *consumer* of the colour profile IDEA-013 produces:
  load the latest profile (if any) before band classification; no
  profile → fall back to white-balance-naive decoding and surface that
  in the report as lower baseline confidence.
- ~~**Confidence threshold for `uniform` claim.**~~ *Closed 2026-05-14.*
  **Strict uniformity — flag every deviation.** The user's intent when
  feeding a batch image is "these are all the same value", so any decoded
  difference is signal worth surfacing, not noise to smooth away. Cluster
  on the raw decoded value (no confidence-weighting); report the modal
  value plus an explicit list of every resistor whose decoded value
  differs, regardless of that resistor's confidence score. Low confidence
  on an outlier is itself a reason to show it to the user (re-shoot or
  inspect by hand) rather than a reason to discount it. Per-resistor
  confidence still appears in the report for inspection.
- ~~**Relationship to PartsLedger.**~~ *Closed 2026-05-14.* **Stay
  independent.** A maker who uses this tool off-bench and later wants to
  record the parts uses the existing skill path
  ([IDEA-005](idea-005-skill-path-today.md)): `/inventory-add 4k7 5` on
  their workstation. No special write-API on the PartsLedger side, no
  reverse import here. The only contract between the projects is
  **value-formatting compatibility** — `4k7`, `100Ω`, `1M` must match the
  [PartsLedger schema](idea-004-markdown-inventory-schema.md) so a
  copy-paste of this tool's output works as `/inventory-add` input.
