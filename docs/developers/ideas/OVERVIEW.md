# Ideas Overview

**Open: 3** | **Archived: 11**

Ideas are lightweight, qualitative proposals tracked in [`open/`](open/) until they are either converted into structured tasks or archived. Archived ideas are kept for history in [`archived/`](archived/). See [README.md](README.md) for the file-naming convention (one row per IDEA, sub-notes use the `idea-NNN.<sub-slug>.md` form).

## Open Ideas

| ID | Category | Title | Description |
|----|----------|-------|-------------|
| [IDEA-003](open/idea-003-external-inventory-tool-integration.md) | integration | External inventory tool integration | Add an interface to an existing electronics inventory tool (InvenTree / PartKeepr / Partsbox) for import, export, or sync of parts data. |
| [IDEA-010](open/idea-010-local-vlm-hosting.md) | camera-path | Local model hosting — VLM and embedding backbone, Ollama-first, fully offline mode | Local hosting of all camera-path models — VLM (Pixtral et al. via Ollama / vllm / llama.cpp) and DINOv2 embedding backbone (via torch.hub). Owns the fully-offline story. |
| [IDEA-013](open/idea-013-capture-setup-and-color-calibration.md) | foundation | Capture setup and color calibration | Photo capture quality across every vision pipeline — bench setup tiers from makeshift to studio, plus a printed calibration card and persistent color profile consumed by the camera path ([IDEA-006-008]) and the resistor reader ([IDEA-011]). |

## Archived Ideas

| ID | Category | Title |
|----|----------|-------|
| [IDEA-001](archived/idea-001-partsledger-concept.md) | foundation | PartsLedger concept (superseded — split 2026-05-13) |
| [IDEA-002](archived/idea-002-align-with-circuitsmith.md) | foundation | Align PartsLedger with CircuitSmith framework |
| [IDEA-004](archived/idea-004-markdown-inventory-schema.md) | foundation | Markdown inventory schema |
| [IDEA-005](archived/idea-005-skill-path-today.md) | 🛠️ tooling | Skill path — /inventory-add and /inventory-page (today, as-built) |
| [IDEA-006](archived/idea-006-usb-camera-capture.md) | camera-path | USB camera capture — the camera-path front door |
| [IDEA-007](archived/idea-007-visual-recognition-dinov2-vlm.md) | camera-path | Visual recognition — DINOv2 similarity cache + VLM identification |
| [IDEA-008](archived/idea-008-metadata-enrichment.md) | camera-path | Metadata enrichment — Nexar/Octopart |
| [IDEA-009](archived/idea-009-circuitsmith-prefer-inventory-adapter.md) | integration | CircuitSmith --prefer-inventory adapter (moved to CircuitSmith) |
| [IDEA-011](archived/idea-011-resistor-color-band-detector.md) | 🛠️ tooling | Resistor color band detector (spinoff tool) |
| [IDEA-012](archived/idea-012-integration-pass.md) | foundation | Putting it all together — workflows, pipeline, sequence, gaps |
| [IDEA-014](archived/idea-014-project-setup-review-vs-circuitsmith.md) | 🛠️ tooling | Project setup review — mirror CircuitSmith's release + module layout |
