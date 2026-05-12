# CI Pipeline

Inventory of PartsLedger's CI workflows, what each step gates, and
what to do when the build is red. The authoritative source is
[`.github/workflows/`](../../.github/workflows/) — if this doc and the
YAML disagree, the YAML wins; fix the doc.

## Workflows

### `ci.yml` — `CI`

Triggered on every `push` and `pull_request`. Single job (`test`)
fanned out across an OS matrix.

| Field | Value |
|---|---|
| File | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) |
| Trigger | `push`, `pull_request` |
| OS matrix | `ubuntu-latest`, `windows-latest` |
| Python | 3.11 (lower bound of `requires-python`) |
| Node | 20 |
| `fail-fast` | `false` — one OS failing does not abort the other |

Steps, in order:

| Step | What it does | Red means |
|---|---|---|
| Checkout | `actions/checkout@v4`. | Harness failure. |
| setup-python | Installs Python 3.11. | Harness failure. |
| setup-uv | `astral-sh/setup-uv@v3`. Installs the `uv` binary. | Harness failure. |
| setup-node | Installs Node 20. | Harness failure. |
| Install Python dev deps | `uv pip install --system -r requirements-dev.txt`. | A declared dep is missing from PyPI or the lock file diverged. |
| Install markdownlint-cli2 | `npm install -g markdownlint-cli2`. | npm registry issue. |
| Markdown lint | `markdownlint-cli2 "**/*.md" "#node_modules" "#.claude/security-review-latest.md"`. Mirror of the local pre-commit step. | A `.md` file violates the configured ruleset. Reproduce locally with the same command. |
| Ruff lint | `ruff check .`. Mirror of the local pre-commit step. | A `.py` file violates the configured `select = ["E4","E7","E9","F"]` ruleset. |
| Pytest | `pytest`. Picks up both test roots (`tests`, `scripts/tests`) per [`pyproject.toml`](../../pyproject.toml). | A test failed. Reproduce locally per [`TESTING.md`](TESTING.md). |

## Local mirror — the pre-commit hook

Every CI gate that runs on a *file you committed* also runs locally
via the pre-commit hook installed by
[`scripts/install_git_hooks.sh`](../../scripts/install_git_hooks.sh):

| CI step | Local equivalent |
|---|---|
| Markdown lint | `scripts/pre-commit` invokes `markdownlint-cli2` on staged `*.md`. |
| Ruff lint | `scripts/pre-commit` invokes `ruff check` on staged `*.py`. |
| Pytest | **Not** in the pre-commit hook — pytest is too slow for the per-commit budget. Run it manually before pushing. |
| Security review | `pre-merge-commit`, `post-merge`, `pre-rebase` hooks scan pulls/merges/rebases. Reports land at `.claude/security-review-latest.md`. |

The hook is the local insurance policy: if it's installed and green,
CI will be green for the same change. If the hook is bypassed
(`PL_COMMIT_BYPASS`) or skipped (`PL_SKIP_SECURITY_REVIEW`), CI is the
backstop.

## Gating policy

All CI steps in `ci.yml` are **blocking**. A red build prevents merge
once branch protection on `main` is enabled
([`BRANCH_PROTECTION_CONCEPT.md`](BRANCH_PROTECTION_CONCEPT.md)). There
is no "advisory" tier today — every job is on the required-status-checks
list.

The required-status-checks list for branch protection mirrors the job
names produced by `ci.yml`:

- `Test (ubuntu-latest)`
- `Test (windows-latest)`

Both must be green before a PR can merge to `main`.

## Red build — response

1. **Read the failing step.** Open the Actions tab; the failed step
   is named in the run summary.
2. **Reproduce locally** with the same command. CI commands are
   intentionally short so you can copy-paste them:
   - Markdown lint: `markdownlint-cli2 "**/*.md" "#node_modules" "#.claude/security-review-latest.md"`
   - Ruff lint: `ruff check .`
   - Pytest: `pytest`
3. **Fix and re-push.** No need to rerun the workflow by hand — a new
   push re-triggers it.
4. **Escalate** when the failure looks harness-side: pip/npm registry
   500s, a setup-python action regression, a Windows-runner glitch
   that does not reproduce locally on either OS. In those cases the
   first move is a fresh push (cheap re-run); the second is to open
   an issue in `.github/workflows/` rather than chase the code.

## Future workflows

Placeholders for workflows that do not yet exist; documented here so
they are not invented twice.

- **Release** — tag-driven build that produces a packaged inventory
  release once the pipeline modules land.
- **Docs site** — if an MkDocs build is adopted, a Pages-deploy
  workflow joins the matrix.

Both stay unimplemented until they are needed; this doc updates when
they land.
