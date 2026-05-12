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

### Policy

- TASK-003 closed: `scripts/pre-commit` replaced with CircuitSmith's
  version (substitutions `cs-` → `pl-`). Mandatory markdownlint and
  ruff gates; obsolete `sync_task_system.py --check` block removed.
- TASK-004 closed: `/commit` skill and `scripts/commit-pathspec.sh`
  upgraded. Wrapper accepts `--stage-untracked` for atomic in-process
  staging. Skill body runs `markdownlint-cli2 --fix` / `ruff check
  --fix` scoped to the pathspec before invoking git.
