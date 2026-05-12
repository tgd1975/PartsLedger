---
id: TASK-002
title: Author Python project skeleton (pyproject, requirements-dev, CI, conftest, gitignore)
status: open
opened: 2026-05-12
effort: Small
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 2
prerequisites: [TASK-001]
---

## Description

Author the Python project skeleton mirroring CircuitSmith's. Five
files / sweeps:

1. **`pyproject.toml`** — keep CircuitSmith's structure (project
   metadata block, `requires-python = ">=3.11"`, ruff
   `select = ["E4","E7","E9","F"]`,
   `[tool.pytest.ini_options]` with
   `testpaths = ["tests","scripts/tests"]`,
   `python_files = "test_*.py"`,
   `addopts = "-ra"`, `strict_markers = true`,
   `[tool.setuptools] py-modules = []`). Replace project name with
   `partsledger`. Replace `dependencies` with PartsLedger's actual
   stack — best-effort initial list from IDEA-001 and `CLAUDE.md`:
   `torch`, `transformers`, `Pillow`, `opencv-python`, `sqlite-vec`,
   `requests`, `anthropic`, `python-dotenv`. Ship and adjust on the
   first `uv pip install -e .[dev]` failure. **No `[tool.uv]` block,
   no `uv.lock`, no `.python-version`** — match CircuitSmith's
   pip-replacement mode of uv.
2. **`requirements-dev.txt`** — one-liner `-e .[dev]` (verbatim from
   CircuitSmith).
3. **`tests/conftest.py`** — empty file. CircuitSmith's conftest
   splices `.claude/skills/<lib>/` into `sys.path` per ADR-0007;
   PartsLedger has no such library-in-skill layout, so the splice
   would be a no-op. An empty conftest is still needed for pytest's
   test-root discovery on `testpaths = ["tests", "scripts/tests"]`.
4. **`.github/workflows/ci.yml`** — ubuntu + windows matrix,
   Python 3.11, **`astral-sh/setup-uv@v3`** action, then
   `uv pip install --system -r requirements-dev.txt`,
   `npm install -g markdownlint-cli2`, markdown lint glob, `ruff
   check .`, `pytest`. Drop CircuitSmith's portability-lint step
   (camel-vs-giraffe). PartsLedger leapfrogs CircuitSmith's
   own `ci.yml` which is still on pip at scan time.
5. **`.gitignore`** sweep — add the entries PartsLedger is missing
   versus CircuitSmith: `.idea/`,
   `.vscode/{launch.json,c_cpp_properties.json}`, `*.swo`, `*.egg`,
   `.claude/security-review-latest.md`.

**Bundled cleanup:** run `ruff check --fix scripts/` and commit the
fixes alongside the skeleton so TASK-003 (which adds a mandatory
`ruff check` step to the pre-commit hook) does not bounce. Any
residual ruff findings that auto-fix cannot resolve are listed in
this task's commit message.

## Acceptance Criteria

- [ ] `pyproject.toml` exists; `pip install -e .` and `uv pip install
      -e .[dev]` both succeed in a fresh venv (the latter is the
      canonical install).
- [ ] `requirements-dev.txt` is the verbatim CircuitSmith one-liner.
- [ ] `tests/conftest.py` exists and is empty.
- [ ] `.github/workflows/ci.yml` exists and uses `astral-sh/setup-uv`
      (not `pip install`).
- [ ] `.gitignore` carries the additions listed above.
- [ ] `ruff check scripts/` exits 0 on the post-cleanup tree.
- [ ] `pytest` from the repo root collects without errors (zero tests
      is acceptable; a collection error is not).

## Test Plan

In a fresh venv: `uv venv && source .venv/bin/activate && uv pip
install -e .[dev]`; verify `python -c "import torch, anthropic"` (or
whichever subset of declared deps is import-checkable without
hardware); `ruff check .` exits 0; `pytest` collects without error.

## Notes

CircuitSmith's `pyproject.toml` runtime deps are circuit-specific
(`schemdraw`, `matplotlib`, `jsonschema`, `ruamel.yaml`). Substitute
PartsLedger's stack — none of CircuitSmith's runtime deps transfer.
