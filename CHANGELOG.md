# Changelog

All notable changes to PartsLedger are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) at
a relaxed cadence — bullet lists per release, no per-PR enumeration. The
project version follows [Semantic Versioning](https://semver.org/) once the
first tag is cut; until then the `[Unreleased]` section is the only entry.

## [Unreleased]

### Bootstrap

- Repository concept-staged from IDEA-001 (the markdown-native inventory
  for an electronics parts bin, paired with the planned CircuitSmith).
- EPIC-001 (align-with-circuitsmith) opened to transfer CircuitSmith's
  project framework — commit policy with provenance token, mandatory
  ruff + markdownlint pre-commit gates, developer-docs framework,
  security-review hooks, codeowner reminder system, autonomous-epic-run
  skill, GitHub Actions CI matrix, server-side branch protection.

### Tooling

- TASK-001 closed: deleted `awesome-task-system/` and
  `scripts/sync_task_system.py`. PartsLedger now follows CircuitSmith's
  installed-copy model — the live `scripts/`, `.claude/skills/`, and
  `docs/developers/task-system.yaml` are the source of truth.
- TASK-002 closed: Python project skeleton landed — `pyproject.toml`
  (`requires-python = ">=3.11"`, runtime deps `torch`, `transformers`,
  `Pillow`, `opencv-python`, `sqlite-vec`, `requests`, `anthropic`,
  `python-dotenv`), `requirements-dev.txt` one-liner, empty
  `tests/conftest.py`, uv-based CI workflow (ubuntu + windows matrix,
  `astral-sh/setup-uv@v3`, ruff, pytest). Bundled ruff cleanup landed
  the same commit so the new ruff hook from TASK-003 doesn't bounce.
- TASK-005 closed: `.claude/settings.json` authored with allowlist +
  deny mirroring CircuitSmith's shape. Deny includes `Bash(git add:*)`
  (harness-enforced no-`git add`), `Bash(sed/awk/head/tail:*)`,
  `Bash(git push origin main|--force|-f:*)`.
- `.envrc.example` extended with the VLM env-vars
  (`PL_VLM_ENDPOINT`, `PL_VLM_MODEL`) and the IDEA-006 camera-wizard
  placeholders.
- `docs/developers/config.toml.example` added as the canonical
  `~/.config/partsledger/config.toml` shape for the camera + recognition
  layers (consumed by TASK-032 wizard and TASK-039..042 recognition stack).
- `scripts/security_review_changes.py` sensitised to hardcoded API keys
  and private-key blocks; `docs/developers/SECURITY_REVIEW.md` updated
  to match.

### Policy

- TASK-003 closed: `scripts/pre-commit` replaced with CircuitSmith's
  version (substitutions `cs-` → `pl-`). Mandatory markdownlint and
  ruff gates; obsolete `sync_task_system.py --check` block removed.
- TASK-004 closed: `/commit` skill and `scripts/commit-pathspec.sh`
  upgraded. Wrapper accepts `--stage-untracked` for atomic in-process
  staging. Skill body runs `markdownlint-cli2 --fix` / `ruff check
  --fix` scoped to the pathspec before invoking git.
- TASK-011 closed: `CLAUDE.md` rewritten to mirror CircuitSmith's
  operational framework — added sections on no-diagnostic-suffix
  Bash, no-end-of-turn-checkpoints, squash-merge-to-main, CHANGELOG-
  rides-with-merge, autonomy. PartsLedger-shaped retentions kept for
  the inventory-is-source-of-truth invariant and the heavyweight-deps
  Missing-executables body (with `pip` → `uv pip`).
- TASK-013 closed: server-side branch protection applied on
  `tgd1975/PartsLedger/main` via `gh api -X PUT`. Required status
  checks (`Test (ubuntu-latest)`, `Test (windows-latest)`), linear
  history required, force-push and deletion forbidden, admin
  enforcement off (owner keeps hot-fix path), PR review off (solo
  project — trigger to flip is contributor #2 landing).

### Documentation

- TASK-006 closed: 13 verbatim developer docs ported from
  CircuitSmith with `cs-` → `pl-` substitutions — `CONTRIBUTING.md`,
  `CHANGELOG.md` shape, `docs/developers/{COMMIT_POLICY, CODING_STANDARDS,
  CI_PIPELINE, DEVELOPMENT_SETUP, TASK_SYSTEM, TESTING,
  MERMAID_STYLE_GUIDE, CODE_OF_CONDUCT, BRANCH_PROTECTION_CONCEPT}.md`,
  plus the `adr/` scaffold (`0000-template.md`, `README.md`).
  DEVELOPMENT_SETUP expanded for PartsLedger's heavy deps
  (torch / opencv / sqlite-vec, optional OCR); CI_PIPELINE uses uv +
  ruff and drops the CS-specific portability-lint step;
  MERMAID_STYLE_GUIDE example diagrams adapted to PartsLedger's
  pipeline.
- TASK-007 closed: `docs/developers/ARCHITECTURE.md` fresh-authored
  for PartsLedger's pipeline (camera → DINOv2 → KNN → Claude Vision →
  Nexar → MD entry). Mermaid pipeline (`flowchart LR`) and module-
  boundary graph (`graph TD`) with the forbidden
  `embed_cache → inventory_md` edge in red-dashed style per
  MERMAID_STYLE_GUIDE.md. Decoupling-seams section names the two
  load-bearing invariants (MD is source of truth; CircuitSmith reads
  PartsLedger one-way via `--prefer-inventory`).

### Governance

- TASK-008 closed: security-review hook layer ported —
  `scripts/security_review_changes.py`, the three git-hooks
  (`pre-merge-commit`, `post-merge`, `pre-rebase`),
  `scripts/install_git_hooks.sh`, and
  `docs/developers/SECURITY_REVIEW.md`. Bypass with
  `PL_SKIP_SECURITY_REVIEW=1` / `PL_SKIP_CLAUDE_REVIEW=1`.
  Allowlist gained `Bash(python scripts/security_review_changes.py:*)`.
- TASK-009 closed: codeowner reminder mechanism —
  `scripts/codeowner_hook.py` (PreToolUse hook), `.claude/codeowners.yaml`
  registry with `inventory/parts/*.md` → `co-inventory-schema` and
  `inventory/INVENTORY.md` → `co-inventory-master-index` bindings.
  Settings.json gains the `hooks.PreToolUse` block. Full 26-test suite
  ported (parser, glob, hook flow) and green.
  `docs/developers/CODE_OWNERS.md` documents the mechanism.
- TASK-010 closed: starter `co-*` skills authored —
  `co-inventory-schema` (frontmatter schema per IDEA-027 vocabulary,
  pin-aliasing per ADR-0010, MD-is-truth invariant, master-index
  linkage rule) and `co-inventory-master-index` (per-row schema,
  category sections, qty-rides-here-not-in-MD invariant). Both
  registered in `.vibe/config.toml` `enabled_skills`.

### Autonomy

- TASK-012 closed: autonomous-implementation mode wired up.
  - `docs/developers/AUTONOMY.md` codifies the four HIL values
    (`No` / `Clarification` / `Support` / `Main`), the
    ADR-on-ambiguity rule, the epic-driver loop (work-phase +
    commit-phase + hand-off phase + CHANGELOG-delta phase), the
    definition-of-done checklist, the review-packet format, and
    the no-published-effect-without-approval policy.
  - `.claude/skills/epic-run/SKILL.md` is the protocol-scaffold
    driver skill the agent follows (composer over `/ts-task-active`,
    `/commit`, `/housekeep`, `/ts-task-done`, `/check-branch`).
  - HIL frontmatter sweep was a no-op — every existing task already
    carried the field.

### CI

- `chore(ci)`: fixed pre-existing housekeep test failures so the
  CI gate goes green and TASK-013's branch-protection rule could
  reference the named status checks. Five drift-fixes in
  `scripts/tests/test_housekeep.py`,
  `scripts/tests/test_housekeep_concurrency.py`, and
  `scripts/housekeep.py`'s `Move.describe()` (path normalization for
  cross-platform stable output). Not in EPIC-001's scope but
  blocked TASK-013.

### EPIC-001 closed

- **EPIC-001 (align-with-circuitsmith) closed** — all 13 tasks
  done. PartsLedger now mirrors CircuitSmith's project framework:
  commit policy with one-shot provenance token, mandatory ruff +
  markdownlint gates, full developer-docs set + fresh
  ARCHITECTURE.md, security-review hooks, codeowner reminder
  mechanism, autonomous-epic-run skill, GitHub Actions CI matrix,
  server-side branch protection on `main`. See the closed epic at
  [docs/developers/tasks/closed/epic-001-align-with-circuitsmith.md](docs/developers/tasks/closed/epic-001-align-with-circuitsmith.md).

### Ideas

- IDEA-001 split (2026-05-13) into six per-toolchain-piece dossiers so
  each part of the pipeline can be honed independently before any of it
  reaches epic / implementation: **IDEA-004** (Markdown inventory
  schema), **IDEA-005** (skill path — `/inventory-add` + `/inventory-page`,
  as-built), **IDEA-006** (USB camera capture), **IDEA-007** (visual
  recognition — DINOv2 cache + VLM), **IDEA-008** (metadata
  enrichment — Nexar/Octopart + optional OCR), **IDEA-009** (CircuitSmith
  `--prefer-inventory` adapter). The seed dossier moved to
  `archived/idea-001-partsledger-concept.md` with a "superseded by"
  header. Cross-references updated in README, CLAUDE.md, CONTRIBUTING,
  ARCHITECTURE, AUTONOMY, CODE_OWNERS, TASK_SYSTEM, adr/README, the
  two `co-inventory-*` SKILL.md files, and IDEA-003.
- IDEAs 004, 005, 006, 007, 008, 011, 012, 014 honed across the 2026-05
  work and archived after promotion to their corresponding epics.
  IDEA-012 captured the cross-cuts (workflows A + B, unified pipeline,
  six-phase rollout, Section 4 gap analysis pruned from 9 to 2,
  Section 5 implementation plan synthesised) before being promoted.
- IDEA-010 (local VLM hosting) added as a spin-off from IDEA-007; scope
  widened to cover both DINOv2 backbone hosting and VLM hosting.
  Remains open.
- IDEA-011 (resistor color-band detector) added as a standalone-tool
  sibling; archived after promotion to EPIC-008.
- IDEA-013 (capture setup + colour calibration) added; remains open as
  the colour-profile input to TASK-054 (resistor reader V1).
- IDEA-014 (project setup review vs CircuitSmith) added and archived
  after promotion to EPIC-004 (cross-cutting Phase 0b prerequisite).
- IDEA-009 (CircuitSmith prefer-inventory adapter) archived — owned
  downstream by CircuitSmith IDEA-010.

### Roadmap

- **8 epics opened** (EPIC-002..EPIC-009) and **45 tasks scaffolded**
  (TASK-014..TASK-058) realizing the IDEA-012 implementation plan.
  Mapping (epic ← seed idea):
  - EPIC-002 markdown-inventory-schema  ← IDEA-004 (TASK-014..018)
  - EPIC-003 skill-path-today           ← IDEA-005 (TASK-019..021)
  - EPIC-004 project-setup              ← IDEA-014 (TASK-022..031, Phase 0b)
  - EPIC-005 usb-camera-capture         ← IDEA-006 (TASK-032..038)
  - EPIC-006 visual-recognition         ← IDEA-007 (TASK-039..044)
  - EPIC-007 metadata-enrichment        ← IDEA-008 (TASK-045..050)
  - EPIC-008 resistor-reader            ← IDEA-011 + IDEA-013 (TASK-051..056)
  - EPIC-009 integration-followups      ← IDEA-012 § 4 (TASK-057..058)
- Three tasks land paused awaiting upstream prerequisites: TASK-018
  (multi-file split, real-bin trigger), TASK-057 (pipeline fixture
  corpus, awaits TASK-043 active), TASK-058 (resistor-reader parser
  test, awaits TASK-054 close).
- EPIC-004 Phase 0b is the hard prerequisite for every Phase 1+ task —
  no module is importable as `partsledger.*` until `src/partsledger/`
  layout, release pipeline, lockfile, shim convention, and the inventory
  writer + lint modules (TASK-016/017) land.
