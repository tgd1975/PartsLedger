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

## 3. First capture

EPIC-005 Phase 1 has landed: the camera-selection wizard, live
viewfinder with capture overlays, capture trigger + single-still
emit, and the thin `/capture` slash-skill are all in. Recognition
(EPIC-006) is a separate epic — for now, `<Space>` produces a
shutter-flash receipt + an in-memory frame (optionally dumped to
disk for inspection); identification still goes through
`/inventory-add` in Section 4.

From inside the repo, with the venv active:

```bash
python -m partsledger.capture
```

First run only: the camera-selection wizard prints a numbered list
of connected cameras by **friendly name** (e.g. *"046d Logitech
StreamCam DAE9AA45"*, *"Integrated Camera 0001"*). Pick the one
pointed at your parts mat; the choice is persisted to
`~/.config/partsledger/config.toml`. Re-running the CLI uses the
persisted choice silently.

Once the viewfinder is up:

- **Green rectangle** in the middle is the framing overlay — line
  the part up inside it.
- **Focus** (top-left) — Laplacian-variance traffic light. Green =
  sharp, amber = soft, red = blurry. Adjust working distance until
  it goes green.
- **Light** (top-left, below Focus) — mean luminance + clip-fraction
  traffic light. Green = balanced, amber = dim or hot, red = too
  dark / too clipped.
- **Press `<Space>` to capture** — bottom edge.

Press `<Space>` to capture. You'll see a brief shutter flash (white
border + "Captured") as visual confirmation. The frame is held in
memory ready for the recognition pipeline; nothing is written to
inventory at this stage (yet — that's EPIC-006 + EPIC-007).

Exit with `q`, `Esc`, the WM close button, or `Ctrl-C`. All four
release the camera cleanly.

Useful flags:

- `--pick-camera` — force the wizard to re-enter, even if a
  persisted choice still resolves.
- `--no-preview` — headless mode for scripted regression runs (no
  window opens; returns immediately).
- `--dump-captures-to <path>` — write each captured frame as a PNG
  into `<path>`. Filename is the metadata timestamp; files are
  **not** cleaned up at session end. Useful for collecting fixture
  images during EPIC-006 development.

Exit codes: `0` clean, `1` camera not resolvable, `2` display
backend unusable, `130` interrupted by `Ctrl-C`.

From inside Claude Code, `/capture` wraps the same CLI as a
subprocess — the viewfinder opens on your display, control returns
to the session when you exit.

### Troubleshooting

**Qt font warnings on Ubuntu** (`QFontDatabase: Cannot find font
directory ...cv2/qt/fonts`). Harmless — cv2's bundled Qt can't find
fallback fonts. The viewfinder still works.

The `opencv-python` wheel's embedded Qt looks for fonts inside its
own site-packages tree and **ignores `QT_QPA_FONTDIR`**. The fix is
a one-time symlink:

```bash
sudo apt install fonts-dejavu          # if not already installed

# Point the wheel's Qt at the system DejaVu fonts. Adjust the python3.X
# segment to match your venv.
mkdir -p .venv/lib/python3.X/site-packages/cv2/qt/fonts
ln -sf /usr/share/fonts/truetype/dejavu/*.ttf \
       .venv/lib/python3.X/site-packages/cv2/qt/fonts/
```

Persists for the lifetime of the venv; re-run after a `uv sync` that
rebuilds the cv2 install.

**`Warning: Ignoring XDG_SESSION_TYPE=wayland on Gnome.`** OpenCV's
window backend runs under XWayland. Harmless; the WM-close button,
`q`, `Esc`, and `Ctrl-C` all still route through the same cleanup
path.

**`No module named 'cv2'`.** You're not in the venv, or the venv
was built without the runtime deps. Re-run `uv sync` (or `uv pip
install opencv-python numpy` for the minimum capture-path footprint).

**Wizard re-enters every time.** Either no `[camera]` section
exists in `~/.config/partsledger/config.toml` yet, or the persisted
device no longer opens (unplugged, USB ID changed). This is the
fail-loud contract from IDEA-006 — the camera path will never
silently fall back to a different device.

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
