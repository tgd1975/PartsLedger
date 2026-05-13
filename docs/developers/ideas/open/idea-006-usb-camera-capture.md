---
id: IDEA-006
title: USB camera capture — the camera-path front door
description: How the 2K USB webcam sees a part. Capture trigger UX, framing, lighting, OpenCV plumbing, $PL_CAMERA_INDEX. The first toolchain stage that has to be reliable before anything downstream is worth tuning.
category: camera-path
---

> *Replaces the camera-path "USB camera capture" stage from the retired
> IDEA-001 dossier.* The cheap, well-understood part of the camera
> pipeline — but only **after** the capture ergonomics are nailed. A
> downstream VLM cannot recover from a blurry, off-axis, badly lit photo.

## Status

⏳ **Planned.** No code yet. The 2K USB webcam is already on the desk;
`$PL_CAMERA_INDEX` is the env var the rest of the pipeline will read.

## What this stage owns

The pipeline edge between the physical part on the bench and the first
in-memory image tensor:

```text
hardware → OpenCV → numpy image
                       │
                       ▼
              downstream stages (IDEA-007)
```

Concretely: opening the camera device, framing/cropping the part,
triggering capture, handing a clean image to the recognition stage. **No
identification work happens here** — that's [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md).

## Hardware assumptions

- **Camera**: 2K USB webcam already in use (the maker's own; brand-
  agnostic). Connected via USB-A.
- **Lighting**: ring light around the lens or a desk lamp at a fixed
  angle. Lighting consistency matters more than absolute brightness —
  DINOv2 embeddings are sensitive to harsh shadows.
- **Surface**: matte mat, ideally a single contrasting colour (white or
  black). Reflective surfaces (a steel desk) confuse both DINOv2 and
  the VLM.
- **No microscope.** SMD micro-marking codes (`A6`, `T4`) are
  deliberately out of scope; this is a webcam for through-hole / DIP /
  module-sized parts.

## Software stack

| Job | Library |
|---|---|
| Device open / frame grab | `cv2.VideoCapture` (OpenCV) |
| Frame buffering | numpy arrays |
| Trigger UI | TBD (see open questions) |
| Pre-flight check | `cv2.VideoCapture(int($PL_CAMERA_INDEX)).isOpened()` |

Heavy dep: OpenCV is one of the bigger Python packages PartsLedger pulls
in (see [CLAUDE.md § Missing executables](../../../../CLAUDE.md#missing-executables)).
Worth gating with `/check-tool cv2` at runtime.

## Capture trigger UX — the central open question

The hand-eye loop is the user-facing core of the camera path. Three
candidate triggers, none ideal alone:

### Option A — keyboard hotkey

Maker holds part under camera with one hand, taps `<Space>` (or similar)
with the other. Familiar, zero hardware, but constrains the maker to a
two-handed pose.

### Option B — foot pedal

USB foot pedal (`HID`-compatible, ~€20) frees both hands. Best for batch
sessions ("rip through a tray of new arrivals"). Extra hardware on the
desk; needs HID glue.

### Option C — auto-detect "part placed"

OpenCV background-subtraction watches the mat; when stable motion stops,
auto-trigger. Most ergonomic on paper; most failure-prone in practice
(shadows count as motion, two parts in frame both trigger).

A pragmatic answer is probably **A first, B and C as polish**.

## Framing & quality requirements

Driven by downstream needs from [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md):

- **Resolution**: the 2K sensor is generous. Downstream DINOv2 wants
  ≥ 224×224 of the *part* (not the frame); the VLM reads marking text,
  so at least ~10 px per character is the operational minimum.
- **Focal distance**: fixed working distance (a marked rectangle on the
  mat) avoids re-focus latency and makes embedding-space neighbours
  comparable across sessions.
- **Autofocus**: helps for varied part sizes, hurts for consistent
  embedding distances. **Worth honing** — manual focus on a fixed jig
  vs autofocus with a "lock when stable" heuristic.
- **Background**: single colour, no clutter. The DINOv2 backbone will
  pick up *anything* in frame as feature signal.

## Output contract to downstream

A successful capture yields:

```text
image: np.ndarray  (H, W, 3), BGR uint8 (OpenCV native)
metadata: {
  timestamp: ISO 8601,
  camera_index: int,
  resolution: (W, H),
  trigger: "keyboard" | "pedal" | "auto",
}
```

The metadata block rides along into the per-capture record, even if it
isn't persisted in the inventory itself — useful for the active-learning
loop in IDEA-007.

## Open questions to hone

- **Trigger choice.** A / B / C above, or some combination.
- **Multi-angle workflow.** A single still rarely shows the part's
  marking *and* its pin pattern. Capture loop that asks "rotate 90°" and
  takes a burst? Stitch multiple stills into a contact-sheet for the
  VLM? Average DINOv2 embeddings across angles?
- **Calibration ritual.** Should a session start with a known reference
  part (an LM358N taped to the mat) so the pipeline can verify lighting
  hasn't drifted from the embedding cache's distribution?
- **Autofocus policy.** Lock at fixed working distance, or let the
  camera autofocus per shot?
- **Live preview vs blind capture.** Always show a viewfinder window,
  or only capture+confirm? The viewfinder helps framing but adds a
  display dependency on headless machines.
- **Image retention.** Keep captures forever (for re-training the
  embedding cache after a model upgrade)? Discard after a successful
  identification? Configurable retention window?
- **Pedal hardware choice.** Generic HID foot pedal — any
  vendor-specific compatibility traps with Linux + Windows 11 (the two
  dev OSes; see [CLAUDE.md § OS context](../../../../CLAUDE.md#os-context))?

## Related

- [IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) — the immediate
  downstream consumer of the image.
- [IDEA-008](idea-008-metadata-enrichment.md) — also reads images, but
  only for the optional resistor-band OCR fork.
- [IDEA-005](idea-005-skill-path-today.md) — the already-working
  alternative to the camera path; useful sanity check when the camera
  pipeline misidentifies.
