#!/usr/bin/env python3
"""
Regenerate docs/developers/ideas/OVERVIEW.md from idea files in
docs/developers/ideas/open/.

Each file must contain YAML frontmatter with at least `id` and `title`
fields; `description` and `category` are optional. A missing `category`
renders as an em dash in the table.

Usage:
    python scripts/update_idea_overview.py            # write OVERVIEW.md
    python scripts/update_idea_overview.py --dry-run  # print to stdout
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_system_config as tsc

_CFG = tsc.load(warn=False)
IDEAS_DIR = tsc.get(_CFG, "ideas", "base_folder", default="docs/developers/ideas")
OPEN_DIR = os.path.join(IDEAS_DIR, "open")
ARCHIVED_DIR = os.path.join(IDEAS_DIR, "archived")
OVERVIEW = os.path.join(IDEAS_DIR, "OVERVIEW.md")

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)


def _md_cell(text):
    """Escape free-text frontmatter for safe rendering in a markdown table cell.

    Mirrors the helper in housekeep.py / update_task_overview.py.
    Guards against MD033 (`<word>` parsed as inline HTML) and pipe
    characters that would split table cells.
    """
    return (
        str(text)
        .replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# Main idea files are named `idea-NNN-<slug>.md`. Sub-notes attached to a
# main idea use a dot instead of the hyphen: `idea-NNN.<sub-slug>.md`.
# See docs/developers/ideas/README.md for the convention. Sub-notes never
# appear in OVERVIEW.
SUB_FILE_RE = re.compile(r"^idea-\d+\..+\.md$", re.IGNORECASE)


def is_sub_file(filename: str) -> bool:
    """True for sub-notes (`idea-NNN.<sub-slug>.md`), which OVERVIEW skips."""
    return bool(SUB_FILE_RE.match(filename))

# Emoji prefix per known idea category. Unknown categories render as bare text.
CATEGORY_ICONS = {
    "hardware": "🔧",
    "firmware": "⚡",
    "apps": "📱",
    "tooling": "🛠️",
    "docs": "📖",
    "outreach": "📣",
}


# U+00A0 keeps the emoji and the category name on the same line — a regular
# space lets narrow renderers wrap the name and orphan the icon.
_NBSP = " "


def format_category(category: str) -> str:
    """Render a category cell with an emoji prefix when known.

    Empty / missing → em dash.
    Known category  → "<emoji> <name>" (non-breaking space).
    Unknown name    → bare name (no icon).
    """
    name = (category or "").strip()
    if not name:
        return "—"
    icon = CATEGORY_ICONS.get(name)
    return f"{icon}{_NBSP}{name}" if icon else name


def parse_idea_file(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = FRONTMATTER_RE.match(content)
    if not m:
        return None
    fields = dict(FIELD_RE.findall(m.group(1)))
    fields["_file"] = os.path.basename(path)
    return fields


def load_ideas(directory):
    ideas = []
    if not os.path.isdir(directory):
        return ideas
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".md"):
            continue
        if is_sub_file(fname):
            continue
        idea = parse_idea_file(os.path.join(directory, fname))
        if idea:
            ideas.append(idea)
    return ideas


def render_overview(open_ideas, archived_ideas):
    lines = [
        "# Ideas Overview",
        "",
        f"**Open: {len(open_ideas)}** | **Archived: {len(archived_ideas)}**",
        "",
        "Ideas are lightweight, qualitative proposals tracked in"
        " [`open/`](open/) until they are either converted into structured"
        " tasks or archived. Archived ideas are kept for history in"
        " [`archived/`](archived/). See [README.md](README.md) for the"
        " file-naming convention (one row per IDEA, sub-notes use the"
        " `idea-NNN.<sub-slug>.md` form).",
        "",
        "## Open Ideas",
        "",
    ]

    if open_ideas:
        lines += [
            "| ID | Category | Title | Description |",
            "|----|----------|-------|-------------|",
        ]
        for idea in open_ideas:
            idea_id = idea.get("id", "?")
            title = _md_cell(idea.get("title", idea["_file"]))
            description = _md_cell(idea.get("description", ""))
            category = format_category(idea.get("category", ""))
            fname = idea["_file"]
            lines.append(
                f"| [{idea_id}](open/{fname}) | {category} | {title} | {description} |"
            )
    else:
        lines.append("_No open ideas._")

    if archived_ideas:
        lines += [
            "",
            "## Archived Ideas",
            "",
            "| ID | Category | Title |",
            "|----|----------|-------|",
        ]
        for idea in archived_ideas:
            idea_id = idea.get("id", "?")
            title = _md_cell(idea.get("title", idea["_file"]))
            category = format_category(idea.get("category", ""))
            fname = idea["_file"]
            lines.append(f"| [{idea_id}](archived/{fname}) | {category} | {title} |")

    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else "")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print generated OVERVIEW.md to stdout without writing.")
    args = parser.parse_args(argv)

    open_ideas = load_ideas(OPEN_DIR)
    archived_ideas = load_ideas(ARCHIVED_DIR)
    output = render_overview(open_ideas, archived_ideas)

    if args.dry_run:
        sys.stdout.write(output)
        return 0

    with open(OVERVIEW, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"Updated {OVERVIEW} ({len(open_ideas)} open, {len(archived_ideas)} archived)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
