# Tasks Overview

<!-- HEADER -->

<!-- markdownlint-disable-file MD033 -->

⚪ **Open: 21** | 🔵 **Active: 0** | 🟡 **Paused: 3** | 🟢 **Closed: 34** | **Total: 58** | ██████░░░░ 59%

**Jump to:** [Burn-up](#burn-up) · [Active Tasks](#active-tasks) · [Paused Tasks](#paused-tasks) · [Open Tasks](#open-tasks) · [Closed Tasks](#closed-tasks)

<!-- END HEADER -->

<!-- BURNUP:START -->
<a id="burn-up"></a>

_No git tag found yet — burn-up chart needs a release tag to anchor on._
<!-- BURNUP:END -->

<!-- GENERATED -->

## Active Tasks

_No active tasks._

## Paused Tasks

| ID | Title | Effort | Complexity | Status |
|----|-------|--------|------------|--------|
| [TASK-018](paused/task-018-inventory-split-support.md) | Multi-file INVENTORY.md split support + suggestion trigger | Large (8-24h) | Medium | 🟡 **paused** |
| [TASK-057](paused/task-057-pipeline-test-fixture-corpus.md) | Build pipeline test-fixture corpus under tests/fixtures/ | Medium (2-8h) | Senior | 🟡 **paused** |
| [TASK-058](paused/task-058-resistor-output-parser-test.md) | One-line parser test walking IDEA-011 V1 output through /inventory-add's parser | Small (&lt;2h) | Medium | 🟡 **paused** |

## Open Tasks

| ID | Title | Effort | Complexity | Status |
|----|-------|--------|------------|--------|
| [TASK-020](open/task-020-page-gen-auto-trigger.md) | Auto-trigger /inventory-page on row creation via /inventory-add | Medium (2-8h) | Senior | ⚪ open |
| [TASK-036](open/task-036-recognition-overlay-state-machine.md) | Recognition-status overlay state machine + hint-family tokeniser | Large (8-24h) | Senior | ⚪ open |
| [TASK-037](open/task-037-secondary-key-dispatch.md) | Secondary key dispatch — R / X / U handlers | Medium (2-8h) | Senior | ⚪ open |
| [TASK-039](open/task-039-recognition-embed-module.md) | Implement src/partsledger/recognition/embed.py — DINOv2-ViT-S/14 via torch.hub | Medium (2-8h) | Senior | ⚪ open |
| [TASK-040](open/task-040-recognition-cache-module.md) | Implement src/partsledger/recognition/cache.py — sqlite-vec backed | Medium (2-8h) | Senior | ⚪ open |
| [TASK-041](open/task-041-cache-only-banded-recognition.md) | Cache-only recognition with tight / tight_ambiguous / medium / miss bands | Medium (2-8h) | Senior | ⚪ open |
| [TASK-042](open/task-042-vlm-adapter.md) | Implement src/partsledger/recognition/vlm.py — OpenAI-compatible REST adapter | Large (8-24h) | Senior | ⚪ open |
| [TASK-043](open/task-043-recognition-pipeline-glue.md) | Pipeline glue — pipeline.run(image) -&gt; Outcome with re-frame loop and writer hand-off | Large (8-24h) | Senior | ⚪ open |
| [TASK-044](open/task-044-undo-journal.md) | Undo journal at inventory/.embeddings/undo.toml, depth 1 | Medium (2-8h) | Senior | ⚪ open |
| [TASK-045](open/task-045-nexar-graphql-adapter.md) | Implement src/partsledger/enrichment/nexar.py — OAuth + GraphQL supSearchMpn | Medium (2-8h) | Senior | ⚪ open |
| [TASK-046](open/task-046-nexar-response-cache.md) | Implement src/partsledger/enrichment/cache.py — SQLite per-MPN response cache | Small (&lt;2h) | Medium | ⚪ open |
| [TASK-047](open/task-047-family-datasheet-fallback.md) | Implement src/partsledger/enrichment/family_datasheets.py — MPN-prefix → URL table | Small (&lt;2h) | Junior | ⚪ open |
| [TASK-048](open/task-048-enrichment-orchestrator.md) | Orchestrator enrich(part_id) + writer-integration (no clobber on non-empty cells) | Medium (2-8h) | Senior | ⚪ open |
| [TASK-049](open/task-049-camera-async-dispatch.md) | Camera-path async dispatch — dispatch_async() + single-worker thread + enrichment.log | Medium (2-8h) | Senior | ⚪ open |
| [TASK-050](open/task-050-skill-sync-chain.md) | Skill-path sync enrichment + page-gen chain (sync for /inventory-add, async for camera) | Medium (2-8h) | Senior | ⚪ open |
| [TASK-051](open/task-051-resistor-localisation-v1.md) | V1 — resistor localisation (HSV thresholding + contour finding) on still images | Medium (2-8h) | Senior | ⚪ open |
| [TASK-052](open/task-052-resistor-band-reading-eia.md) | V1 — band reading + EIA classifier + orientation disambiguation via E-series check | Medium (2-8h) | Senior | ⚪ open |
| [TASK-053](open/task-053-resistor-uniformity-check.md) | V1 — uniformity check (strict, every deviation flagged) | Small (&lt;2h) | Medium | ⚪ open |
| [TASK-054](open/task-054-resistor-extra-packaging.md) | V1 — package as partsledger[resistor-reader] extra with CLI entry-point | Small (&lt;2h) | Medium | ⚪ open |
| [TASK-055](open/task-055-resistor-trained-detector-v2.md) | V2 — small trained detector (YOLO-nano / MobileNet-SSD) for live-view localisation | Large (8-24h) | Senior | ⚪ open |
| [TASK-056](open/task-056-resistor-live-overlay-v2.md) | V2 — live overlay + per-frame stable decoding at ≥10 fps | Large (8-24h) | Senior | ⚪ open |

## Closed Tasks

| ID | Title | Effort |
|----|-------|--------|
| [TASK-001](closed/task-001-delete-sync-layer.md) | Delete awesome-task-system/ and scripts/sync_task_system.py | Small |
| [TASK-002](closed/task-002-python-skeleton.md) | Author Python project skeleton (pyproject, requirements-dev, CI, conftest, gitignore) | Small |
| [TASK-003](closed/task-003-replace-pre-commit.md) | Replace scripts/pre-commit with the CircuitSmith version | Small |
| [TASK-004](closed/task-004-upgrade-commit-skill.md) | Upgrade /commit skill and commit-pathspec.sh to the CircuitSmith versions | Small |
| [TASK-005](closed/task-005-settings-json.md) | Author .claude/settings.json with full allowlist + deny | Small |
| [TASK-006](closed/task-006-docs-verbatim-port.md) | Port the 13 verbatim developer docs from CircuitSmith | Medium |
| [TASK-007](closed/task-007-architecture-doc.md) | Write docs/developers/ARCHITECTURE.md for the PartsLedger pipeline | Medium |
| [TASK-008](closed/task-008-security-review-hooks.md) | Port security-review hooks (pre-merge-commit, post-merge, pre-rebase) | Medium |
| [TASK-009](closed/task-009-codeowner-mechanism.md) | Port codeowner reminder mechanism (hook + registry + PreToolUse) | Small |
| [TASK-010](closed/task-010-codeowner-starter-skills.md) | Author starter co-* skills capturing PartsLedger invariants | Small |
| [TASK-011](closed/task-011-claude-md-rewrite.md) | Rewrite CLAUDE.md to mirror CircuitSmith's verbatim | Small |
| [TASK-012](closed/task-012-epic-run-and-autonomy.md) | Port /epic-run skill and AUTONOMY.md, sweep HIL frontmatter on open tasks | Medium |
| [TASK-013](closed/task-013-apply-branch-protection.md) | Apply server-side branch protection to tgd1975/PartsLedger main | Small |
| [TASK-014](closed/task-014-source-column-and-section-flex.md) | Add Source column and maker-choice section taxonomy to INVENTORY.md | Medium (2-8h) |
| [TASK-015](closed/task-015-parts-page-template-adaptivity.md) | Teach /inventory-page to produce part-class-appropriate sections | Small (&lt;2h) |
| [TASK-016](closed/task-016-inventory-writer-module.md) | Implement src/partsledger/inventory/writer.py with upsert_row() contract | Large (8-24h) |
| [TASK-017](closed/task-017-inventory-lint-module.md) | Implement src/partsledger/inventory/lint.py + scripts/lint_inventory.py shim | Medium (2-8h) |
| [TASK-019](closed/task-019-hedge-language-lint.md) | Hedge-language lint over inventory/parts/*.md + pre-commit hook | Medium (2-8h) |
| [TASK-021](closed/task-021-family-page-proactive-suggestion.md) | Family-page proactive suggestion at add-time + page-gen-time | Medium (2-8h) |
| [TASK-022](closed/task-022-adopt-src-layout.md) | Adopt src/partsledger/ layout in pyproject | Medium (2-8h) |
| [TASK-023](closed/task-023-releasing-docs-and-release-skill.md) | Port RELEASING.md and /release skill; rewrite semver for three public surfaces | Medium (2-8h) |
| [TASK-024](closed/task-024-github-workflows.md) | Add .github/workflows/ci.yml and release.yml | Medium (2-8h) |
| [TASK-025](closed/task-025-uv-lock.md) | Adopt uv.lock for reproducible installs | Small (&lt;2h) |
| [TASK-026](closed/task-026-portability-lint.md) | Add src/partsledger/_dev/portability_lint.py with scripts/ shim | Medium (2-8h) |
| [TASK-027](closed/task-027-shim-convention-doc.md) | Document shim convention (scripts/ and skill .py files as thin shims) | Small (&lt;2h) |
| [TASK-028](closed/task-028-scripts-drift-audit.md) | Drift audit on already-copied scripts/ files vs CircuitSmith | Medium (2-8h) |
| [TASK-029](closed/task-029-optional-dependencies-extras.md) | Configure [project.optional-dependencies] for partsledger[resistor-reader] extra | Small (&lt;2h) |
| [TASK-030](closed/task-030-adr-0001-library-as-installable-package.md) | Write ADR-0001 — library as installable package | Small (&lt;2h) |
| [TASK-031](closed/task-031-bootstrap-readme-quickstart.md) | Write README.md / QUICKSTART.md bootstrap section | Medium (2-8h) |
| [TASK-032](closed/task-032-camera-selection-wizard.md) | Camera-selection wizard (V4L2 / DirectShow enumeration, friendly names) | Large (8-24h) |
| [TASK-033](closed/task-033-live-viewfinder-overlays.md) | Live viewfinder + capture overlays (framing rect, focus, lighting, trigger hint) | Large (8-24h) |
| [TASK-034](closed/task-034-capture-trigger-and-still.md) | Capture trigger + single-still emit per Output contract | Medium (2-8h) |
| [TASK-035](closed/task-035-camera-cli-wrapper.md) | CLI wrapper python -m partsledger.capture | Small (&lt;2h) |
| [TASK-038](closed/task-038-capture-slash-skill.md) | /capture thin slash-skill subprocess wrapper | Small (&lt;2h) |
<!-- END GENERATED -->
