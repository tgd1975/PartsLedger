#!/usr/bin/env python3
"""
DEPRECATED — prefer `scripts/housekeep.py` for the full flow (file
moves + overview regeneration). This script now runs only the
regeneration half and is kept as an internal helper that `housekeep.py`
delegates to. A future task will inline the logic here into
`housekeep.py` and remove this file.

Regenerate docs/developers/tasks/OVERVIEW.md from the task files
in docs/developers/tasks/{open,closed}/.

Usage: python scripts/update_task_overview.py
"""
import os
import re

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import task_system_config as tsc

_CFG = tsc.load(warn=False)
TASKS_DIR = tsc.get(_CFG, "tasks", "base_folder", default="docs/developers/tasks")
OPEN_DIR = os.path.join(TASKS_DIR, "open")
ACTIVE_DIR = os.path.join(TASKS_DIR, "active")
PAUSED_DIR = os.path.join(TASKS_DIR, "paused")
CLOSED_DIR = os.path.join(TASKS_DIR, "closed")
ARCHIVE_DIR = os.path.join(TASKS_DIR, "archive")
OVERVIEW = os.path.join(TASKS_DIR, "OVERVIEW.md")
PAUSED_ENABLED = tsc.paused_enabled(_CFG)
BURNUP_ENABLED = bool(tsc.get(_CFG, "visualizations", "burnup", "enabled", default=True))

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)


def _md_cell(text):
    """Escape free-text frontmatter for safe rendering in a markdown table cell.

    Mirrors the helper in housekeep.py — kept duplicated to avoid an
    import cycle (this module is invoked as a CLI from housekeep, and
    housekeep also imports configuration from task_system_config).
    Guards against MD033 (`<word>` parsed as inline HTML) and pipe
    characters that would split table cells.
    """
    return (
        str(text)
        .replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


MARKER_START = "<!-- GENERATED -->"
MARKER_END = "<!-- END GENERATED -->"
# A small second block above GENERATED that holds the counts line and the
# Jump-to index. Splitting them out keeps the at-a-glance metadata at the
# top of the file, with the burn-up charts (BURNUP block) slotting in
# between the header and the task tables.
HEADER_START = "<!-- HEADER -->"
HEADER_END = "<!-- END HEADER -->"


def parse_task_file(path):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    m = FRONTMATTER_RE.match(content)
    if not m:
        return None
    fields = dict(FIELD_RE.findall(m.group(1)))
    fields["_file"] = os.path.basename(path)
    return fields


def load_tasks(directory, status):
    """Load tasks from the root of directory only (ignores subdirectories).

    Epic files (id starting with `EPIC-`) are skipped — they live in the
    same folders as tasks but are rendered separately.
    """
    tasks = []
    if not os.path.isdir(directory):
        return tasks
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(directory, fname)
        if not os.path.isfile(path):
            continue
        task = parse_task_file(path)
        if task and str(task.get("id", "")).startswith("EPIC-"):
            continue
        if task:
            task.setdefault("status", status)
            tasks.append(task)
    return tasks


def load_archived_releases(archive_dir):
    """Return sorted list of version subdirectory names under archive/ (e.g. ['v0.1.0', 'v0.2.0'])."""
    if not os.path.isdir(archive_dir):
        return []
    return sorted(
        entry for entry in os.listdir(archive_dir)
        if os.path.isdir(os.path.join(archive_dir, entry))
        and re.fullmatch(r"v\d+\.\d+\.\d+", entry)
    )


def generate_release_overview(version, release_dir):
    """Write closed/<version>/OVERVIEW.md listing every task in that release folder."""
    tasks = load_tasks(release_dir, "closed")
    tasks.sort(key=lambda t: t.get("id", ""))

    lines = [
        f"# Tasks archived in {version}",
        "",
        f"**{len(tasks)} task(s) closed in this release.**",
        "",
        "| ID | Title | Effort | Complexity |",
        "|----|-------|--------|------------|",
    ]
    for t in tasks:
        task_id = t.get("id", "?")
        title = _md_cell(t.get("title", t["_file"]))
        effort = _md_cell(t.get("effort", "?"))
        complexity = _md_cell(t.get("complexity", "?"))
        lines.append(f"| [{task_id}]({t['_file']}) | {title} | {effort} | {complexity} |")

    out_path = os.path.join(release_dir, "OVERVIEW.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return out_path


def generate_release_overviews(archive_dir, versions):
    """Generate OVERVIEW.md for every archived release version."""
    generated = []
    for version in versions:
        release_dir = os.path.join(archive_dir, version)
        out_path = generate_release_overview(version, release_dir)
        generated.append(out_path)
    return generated


def read_frame():
    """Return (pre_header, between, suffix) — the three static spans of OVERVIEW.md.

    Layout the writer assembles:
        pre_header
        <!-- HEADER -->
        {counts + Jump-to}
        <!-- END HEADER -->
        between          ← preserved verbatim; this is where release_burnup
                           lands its <!-- BURNUP:START --> ... block
        <!-- GENERATED -->
        {task tables + archived releases}
        <!-- END GENERATED -->
        (trailing content, if any)

    `pre_header` is everything above the HEADER block (typically the H1).
    `between` is whatever sits between END HEADER and GENERATED — preserved
    so the BURNUP block (managed by release_burnup.py) survives regeneration.
    """
    default_pre = "\n# Task Overview\n\n"
    if not os.path.exists(OVERVIEW):
        return default_pre, "", "\n" + MARKER_END + "\n"
    with open(OVERVIEW, encoding="utf-8") as f:
        content = f.read()

    gen_start = content.find(MARKER_START)
    gen_end = content.find(MARKER_END)
    hdr_start = content.find(HEADER_START)
    hdr_end = content.find(HEADER_END)

    if gen_start == -1:
        # Brand-new or hand-written file with no GENERATED block yet — keep
        # whatever's there above, append a fresh frame below.
        pre = content.rstrip("\n") + "\n\n"
        return pre, "", "\n" + MARKER_END + "\n"

    if hdr_start != -1 and hdr_end != -1 and hdr_end < gen_start:
        pre_header = content[:hdr_start]
        between = content[hdr_end + len(HEADER_END): gen_start]
    else:
        # No HEADER block yet — first run after introducing it. Treat
        # everything above GENERATED as pre_header so we don't lose the H1.
        pre_header = content[:gen_start]
        between = ""

    suffix = "\n" + MARKER_END + (
        content[gen_end + len(MARKER_END):] if gen_end != -1 else "\n"
    )
    return pre_header, between, suffix


def main():
    open_tasks = load_tasks(OPEN_DIR, "open")
    active_tasks = load_tasks(ACTIVE_DIR, "active")
    paused_tasks = load_tasks(PAUSED_DIR, "paused") if PAUSED_ENABLED else []
    closed_tasks = load_tasks(CLOSED_DIR, "closed")
    archived_releases = load_archived_releases(ARCHIVE_DIR)
    # Active and paused tasks are tracked alongside open ones for rendering;
    # the per-section split below sorts them out.
    unfinished = active_tasks + paused_tasks + open_tasks

    pre_header, between, suffix = read_frame()

    n_open = sum(1 for t in unfinished if t.get("status") == "open")
    n_active = sum(1 for t in unfinished if t.get("status") == "active")
    n_paused = sum(1 for t in unfinished if t.get("status") == "paused")
    n_closed = len(closed_tasks)
    total = n_open + n_active + n_paused + n_closed
    pct = round(100 * n_closed / total) if total else 0
    filled = round(10 * pct / 100)
    bar = "█" * filled + "░" * (10 - filled)
    counts_parts = [
        f"⚪ **Open: {n_open}**",
        f"🔵 **Active: {n_active}**",
    ]
    if PAUSED_ENABLED:
        counts_parts.append(f"🟡 **Paused: {n_paused}**")
    counts_parts += [
        f"🟢 **Closed: {n_closed}**",
        f"**Total: {total}**",
        f"{bar} {pct}%",
    ]
    counts_line = " | ".join(counts_parts)
    index_parts = []
    if BURNUP_ENABLED:
        index_parts.append("[Burn-up](#burn-up)")
    index_parts.append("[Active Tasks](#active-tasks)")
    if PAUSED_ENABLED:
        index_parts.append("[Paused Tasks](#paused-tasks)")
    index_parts += ["[Open Tasks](#open-tasks)", "[Closed Tasks](#closed-tasks)"]
    index_line = "**Jump to:** " + " · ".join(index_parts)

    # Header block — counts + Jump-to. Lives above the BURNUP block.
    header_lines = [
        "",
        counts_line,
        "",
        index_line,
        "",
    ]

    # Generated block — task tables and archived releases.
    lines = [
        "",
        "## Active Tasks",
        "",
    ]

    def _folder_for(task):
        s = task.get("status")
        if s == "active":
            return "active"
        if s == "paused":
            return "paused"
        return "open"

    show_assigned = any(t.get("assigned") for t in unfinished + closed_tasks)

    def task_table_rows(tasks, header=True):
        rows = []
        if header:
            if show_assigned:
                rows += [
                    "| ID | Title | Effort | Complexity | Status | Assigned |",
                    "|----|-------|--------|------------|--------|----------|",
                ]
            else:
                rows += [
                    "| ID | Title | Effort | Complexity | Status |",
                    "|----|-------|--------|------------|--------|",
                ]
        for t in tasks:
            task_id = t.get("id", "?")
            title = _md_cell(t.get("title", t["_file"]))
            effort = _md_cell(t.get("effort", "?"))
            complexity = _md_cell(t.get("complexity", "?"))
            status = t.get("status", "open")
            if status == "active":
                status_badge = "🔵 **active**"
            elif status == "paused":
                status_badge = "🟡 **paused**"
            else:
                status_badge = "⚪ open"
            folder = _folder_for(t)
            row = (
                f"| [{task_id}]({folder}/{t['_file']}) | {title} |"
                f" {effort} | {complexity} | {status_badge} |"
            )
            if show_assigned:
                assigned = t.get("assigned", "")
                assigned_cell = f"@{assigned}" if assigned else ""
                row += f" {assigned_cell} |"
            rows.append(row)
        return rows

    only_active = [t for t in unfinished if t.get("status") == "active"]
    only_paused = [t for t in unfinished if t.get("status") == "paused"]
    only_open   = [t for t in unfinished if t.get("status") == "open"]

    if only_active:
        lines += task_table_rows(sorted(only_active, key=lambda t: t.get("id", "")))
    else:
        lines += ["_No active tasks._"]

    if PAUSED_ENABLED:
        lines += [
            "",
            "## Paused Tasks",
            "",
        ]
        if only_paused:
            lines += task_table_rows(sorted(only_paused, key=lambda t: t.get("id", "")))
        else:
            lines += ["_No paused tasks._"]

    lines += [
        "",
        "## Open Tasks",
        "",
    ]

    if only_open:
        lines += task_table_rows(sorted(only_open, key=lambda t: t.get("id", "")))
    else:
        lines += ["_No open tasks._"]

    lines += [
        "",
        "## Closed Tasks",
        "",
        "| ID | Title | Effort |",
        "|----|-------|--------|",
    ]

    for t in closed_tasks:
        task_id = t.get("id", "?")
        title = _md_cell(t.get("title", t["_file"]))
        effort = _md_cell(t.get("effort", "?"))
        lines.append(f"| [{task_id}](closed/{t['_file']}) | {title} | {effort} |")

    if archived_releases:
        lines += [
            "",
            "## Archived Releases",
            "",
        ]
        for version in archived_releases:
            lines.append(f"- [{version}](archive/{version}/OVERVIEW.md)")

    # Assemble: pre_header + HEADER block + preserved between-span (which
    # is where release_burnup lands its BURNUP block) + GENERATED block +
    # suffix. Each section is bracketed with explicit blank lines so the
    # file shape stays consistent across regenerations.
    pre_header = pre_header.rstrip("\n") + "\n\n"

    header_block = (
        HEADER_START + "\n\n"
        + "<!-- markdownlint-disable-file MD033 -->\n\n"
        + "\n".join(header_lines).strip("\n")
        + "\n\n" + HEADER_END + "\n\n"
    )

    if between.strip():
        # Preserve any user-visible content between END HEADER and
        # GENERATED (currently: the BURNUP block).
        between_block = between.strip("\n") + "\n\n"
    else:
        between_block = ""

    generated_block = MARKER_START + "\n\n" + "\n".join(lines).lstrip("\n") + suffix

    with open(OVERVIEW, "w", encoding="utf-8") as f:
        f.write(pre_header + header_block + between_block + generated_block)

    # Generate per-release OVERVIEW.md files
    release_overviews = generate_release_overviews(ARCHIVE_DIR, archived_releases)

    paused_summary = f", {len(paused_tasks)} paused" if PAUSED_ENABLED else ""
    print(f"Updated {OVERVIEW} ({len(unfinished)} unfinished{paused_summary}, "
          f"{len(closed_tasks)} closed, {len(archived_releases)} archived releases)")
    for p in release_overviews:
        print(f"  Generated {p}")


if __name__ == "__main__":
    main()
