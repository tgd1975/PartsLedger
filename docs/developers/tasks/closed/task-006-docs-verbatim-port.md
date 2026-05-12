---
id: TASK-006
title: Port the 13 verbatim developer docs from CircuitSmith
status: closed
closed: 2026-05-13
opened: 2026-05-12
effort: Medium
effort_actual: Medium (2-8h)
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 6
---

## Description

Port the documentation framework from CircuitSmith, verbatim except
for name-substitution. Thirteen files:

| File | Treatment |
|---|---|
| `CONTRIBUTING.md` | Verbatim; replace `npm install` + `pip install` steps with `uv venv && uv pip install -r requirements-dev.txt` (uv-native; see also `DEVELOPMENT_SETUP.md`). |
| `CHANGELOG.md` | Verbatim Keep-a-Changelog header; first `[Unreleased]` section enumerates this epic's deliverables under Bootstrap / Tooling / Policy subheadings. |
| `docs/developers/COMMIT_POLICY.md` | Verbatim. |
| `docs/developers/CODING_STANDARDS.md` | Verbatim. |
| `docs/developers/CI_PIPELINE.md` | Verbatim but rewritten install step uses uv (matches TASK-002's CI workflow). |
| `docs/developers/DEVELOPMENT_SETUP.md` | CS structure; expanded for PartsLedger's heavy deps (PyTorch, OpenCV, sqlite-vec, optional PaddleOCR/Tesseract). Install flow uses uv, not pip: `curl -LsSf https://astral.sh/uv/install.sh \| sh` → `uv venv` → `uv pip install -r requirements-dev.txt` → `uv run pytest`. |
| `docs/developers/TASK_SYSTEM.md` | Verbatim. (PartsLedger now matches CS's installed-copy model per TASK-001.) |
| `docs/developers/TESTING.md` | Verbatim. |
| `docs/developers/MERMAID_STYLE_GUIDE.md` | Verbatim; example diagram references adapted to PartsLedger's pipeline. |
| `docs/developers/CODE_OF_CONDUCT.md` | Verbatim. |
| `docs/developers/BRANCH_PROTECTION_CONCEPT.md` | Verbatim; URL paths in the `gh api` example point at `tgd1975/PartsLedger`. |
| `docs/developers/adr/0000-template.md` | Verbatim. |
| `docs/developers/adr/README.md` | Verbatim framework prose; the `## Index` section is empty (`(none yet)` under each status heading). |

**Name substitutions across all files** (mechanical):

- `CircuitSmith` → `PartsLedger`
- `circuitsmith` → `partsledger`
- `CS_` → `PL_`
- `cs-commit-token` → `pl-commit-token`
- `cs-commit-bypass.log` → `pl-commit-bypass.log`
- `tgd1975/CircuitSmith` → `tgd1975/PartsLedger`
- Internal links to CircuitSmith-only files (e.g. `tasks/closed/task-046-…`) → replaced with PartsLedger TASK references where they exist, or stripped where they don't.

**Not in this task:** `SECURITY_REVIEW.md`, `CODE_OWNERS.md`,
`AUTONOMY.md`, `ARCHITECTURE.md` — each ships with its mechanism
(TASKs 008, 009, 012, 007 respectively).

## Acceptance Criteria

- [x] Each of the 13 files exists at the right path and lint-passes
      `markdownlint-cli2`.
- [x] No occurrence of `CircuitSmith` / `circuitsmith` / `CS_` /
      `cs-` token in any of the ported files (run a final grep) —
      remaining mentions in CHANGELOG.md, CODING_STANDARDS.md,
      BRANCH_PROTECTION_CONCEPT.md, TASK_SYSTEM.md are intentional
      references to the sibling project / the epic slug
      `align-with-circuitsmith`, not stale substitution targets.
- [x] All in-doc cross-links resolve to a real file in the repo.
- [x] `CHANGELOG.md` `[Unreleased]` section has one bullet per
      preceding task in this epic (001–005) under appropriate
      Keep-a-Changelog subheadings.

## Test Plan

`markdownlint-cli2 "**/*.md"` exits 0. `grep -ri "CircuitSmith\|CS_\|cs-commit" <listed files>` returns no matches. Each cross-link resolves.

## Notes

CircuitSmith's `DEVELOPMENT_SETUP.md` is still on the pip wording at
scan time (mid-flight uv migration). PartsLedger leapfrogs that. If
CS later updates its `DEVELOPMENT_SETUP.md` to uv, the PartsLedger
copy will already match — no resync needed.
