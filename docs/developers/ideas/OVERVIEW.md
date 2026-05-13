# Ideas Overview

**Open: 7** | **Archived: 2**

Ideas are lightweight, qualitative proposals tracked in [`open/`](open/) until they are either converted into structured tasks or archived. Archived ideas are kept for history in [`archived/`](archived/). See [README.md](README.md) for the file-naming convention (one row per IDEA, sub-notes use the `idea-NNN.<sub-slug>.md` form).

## Open Ideas

| ID | Category | Title | Description |
|----|----------|-------|-------------|
| [IDEA-003](open/idea-003-external-inventory-tool-integration.md) | integration | External inventory tool integration | Add an interface to an existing electronics inventory tool (InvenTree / PartKeepr / Partsbox) for import, export, or sync of parts data. |
| [IDEA-004](open/idea-004-markdown-inventory-schema.md) | foundation | Markdown inventory schema | The two-file shape (INVENTORY.md flat index + parts/*.md prose pages), section taxonomy, family-page pattern, table-padding discipline, directory layout. The foundation every other toolchain piece reads and writes. |
| [IDEA-005](open/idea-005-skill-path-today.md) | 🛠️ tooling | Skill path — /inventory-add and /inventory-page (today, as-built) | The two LLM-orchestrated skills that write the inventory by hand. Already in use; documented here so the schema it writes ([IDEA-004]) is matched by the camera path ([IDEA-006-008]) and so the as-built behaviour is honable. |
| [IDEA-006](open/idea-006-usb-camera-capture.md) | camera-path | USB camera capture — the camera-path front door | How the 2K USB webcam sees a part. Capture trigger UX, framing, lighting, OpenCV plumbing, $PL_CAMERA_INDEX. The first toolchain stage that has to be reliable before anything downstream is worth tuning. |
| [IDEA-007](open/idea-007-visual-recognition-dinov2-vlm.md) | camera-path | Visual recognition — DINOv2 similarity cache + VLM identification | The brain of the camera path. Two-stage pipeline that turns a captured image into a part-ID guess. DINOv2 embeddings act as a similarity cache; on miss, a VLM (Claude Opus 4.7 Vision or Pixtral 12B) identifies the part. Includes the offline-mode story. |
| [IDEA-008](open/idea-008-metadata-enrichment.md) | camera-path | Metadata enrichment — Nexar/Octopart + optional resistor-band OCR | After identification ([IDEA-007]) names the part, this stage fills in the datasheet URL, manufacturer, package, lifecycle, and (optionally) reads colour bands on resistors. Optional in both senses — the maker can fill datasheets by hand and the project can stay fully offline. |
| [IDEA-009](open/idea-009-circuitsmith-prefer-inventory-adapter.md) | integration | CircuitSmith --prefer-inventory adapter | The bridge that lets CircuitSmith bias its component selection toward parts the maker already owns. Lives in the CircuitSmith repo, depends on the PartsLedger MD schema ([IDEA-004]). BOM gets three columns — needed / in stock / to order. |

## Archived Ideas

| ID | Category | Title |
|----|----------|-------|
| [IDEA-001](archived/idea-001-partsledger-concept.md) | foundation | PartsLedger concept (superseded — split 2026-05-13) |
| [IDEA-002](archived/idea-002-align-with-circuitsmith.md) | foundation | Align PartsLedger with CircuitSmith framework |
