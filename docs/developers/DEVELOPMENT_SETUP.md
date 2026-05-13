# Development Setup

The canonical first-time-setup walk-through for PartsLedger. Follow
top-to-bottom from a clean machine and you reach a green `pytest` run
without coming back with questions.

PartsLedger is developed on both **Ubuntu** and **Windows 11**. Where
the two diverge, this doc spells out both invocations — pick the one
matching your shell.

## Tool prerequisites

| Tool | Version | Required? | Notes |
|---|---|---|---|
| Git | ≥ 2.35 | Yes | Any modern git works; older versions miss `git rev-parse --show-toplevel` quirks the hooks rely on. |
| Python | ≥ 3.11 | Yes | 3.11, 3.12, and 3.13 are all CI-tested. |
| `uv` | latest | Yes | Astral's Python project + venv manager. Replaces `pip` + `venv` in the day-to-day flow. |
| Node.js | ≥ 20 | Yes | Solely to install `markdownlint-cli2`. |
| npm | bundled with Node | Yes | Used to install `markdownlint-cli2` globally. |
| `markdownlint-cli2` | latest | Yes | The pre-commit hook fails hard if this binary is missing. |
| `direnv` | ≥ 2.32 | Optional | Auto-loads the per-developer env vars in `.envrc`. |

### PartsLedger heavyweight runtime deps

The product code talks to a USB camera and runs vision + embedding
models locally. The first `uv pip install -e .[dev]` will pull in:

| Dep | Why | Notes |
|---|---|---|
| `torch` | DINOv2 embedding backbone. | CPU-only is fine for development; CUDA is optional. |
| `transformers` | Hosts the DINOv2 model. | Hugging Face cache is per-developer. |
| `Pillow`, `opencv-python` | Image capture + pre-processing. | OpenCV needs system libraries on minimal Linux installs (`libsm6`, `libxext6`). |
| `sqlite-vec` | Embedding-vector index next to the SQLite cache. | Ships as a Python wheel; no separate native install. |
| `requests`, `python-dotenv` | Nexar/Octopart calls; loading `.envrc` overrides. | — |
| `anthropic` | Claude Opus 4.7 Vision for part identification. | Requires `ANTHROPIC_API_KEY` (see Step 5). |

Optional OCR backends (PaddleOCR or Tesseract) are **not** declared in
`pyproject.toml` — install them per developer if you want to enable
the OCR-assist branch of the pipeline.

Set up these binaries first; everything below assumes they are on
`PATH`.

## Step 1 — Clone the repo

```bash
git clone https://github.com/tgd1975/PartsLedger.git
cd PartsLedger
```

## Step 2 — Install the git hooks

**Run this before your first commit, not after.** Skipping this step
is the most common new-contributor failure: the pre-commit hook is
not just a linter, it also enforces the
[commit-policy provenance token](../../CLAUDE.md#commits-go-through-commit--always)
that `/commit` writes. Raw `git commit` is rejected.

**Ubuntu / WSL / Git Bash:**

```bash
bash scripts/install_git_hooks.sh
```

**Windows 11 (PowerShell):**

```powershell
bash scripts/install_git_hooks.sh
```

The script is bash-only by design; on Windows run it from Git Bash or
WSL. It installs:

- `pre-commit` — markdown lint + ruff lint + commit-policy enforcement wrapper.
- `pre-merge-commit`, `post-merge`, `pre-rebase` — security-review hooks
  that scan incoming changes from pulls/merges/rebases. Reports land at
  `.claude/security-review-latest.md`.

Re-run is idempotent. Existing hooks are backed up to
`.git/hooks/<name>.backup.<timestamp>`.

## Step 3 — Install `markdownlint-cli2`

```bash
npm install -g markdownlint-cli2
```

This is the binary the pre-commit hook calls. Without it, every commit
fails with `markdownlint-cli2: command not found`.

## Step 4 — Install `uv` and the Python dev tooling

[`uv`](https://docs.astral.sh/uv/) is the project's Python lifecycle
manager. It replaces `pip` + `venv` in the day-to-day flow.

**Install uv (Ubuntu):**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Install uv (Windows 11 PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then, from the repo root:

```bash
uv venv
# Ubuntu: activate manually if your shell does not auto-activate
source .venv/bin/activate
# Windows 11 PowerShell:
# .\.venv\Scripts\Activate.ps1
uv pip install -r requirements-dev.txt
```

That installs PartsLedger in editable mode with the `[dev]` extra:
[`pytest`](https://docs.pytest.org/) and
[`ruff`](https://docs.astral.sh/ruff/), plus the runtime deps listed in
[Tool prerequisites § PartsLedger heavyweight runtime deps](#partsledger-heavyweight-runtime-deps).
The full declared list lives in [`pyproject.toml`](../../pyproject.toml).

**Smoke test the install:** `uv run python -c "import torch, anthropic"`
should print nothing and exit 0. If a dep is missing from
`pyproject.toml`, this is where it surfaces — open a PR adding it.

## Step 5 — Configure per-developer env vars

The repo ships [`.envrc.example`](../../.envrc.example) as a template
for paths and credentials that vary per developer (`ANTHROPIC_API_KEY`,
`PL_NEXAR_CLIENT_ID`, `PL_NEXAR_CLIENT_SECRET`, `PL_CAMERA_INDEX`,
`PL_INVENTORY_PATH`, `PL_PYTHON`).

If you use [`direnv`](https://direnv.net):

```bash
cp .envrc.example .envrc
# edit .envrc, fill in values
direnv allow
```

Otherwise, export the variables manually in your shell init file. The
project code references these as `$PL_*` and never hard-codes literal
paths — see [CLAUDE.md § Project env vars](../../CLAUDE.md#project-env-vars--use-pl_-never-hard-code-paths).

## Smoke test

From a clean clone, the following sequence should land you on a green
`pytest`:

```bash
git clone https://github.com/tgd1975/PartsLedger.git
cd PartsLedger
bash scripts/install_git_hooks.sh
npm install -g markdownlint-cli2
curl -LsSf https://astral.sh/uv/install.sh | sh    # Ubuntu
# irm https://astral.sh/uv/install.ps1 | iex       # Windows 11
uv venv && source .venv/bin/activate                # Ubuntu
# uv venv; .\.venv\Scripts\Activate.ps1            # Windows 11
uv pip install -r requirements-dev.txt
pytest
```

`pytest` exits with `0 passed` (or a small number, growing over time)
and no errors. If you reach this, the setup is complete and you can
pick up a task from [`docs/developers/tasks/OVERVIEW.md`](tasks/OVERVIEW.md).
Style conventions and the test-layout reference live in
[`CODING_STANDARDS.md`](CODING_STANDARDS.md) and
[`TESTING.md`](TESTING.md).

## CI merge gate — branch protection on `main`

Local setup mirrors the CI workflow at
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml). Once
server-side branch protection on `main` is enabled
([`BRANCH_PROTECTION_CONCEPT.md`](BRANCH_PROTECTION_CONCEPT.md)), the
required status checks are:

- `Test (ubuntu-latest)`
- `Test (windows-latest)`

Both must be green before a PR can merge. To add a new gate, append a
step to `ci.yml` and (after the first run lands a check with the new
name on a PR) add it to the required-status-checks list in the
branch-protection ruleset.

If your local `pytest` is green but CI is red, suspect:

- A platform-specific path the doc didn't flag (file a doc fix).
- A missing dev dep declared in CI but not in `requirements-dev.txt`
  (or vice-versa).
- An auto-fixable lint issue committed without running the pre-commit
  hook (was the hook installed?).

## Common setup problems

### `markdownlint-cli2: command not found` on commit

You skipped Step 3, or `npm install -g` landed the binary somewhere
not on `PATH`. Re-run Step 3; if it still does not resolve, run
`npm config get prefix` and confirm `<prefix>/bin` is on `PATH`.

### `uv pip install -r requirements-dev.txt` complains about Python version

PartsLedger requires Python ≥ 3.11. Check with `python3 --version`
(Ubuntu) or `py --version` (Windows). On Ubuntu, install a newer
interpreter via `pyenv` or the deadsnakes PPA; on Windows, fetch from
[python.org/downloads](https://www.python.org/downloads/) and re-run
Step 4 from a fresh shell.

### `import cv2` fails with a missing `.so` on Ubuntu

OpenCV's `cv2` wheel needs a handful of system libraries that minimal
Linux installs miss. The most common gaps:

```bash
sudo apt install -y libsm6 libxext6 libxrender1 libgl1
```

Re-run `python -c "import cv2"` to confirm.

### `torch` first-time install is huge

That's expected — the CPU wheel is ~200 MB. `uv pip install` caches it
across projects, so the second install in a fresh venv is fast.

### Commits are rejected with `commit-policy violation`

You ran raw `git commit` instead of the `/commit` skill. The pre-commit
hook validates a one-shot token at `.git/pl-commit-token` that
`scripts/commit-pathspec.sh` writes; raw `git commit` does not write
it. Use `/commit "<message>" <file> [<file> …]` — see
[CLAUDE.md § Commits go through /commit](../../CLAUDE.md#commits-go-through-commit--always).

### `git pull` rejected by the security-review hook

The `pre-merge-commit` hook scanned the incoming diff and flagged
something. Read `.claude/security-review-latest.md` for the report. If
the pull is known-good (e.g. your own branch coming back from a
re-base), bypass with:

```bash
PL_SKIP_SECURITY_REVIEW=1 git pull
```

The bypass is logged.

### `$PL_*` env vars unset

The code references `$PL_NEXAR_CLIENT_ID`, `$PL_NEXAR_CLIENT_SECRET`,
`$PL_CAMERA_INDEX`, `$PL_INVENTORY_PATH`, `$PL_PYTHON`, and
`$ANTHROPIC_API_KEY` directly. If a script complains about an unset
or empty `$PL_*` variable, you skipped Step 5. Re-copy
`.envrc.example`, fill in the value, and re-load your shell (or
`direnv allow`).

### Hooks "stop working" after re-cloning the repo

`.git/hooks/` is not in the working tree and does not survive a
re-clone. Re-run Step 2 in the new clone.
