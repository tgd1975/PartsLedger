# PartsLedger — Quickstart

Fresh-clone-to-first-part walk-through. The vision lives in
[`README.md`](README.md); this file is the operations manual. Follow
the steps in order; each command is meant to be copy-pasted.

## 1. Install

```bash
git clone https://github.com/tgd1975/PartsLedger.git
cd PartsLedger
bash scripts/install_git_hooks.sh        # commit-provenance + security-review hooks
npm install -g markdownlint-cli2          # docs gate

# Install uv (Ubuntu):
curl -LsSf https://astral.sh/uv/install.sh | sh
# Install uv (Windows 11 PowerShell):
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

uv venv
source .venv/bin/activate                # Ubuntu
# .\.venv\Scripts\Activate.ps1           # Windows 11

uv sync                                   # uses uv.lock for reproducible env
```

`uv sync` reads `uv.lock` and installs PartsLedger in editable mode
with the `[dev]` extra. If the lockfile is missing or stale, fall
back to `uv pip install -r requirements-dev.txt`; the long-form
DEVELOPMENT_SETUP doc covers the dep-bump workflow.

Heavy deps (PyTorch, OpenCV, sqlite-vec) pull ~200 MB on first
install; subsequent installs reuse uv's cache. Tool-prerequisite
detail and platform-specific troubleshooting live in
[`docs/developers/DEVELOPMENT_SETUP.md`](docs/developers/DEVELOPMENT_SETUP.md).

## 2. Configure per-developer env vars

Copy the env template and fill in your values:

```bash
cp .envrc.example .envrc
# edit .envrc — fill in:
#   ANTHROPIC_API_KEY        — Claude Vision identifier
#   PL_NEXAR_CLIENT_ID       — Nexar/Octopart credentials (metadata enrichment)
#   PL_NEXAR_CLIENT_SECRET
#   PL_CAMERA_INDEX          — V4L2 / DirectShow index (camera-path; default 0)
#   PL_INVENTORY_PATH        — override path to inventory/INVENTORY.md (optional)
direnv allow                                    # if you use direnv
# otherwise: source .envrc, or export the vars in your shell init
```

The full variable list is in [`.envrc.example`](.envrc.example) —
don't retype it here, it's the source of truth.

## 3. First capture *(Phase 1+ — placeholder)*

The camera-capture entry point (`partsledger capture` or
`python -m partsledger.capture`) lands in **EPIC-005** (TASK-032
through TASK-038). Until that epic closes the skill-path and
camera-path workflows are independent: use `/inventory-add` from
Claude Code to seed entries by hand; come back here once the
camera path lands.

When EPIC-005 closes this section will document the V4L2 /
DirectShow camera-selection wizard, the live viewfinder, the
trigger-and-still capture flow, and the recognition-overlay
state machine.

## 4. First `/inventory-add` walk-through

The skill path works today. From inside Claude Code, with the repo
checked out and the working tree clean:

```text
/inventory-add LM358N 5
```

What happens:

1. The skill identifies the part (LM358N — a dual op-amp from TI).
2. It searches for the datasheet, fills in the Octopart cell, picks
   the right section in `inventory/INVENTORY.md` (`## ICs`).
3. It inserts a new alphabetically-positioned row with
   `Source: manual`. The row carries the description, datasheet
   link, and notes — hedged where the identification is a guess.
4. If a stem-sibling already exists (e.g. you previously added
   `LM358P`), the skill offers the *family-page* pattern per
   IDEA-005 § Stage 2 — accept to mark both rows with a
   "Shares page with …" breadcrumb and generate a single shared
   page.
5. Once the row is committed, `/inventory-add` (after EPIC-007
   lands TASK-050) automatically chains into `/inventory-page LM358N`,
   which generates `inventory/parts/lm358n.md` — a one-page
   "what is this / how do I use it" reference linked from the
   inventory table.

The conventions the skill follows (sincere language, three-column
schema, family-page heuristic, hedge-language lint) are documented
in:

- [`.claude/skills/inventory-add/SKILL.md`](.claude/skills/inventory-add/SKILL.md)
- [`.claude/skills/inventory-page/SKILL.md`](.claude/skills/inventory-page/SKILL.md)
- [`docs/developers/ideas/archived/idea-004-markdown-inventory-schema.md`](docs/developers/ideas/archived/idea-004-markdown-inventory-schema.md)
- [`docs/developers/ideas/archived/idea-005-skill-path-today.md`](docs/developers/ideas/archived/idea-005-skill-path-today.md)

## 5. Working on the codebase

If you want to land code — fix a bug, add a feature, walk through
a task — start at
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the task-system walk and
the commit-policy quick reference. The release procedure is in
[`RELEASING.md`](RELEASING.md). Style and test conventions are at
[`docs/developers/CODING_STANDARDS.md`](docs/developers/CODING_STANDARDS.md)
and [`docs/developers/TESTING.md`](docs/developers/TESTING.md).

## When the doc gets you stuck

This is the doc-first bootstrap path. If you follow the steps and
hit a wall, **that's a doc bug** — file an issue (or open a PR
fixing the step that tripped you up). A `partsledger doctor`
health-check command was deferred per IDEA-012 Gap 5 in favour of
the doc-first approach; if doc fixes pile up faster than they land,
the doctor command lands as a follow-up task.
