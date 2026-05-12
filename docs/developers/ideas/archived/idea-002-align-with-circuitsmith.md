---
id: IDEA-002
title: Align PartsLedger with CircuitSmith framework
description: Transfer CircuitSmith's framework to PartsLedger (commit policy, docs, hooks, AUTONOMY, branch protection); uv-native.
category: foundation
---

## Archive Reason

2026-05-12 — Converted to EPIC-001 (align-with-circuitsmith) with TASK-001..TASK-013.

## Background

The sibling repo at `~/Dokumente/Projekte/CircuitSmith` was tuned over five
hours to a level of project-framework discipline PartsLedger doesn't yet
have: a checked-in `.claude/settings.json`, a `/commit`-skill +
provenance-token pre-commit hook with mandatory ruff and markdownlint, a
codeowner-reminder system, security-review hooks for pulls/merges/rebases,
a thirteen-doc developer-docs framework (`ARCHITECTURE`, `AUTONOMY`,
`COMMIT_POLICY`, `CODING_STANDARDS`, `CI_PIPELINE`, `DEVELOPMENT_SETUP`,
`TASK_SYSTEM`, `TESTING`, `MERMAID_STYLE_GUIDE`, `CODE_OF_CONDUCT`,
`CODE_OWNERS`, `SECURITY_REVIEW`, `BRANCH_PROTECTION_CONCEPT`), an ADR
practice, an `epic-run` skill for autonomous epic-level work, a GitHub
Actions CI matrix (ubuntu + windows), a `CHANGELOG.md`, a `CONTRIBUTING.md`,
and a server-side branch-protection ruleset.

This idea catalogues what to transfer, what to skip (genuinely
CircuitSmith-only "giraffe-riding skills"), and the phased execution plan.

**Directive:** CircuitSmith is the law. Transfer everything. The only
exception is content that is literally about CircuitSmith's domain
(schematics, ERC, NetGraph, skill-extraction) and has no PartsLedger
analogue. For those, keep the *mechanism* and skip the *contents*.

## Camel-vs-giraffe verdict

PartsLedger and CircuitSmith share the same shape: concept-stage solo Python
project, task-system workflow, direnv `.envrc`, markdown-native docs,
`/commit` + provenance-token, the same skill catalogue modulo the
project-specific tail. **Almost everything in CircuitSmith transfers.** The
exceptions are listed under "What to skip" below.

## uv (not pip)

CS's pip → uv migration is mid-flight at scan time: the `.venv/` exists,
the `.claude/settings.json` allowlist already lists the uv commands, but
`pyproject.toml`, `requirements-dev.txt`, `.envrc.example`, the docs, the
CI workflow, and `CLAUDE.md` are still in their pre-uv form. PL leapfrogs
the gap and ships uv consistently from day one. Concretely:

- **Install path:** `uv venv` then `uv pip install -r requirements-dev.txt`
  (or `uv pip install -e .[dev]`). No `pip install` anywhere in PL docs or
  CI.
- **CI workflow:** `astral-sh/setup-uv@v3` action, then
  `uv pip install --system -r requirements-dev.txt`.
- **`pyproject.toml` / `requirements-dev.txt`:** unchanged shape — uv reads
  both. No `[tool.uv]` block, no `uv.lock` checked in, no
  `.python-version` — matches CS's pip-replacement mode of uv.
- **`.claude/settings.json` allowlist:** carry CS's uv block verbatim (`uv
  venv`, `uv pip install`, `uv pip sync`, `uv run`, `uv sync`,
  `.venv/bin/{python,pytest,ruff}`).
- **`CLAUDE.md § Missing executables`:** PL's existing wording mentions
  `pip` as a fallback ("Try once with `pip`, `npx`, full path"). Swap `pip`
  → `uv pip` to reflect the new tooling.
- **`.envrc.example`:** CS has not yet added a venv-activation line; PL
  doesn't either, for now. If you want shell-side autoload, add
  `source .venv/bin/activate` post-Phase 1. Out of scope for this transfer.

## What to delete from PartsLedger before transfer

User directive: align PL with CS's "installed copy, no in-repo sync" model
for the task system. The PL-only sync layer goes.

- `awesome-task-system/` — entire directory.
- `scripts/sync_task_system.py`.
- The `## Task-system source-of-truth` section in `CLAUDE.md` — replaced
  by CS's `## Task-system installation` text under Phase 8.

(The sync-check block in `scripts/pre-commit` does not need a separate
deletion step — the whole file is replaced by the CS version under
Phase 2.)

After deletion, the live copies under `scripts/`, `.claude/skills/`, and
`docs/developers/task-system.yaml` are the truth. Upstream is consulted by
hand when drift becomes a problem, matching CS.

## What PartsLedger already has and must not regress

- `inventory/` directory plus the `inventory-add` / `inventory-page`
  skills.
- `PL_*` env naming, `pl-commit-token`, `PL_COMMIT_BYPASS`.

## What to skip (giraffe-riding)

| Item | Why skip |
|---|---|
| `.claude/skills/{co-erc-engine,co-netgraph,co-schema}/SKILL.md` content | Bound to circuit-specific files. Mechanism transfers; contents don't. PartsLedger gets its own `co-*` skills bound to `inventory/parts/*.md`, the embeddings cache, etc. |
| `docs/developers/adr/0001-…0010-…md` content | Each documents a CircuitSmith decision. Template + README + practice transfer; the ten records don't. PL files its own ADRs as decisions accrue. |
| `scripts/portability_lint.py` | Enforces that `.claude/skills/circuit/` stays path-agnostic so it can be extracted into a standalone repo (CircuitSmith Phase 7). PartsLedger has no equivalent extraction plan in IDEA-001. |
| `scripts/generate-schematic.py` | CircuitSmith product code. |
| `tests/test_schema_validation.py`, `tests/test_generator_byte_identity.py` | Circuit-schema and generator-byte-identity tests — product code. The CS `tests/conftest.py` also skips: it splices `.claude/skills/<lib>/` into `sys.path` per ADR-0007 and only applies when there's a library inside a skill directory (PL has none). PL ships an **empty** `tests/conftest.py` so pytest still finds the test root. |
| `scripts/tests/test_portability_lint.py` | Portability lint is camel-vs-giraffe (above); its test goes with it. |
| `docs/builders/wiring/*.svg` | Predecessor-repo artefacts. |
| `docs/developers/ideas/archived/idea-001.*` | CircuitSmith design dossier. PL already has its own IDEA-001 (PartsLedger concept). |
| All CircuitSmith TASK / EPIC files | PL's task system is its own. |

That's it. Everything else transfers.

## What to transfer

### Identical (do nothing; already in place)

- `.markdownlint.json`
- `.vibe/config.toml` structure
- `docs/developers/task-system.yaml` (byte-identical to CS)
- The provenance-token half of `scripts/pre-commit` (full file replaced
  by CS version under Phase 2 anyway — listed here for completeness)
- `.envrc.example` structure
- The task-system skills (`ts-*`, `tasks`, `housekeep`, `status`,
  `check-branch`, `check-tool`, `fix-markdown`, `os-context`,
  `update-scripts-readme`). NB: `commit` is **not** here — it's
  replaced under Phase 3, see "Transfer verbatim" below.
- `.vscode/settings.json` — both projects only have visual colour
  customisation; the PL palette is different from CS's by design. Keep
  PL's.
- `inventory/*` — PL's data, out of scope.

### Transfer verbatim (with `CS_*` → `PL_*` and `cs-*` → `pl-*` substitution)

- `scripts/security_review_changes.py`
- `scripts/git-hooks/{pre-merge-commit,post-merge,pre-rebase}`
- `scripts/install_git_hooks.sh`
- `scripts/codeowner_hook.py`
- `requirements-dev.txt`
- `docs/developers/adr/0000-template.md`
- `docs/developers/COMMIT_POLICY.md`
- `docs/developers/CODING_STANDARDS.md`
- `docs/developers/CI_PIPELINE.md`
- `docs/developers/TASK_SYSTEM.md`
- `docs/developers/TESTING.md`
- `docs/developers/SECURITY_REVIEW.md`
- `docs/developers/CODE_OWNERS.md`
- `docs/developers/MERMAID_STYLE_GUIDE.md`
- `docs/developers/CODE_OF_CONDUCT.md`
- `docs/developers/BRANCH_PROTECTION_CONCEPT.md`
- `docs/developers/AUTONOMY.md`
- `.claude/skills/epic-run/SKILL.md`
- `.claude/skills/commit/SKILL.md` (CS version is newer: fixer registry +
  `--stage-untracked` flow + `Bash(git add:*)` deny — replaces PL's older
  in-skill `git add` step)

### Transfer with structural adaptation (PL-specific content, CS form)

- `pyproject.toml` — keep CS structure (ruff `select = ["E4","E7","E9","F"]`,
  pytest `testpaths = ["tests","scripts/tests"]`, project metadata block).
  Swap `dependencies` to PL's actual stack inferred from
  [IDEA-001](idea-001-partsledger-concept.md) and
  [CLAUDE.md](../../../../CLAUDE.md): tentative
  `torch`, `transformers`, `Pillow`, `opencv-python`, `sqlite-vec`,
  `requests`, `anthropic`, `python-dotenv`. Ship best-effort; fix when wrong.
  No `[tool.uv]` block — CS is on uv in pip-replacement mode (no project-mode
  declarative deps, no `uv.lock`, no `.python-version` checked in). PL
  matches.
- `.github/workflows/ci.yml` — ubuntu + windows matrix, mandatory markdown
  lint, ruff check, pytest. Drop the portability-lint step. **Use uv to
  install Python deps** (`astral-sh/setup-uv@v3` action, then
  `uv pip install --system -r requirements-dev.txt` or
  `uv pip install --system -e .[dev]`). CS's `ci.yml` itself was not yet
  updated for uv at scan time — this is a known mid-flight gap on the CS
  side; PL leapfrogs it.
- `.claude/settings.json` — full allowlist + deny, plus `PreToolUse` hook
  for `codeowner_hook.py`. Adapt allowlist to PL's actual script names
  (`housekeep`, `release_burnup`, `release_snapshot`, `task_system_config`,
  `update_idea_overview`, `update_task_overview`, `update_scripts_readme`,
  `security_review_changes`, `codeowner_hook`). `portability_lint` and
  `sync_task_system` are dropped — neither exists in the post-deletion repo.
  **Include the uv allowlist block** picked up from CS's uncommitted diff:
  `Bash(uv venv:*)`, `Bash(uv pip install:*)`, `Bash(uv pip sync:*)`,
  `Bash(uv run:*)`, `Bash(uv sync:*)`, `Bash(.venv/bin/python:*)`,
  `Bash(.venv/bin/pytest:*)`, `Bash(.venv/bin/ruff:*)`. Drop CS's
  `python scripts/generate-schematic.py` entry (camel-vs-giraffe).
- `.gitignore` — sweep in missing entries (`.idea/`,
  `.vscode/{launch.json,c_cpp_properties.json}`, `*.swo`, `*.egg`,
  `.claude/security-review-latest.md`).
- `scripts/pre-commit` — **full replacement by CS version.** Substitute
  `CS_COMMIT_BYPASS` → `PL_COMMIT_BYPASS`, `cs-commit-token` →
  `pl-commit-token`, `cs-commit-bypass.log` → `pl-commit-bypass.log`. Drop
  the portability-lint block (camel-vs-giraffe). The CS file already
  contains the mandatory markdown + ruff blocks; no surgical merging
  needed.
- `.claude/codeowners.yaml` — PL-bound patterns:
  `inventory/parts/*.md` → `co-inventory-schema`,
  the embeddings-cache invariant, the housekeep/sync invariants.
- 1–2 starter `co-*` skills under `.claude/skills/` — bodies authored
  from PL invariants (schema, cache, sync).
- `CHANGELOG.md` — CS Keep-a-Changelog header, first entry describes this
  framework import.
- `CONTRIBUTING.md` — CS structure, PL-specific setup steps. Short-form
  setup line: `uv venv && uv pip install -r requirements-dev.txt`.
- `docs/developers/DEVELOPMENT_SETUP.md` — CS structure, expanded for PL's
  heavy deps (PyTorch, OpenCV, sqlite-vec installation per OS). **Install
  flow uses uv, not pip:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
  → `uv venv` → `uv pip install -r requirements-dev.txt` → `uv run pytest`.
  CS's own DEVELOPMENT_SETUP.md is still on the pip wording at scan time
  (mid-flight uv migration); PL leapfrogs that and ships the uv form
  directly.
- `docs/developers/CI_PIPELINE.md` — mirror the uv-based CI workflow from
  Phase 1, not CS's pip wording.
- `docs/developers/ARCHITECTURE.md` — CS structure (Pipeline + Module
  boundaries + Decoupling seams + AI containment + Where-to-go-next).
  Content: PL's camera → DINOv2 → Claude Vision → Nexar pipeline; the
  decoupling seam is "inventory MD files are source of truth; SQLite is
  cache, regenerable"; the AI-containment seam is "Vision API is
  authoring-time only; runtime reads MD".
- `CLAUDE.md` — **full rewrite mirroring CS verbatim.** User directive:
  every rule in CS's CLAUDE.md was learned the hard way; no cherry-picking.
  Substitutions only: `CS_*` → `PL_*`, `CircuitSmith` → `PartsLedger`,
  `cs-commit-token` → `pl-commit-token`, links to `idea-001-circuit-skill`
  → links to `idea-001-partsledger-concept`, etc. Two PL-shaped retentions
  (same structural slot as CS project-specific content, different content):
  - Keep PL's `## Inventory is the source of truth` section (PL's domain
    rule; CS has none of these because it has no inventory).
  - Keep PL's more-detailed `## Missing executables` body (`torch`, `cv2`,
    `sqlite_vec`, PaddleOCR/Tesseract, `/check-tool`) — same slot as CS's
    shorter version, but PL's expanded list is accurate for PL's actual
    heavyweight deps. **Swap `pip` → `uv pip`** in the fallback wording
    per the uv section above.

  Drop PL's `## Task-system source-of-truth` section entirely; replace
  with CS's `## Task-system installation` text.
- `.vibe/config.toml` — add `epic-run` and the new `co-*` skills to
  `enabled_skills`.

## Execution plan

Wrap as **one EPIC** on a single branch
(`release/epic-NNN-align-with-circuitsmith`), one task per phase, one
commit per task closure, one squash-merge to `main` at the end. **11
phases, 8 Small + 3 Medium.**

### Phase table

| # | Phase | Files / output | Predecessor | Size |
|---|---|---|---|---|
| 0 | Delete sync layer | remove `awesome-task-system/`, remove `scripts/sync_task_system.py` | — | S |
| 1 | Python project skeleton | `pyproject.toml`, `requirements-dev.txt`, empty `tests/conftest.py`, `.github/workflows/ci.yml`, `.gitignore` sweep | 0 | S |
| 2 | Pre-commit replacement | `scripts/pre-commit` (full CS-version replace, name subs, drop portability block) | 0 | S |
| 3 | `/commit` skill upgrade | `.claude/skills/commit/SKILL.md` + `scripts/commit-pathspec.sh` (both replaced by CS versions; CS's wrapper has `--stage-untracked`) | 2 | S |
| 4 | `.claude/settings.json` | Full allowlist + deny (incl. uv block, `Bash(git add:*)` deny). PreToolUse hook block deferred to Phase 7. | 3 | S |
| 5 | Documentation framework | 14 files — see [Phase 5 details](#phase-5-details--documentation-framework) | — | M |
| 6 | Security-review hooks | `scripts/security_review_changes.py`, `scripts/git-hooks/{pre-merge-commit,post-merge,pre-rebase}`, `scripts/install_git_hooks.sh`, `docs/developers/SECURITY_REVIEW.md`; allowlist + `.gitignore` updates | 4 | M |
| 7 | Codeowner reminder system | `scripts/codeowner_hook.py`, `scripts/tests/test_codeowner_hook.py`, `.claude/codeowners.yaml`, 1–2 `co-*` SKILL.md files, `docs/developers/CODE_OWNERS.md`; PreToolUse hook block added to `.claude/settings.json` | 4 | S |
| 8 | CLAUDE.md full rewrite | `CLAUDE.md` — mirror CS verbatim with name substitution; retain PL's `## Inventory is the source of truth` and PL's expanded `## Missing executables` (with `pip` → `uv pip`); drop PL's `## Task-system source-of-truth`, add CS's `## Task-system installation` | 0, 1, 2, 3, 4 | S |
| 9 | `epic-run` + AUTONOMY | `.claude/skills/epic-run/SKILL.md`, `docs/developers/AUTONOMY.md`, `.vibe/config.toml` (`epic-run` + `co-*` in `enabled_skills`), sweep open tasks to add `human-in-loop:` frontmatter | 5 | M |
| 10 | Apply server-side branch protection | `gh api -X PUT /repos/tgd1975/PartsLedger/branches/main/protection` — see [Phase 10 details](#phase-10-details--server-side-branch-protection). HIL: Main. | 1, 5 | S |

**Sequencing.** `0 → 1 → 2 → 3 → 4` is the critical path. After Phase 4
lands, Phases 5/6/7/8 are independent and may run in any order. Phase 9
depends on Phase 5 (AUTONOMY.md links into the docs framework). Phase 10
lands last — it needs Phase 1's CI workflow to be producing the named
status checks before the protection rule can reference them.

### Phase 5 details — documentation framework

14 files in one Medium task. All except `ARCHITECTURE.md` are CS-verbatim with
name substitution (`CS_*` → `PL_*`, `CircuitSmith` → `PartsLedger`,
`cs-commit-token` → `pl-commit-token`, link rewrites).

| File | Treatment |
|---|---|
| `CONTRIBUTING.md` | Verbatim; uv install one-liner |
| `CHANGELOG.md` | Verbatim header; first `[Unreleased]` entry = "import CS framework + uv migration" |
| `docs/developers/COMMIT_POLICY.md` | Verbatim |
| `docs/developers/CODING_STANDARDS.md` | Verbatim |
| `docs/developers/CI_PIPELINE.md` | Verbatim, uv wording (not pip) |
| `docs/developers/DEVELOPMENT_SETUP.md` | Verbatim shape; PL-specific install (uv venv, PyTorch/OpenCV/sqlite-vec install per OS) |
| `docs/developers/TASK_SYSTEM.md` | Verbatim |
| `docs/developers/TESTING.md` | Verbatim |
| `docs/developers/MERMAID_STYLE_GUIDE.md` | Verbatim; example adapted to PL pipeline |
| `docs/developers/CODE_OF_CONDUCT.md` | Verbatim |
| `docs/developers/BRANCH_PROTECTION_CONCEPT.md` | Verbatim |
| `docs/developers/adr/0000-template.md` | Verbatim |
| `docs/developers/adr/README.md` | Verbatim framework prose; empty `## Index` (no ADRs yet) |
| `docs/developers/ARCHITECTURE.md` | **Fresh write.** CS structure (Pipeline / Module boundaries / Decoupling seams / AI containment / Where-to-go-next); content is PL's camera → DINOv2 → Claude Vision → Nexar pipeline; seam = "MD is truth, SQLite is cache"; AI containment = "Vision is authoring-time only, runtime reads MD" |

`SECURITY_REVIEW.md`, `CODE_OWNERS.md`, and `AUTONOMY.md` are intentionally
**not** in this phase — each ships with its mechanism (Phases 6, 7, 9).

### Phase 10 details — server-side branch protection

Ruleset from `BRANCH_PROTECTION_CONCEPT.md`:

- Require status checks: `Test (ubuntu-latest)`, `Test (windows-latest)`; strict (branches up to date).
- Require linear history: **yes**.
- Allow force pushes: **no**.
- Allow deletions: **no**.
- Require PR review: **no** (solo project; flip on contributor #2 lands).
- Enforce for administrators: **no** (owner keeps hot-fix path).

Apply via the GitHub REST API:

```bash
gh api -X PUT /repos/tgd1975/PartsLedger/branches/main/protection --input <json-body>
```

`human-in-loop: Main` because `gh api -X PUT` is a remote-effect action
requiring explicit per-invocation user approval per AUTONOMY.md
§ No-published-effect.

## GitHub-side coverage at a glance

| Concern | Client-side | Server-side | In plan |
|---|---|---|---|
| No commits on `main` | `/check-branch` skill (already in PL); `permissions.deny "git push origin main"` (Phase 4) | branch protection blocks direct push (Phase 10) | ✓ both layers |
| Squash-merge only | `/commit` skill + `CLAUDE.md § Branch merges` (Phases 3, 8) | "Require linear history" (Phase 10) | ✓ both layers |
| CI must be green | local pre-commit gates (Phase 2) | "Require status checks" (Phase 10) | ✓ both layers |
| No force-push, no deletion | `permissions.deny "git push --force"` (Phase 4) | "Allow force pushes: No" + "Allow deletions: No" (Phase 10) | ✓ both layers |
| Agent cannot publish without approval | `gh pr create` / `gh pr merge` left **off** the allowlist → prompt-by-default (Phase 4); AUTONOMY.md `§ No-published-effect` (Phase 9) | — (this is purely client-side; the server has no "agent vs human" concept) | ✓ |
| Repo settings beyond branch protection | — | not in scope yet (no PR templates, no issue templates, no `.github/CODEOWNERS`; matches CS) | — (CS doesn't have these either) |

The two layers compose per CS's `BRANCH_PROTECTION_CONCEPT.md § Client-side ≠ server-side`. Skipping the server layer (Phase 10) would leave a checkout-without-the-hooks loophole — anyone with push rights could
bypass the local rules with a raw `git push`.

## Open question

Exactly **one** item is genuinely PL-shaped and not inferable from CS:

- **`pyproject.toml` runtime deps** — best-effort list above
  (`torch`, `transformers`, `Pillow`, `opencv-python`, `sqlite-vec`,
  `requests`, `anthropic`, `python-dotenv`). I'll ship this and fix on
  the first `uv pip install -e .[dev]` failure. No need to block on it.

Everything else: follow CircuitSmith.
