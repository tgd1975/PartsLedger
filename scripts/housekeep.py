#!/usr/bin/env python3
"""
Central housekeeping for the task system.

Scans task and epic files, moves them to the folder that matches their
`status:` frontmatter (open / active / closed), derives epic status
from the tasks that belong to it, and regenerates the overview files.

Default mode is dry-run — prints the planned actions but changes
nothing. Pass `--apply` to actually move files and write overviews.

Usage:
    python scripts/housekeep.py            # dry-run — print plan only
    python scripts/housekeep.py --apply    # execute moves and regen

Concurrency
-----------
`--apply` (and `--init` / `--fix-order`, which also write to disk)
acquires an exclusive lock on `<repo-root>/.housekeep.lock` before
doing any work. If another instance already holds the lock, the
second invocation **waits up to LOCK_WAIT_SECONDS for the lock**, then
exits non-zero with a message naming the holder's PID.

Rationale: housekeep is invoked from many independent paths
(pre-commit hook, /housekeep skill, /ts-task-* skills, manual runs)
and parallel Claude Code sessions are common in this repo, so two
runs can race and produce a half-correct index where the last writer
wins. Wait-then-fail-loud was picked because (a) the pre-commit hook
must not swallow regen failures, (b) silent skips desynchronise the
index from the moved file, and (c) the common case — a second run
triggered *after* the first finishes — "just works" via the wait.

The lock is acquired with `fcntl.flock` on POSIX and
`msvcrt.locking` on Windows, both of which release automatically when
the process exits. This means a stale lockfile on disk (from a
killed process) does not wedge future runs — do not "fix" this by
deleting the file at startup. Dry-run (no flag) does not acquire the
lock; it is a pure read.

Sibling-script audit (TASK-328)
-------------------------------
- `sync_task_system.py`: idempotent file copy from
  `awesome-task-system/` → live. Concurrent `--apply` runs copy the
  same source bytes to the same destination paths via `shutil.copy2`;
  last-writer-wins is benign because both writers produce identical
  bytes. **Safe — no lock needed.** `--check` is read-only.
- `update_task_overview.py`: regenerate `OVERVIEW.md` from task
  frontmatter. Only called by `housekeep.py` (the deprecated public
  path is documented in its docstring). Serialised by its caller, so
  it inherits housekeep's lock. **Safe — no lock needed.**
- `update_idea_overview.py`: regenerate ideas `OVERVIEW.md` from
  frontmatter. Called by `housekeep.py` via
  `regenerate_idea_overview()` during `apply_plan` when
  `ideas.enabled` is set. The output is a pure function of the
  on-disk idea files: two parallel runs reading the same tree write
  byte-identical bytes to the same path, so a last-writer-wins race
  is benign. **Safe — no extra lock needed beyond housekeep's own.**
  Re-evaluate if the script ever takes input from a non-deterministic
  source (clock, env, random ordering).
- `organize_closed_tasks.py`: explicit release-time archival
  (`v0.X.Y` argument), invoked by hand at release. No trigger
  fan-out. **Safe — no lock needed.**
"""
from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_system_config as tsc

_CFG = tsc.load(warn=False)
TASKS_DIR = Path(tsc.get(_CFG, "tasks", "base_folder", default="docs/developers/tasks"))
IDEAS_DIR = Path(tsc.get(_CFG, "ideas", "base_folder", default="docs/developers/ideas"))
_ACTIVE_ENABLED = bool(tsc.get(_CFG, "tasks", "active", "enabled", default=True))
_PAUSED_ENABLED = tsc.paused_enabled(_CFG)
_EPICS_ENABLED = bool(tsc.get(_CFG, "tasks", "epics", "enabled", default=True))
_BURNUP_ENABLED = bool(tsc.get(_CFG, "visualizations", "burnup", "enabled", default=True))
_IDEAS_ENABLED = bool(tsc.get(_CFG, "ideas", "enabled", default=True))


def _status_folders(active_enabled: bool, paused_enabled: bool) -> tuple[str, ...]:
    folders = ["open"]
    if active_enabled:
        folders.append("active")
    if paused_enabled:
        folders.append("paused")
    folders.append("closed")
    return tuple(folders)


TASK_STATUS_FOLDERS = _status_folders(_ACTIVE_ENABLED, _PAUSED_ENABLED)
ARCHIVE_FOLDER = "archive"

LOCK_FILENAME = ".housekeep.lock"
LOCK_WAIT_SECONDS = 30
LOCK_POLL_SECONDS = 0.2


def _lock_path() -> Path:
    """Return the path to the lock file at the repo root.

    The lock lives at the repo root (next to .git) rather than under
    /tmp so that runs against unrelated checkouts do not falsely
    serialise each other.
    """
    return Path.cwd() / LOCK_FILENAME


@contextlib.contextmanager
def acquire_lock(wait_seconds: float | None = None):
    """Acquire an exclusive process-wide lock for housekeep --apply.

    Waits up to `wait_seconds` (defaulting to module-level
    `LOCK_WAIT_SECONDS`, resolved at call time so tests can patch it)
    for the lock to become available. If the wait times out, raises
    SystemExit(2) with a message naming the PID of the current
    holder (best-effort — the file may have been released between
    the check and the message).

    The lock is held by an OS-level advisory lock on the file
    descriptor (`fcntl.flock` on POSIX, `msvcrt.locking` on Windows),
    which the kernel releases automatically when the process exits —
    so a stale lockfile on disk does not wedge future runs.
    """
    if wait_seconds is None:
        wait_seconds = LOCK_WAIT_SECONDS
    lock_path = _lock_path()
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        deadline = time.monotonic() + wait_seconds
        acquired = False
        while True:
            try:
                _platform_lock(fd)
                acquired = True
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    holder = _read_holder_pid(lock_path)
                    msg = (f"housekeep: another instance is running "
                           f"(holder PID={holder or 'unknown'}); "
                           f"timed out after {wait_seconds:g}s waiting "
                           f"for {lock_path}.")
                    print(msg, file=sys.stderr)
                    raise SystemExit(2)
                time.sleep(LOCK_POLL_SECONDS)
        # Record our PID in the lockfile so other waiters can name us
        # in their timeout message. Best-effort; a failure here does
        # not invalidate the lock.
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        except OSError:
            pass
        try:
            yield
        finally:
            if acquired:
                _platform_unlock(fd)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def _read_holder_pid(lock_path: Path) -> str | None:
    try:
        text = lock_path.read_text(encoding="ascii").strip()
        return text or None
    except OSError:
        return None


if sys.platform == "win32":  # pragma: no cover — exercised on Windows only
    import msvcrt

    def _platform_lock(fd: int) -> None:
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise BlockingIOError(str(exc)) from exc

    def _platform_unlock(fd: int) -> None:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def _platform_lock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _platform_unlock(fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)

# Files at the root of TASKS_DIR that are generated — do not touch.
GENERATED_FILES = {"OVERVIEW.md", "EPICS.md", "KANBAN.md"}


@dataclass
class Move:
    src: Path
    dst: Path
    reason: str

    def describe(self) -> str:
        return f"MOVE {self.src.as_posix()} -> {self.dst.as_posix()}  ({self.reason})"

    def apply(self) -> None:
        self.dst.parent.mkdir(parents=True, exist_ok=True)
        # Prefer `git mv` so history follows the file; fall back to a
        # plain rename if the tree is not a git repo.
        if (Path.cwd() / ".git").exists():
            subprocess.run(
                ["git", "mv", str(self.src), str(self.dst)],
                check=True,
            )
        else:
            os.replace(self.src, self.dst)


@dataclass
class Plan:
    moves: list[Move] = field(default_factory=list)
    regen: bool = False
    stubs: list[Path] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.moves and not self.regen and not self.stubs


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(path: Path) -> dict | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = FRONTMATTER_RE.match(content)
    if not m:
        return None
    fields = dict(FIELD_RE.findall(m.group(1)))
    fields["_path"] = path
    return fields


def scan_folder(root: Path, status_folders: tuple[str, ...]) -> list[dict]:
    """Return frontmatter dicts for every .md in root/<status>/ (non-recursive).

    Files under `archive/` are ignored — those are release snapshots.
    """
    items: list[dict] = []
    for status in status_folders:
        folder = root / status
        if not folder.is_dir():
            continue
        for fname in sorted(os.listdir(folder)):
            if not fname.endswith(".md"):
                continue
            p = folder / fname
            if not p.is_file():
                continue
            data = parse_frontmatter(p)
            if data is None:
                continue
            data["_folder"] = status
            items.append(data)
    return items


def scan_tasks() -> list[dict]:
    return scan_folder(TASKS_DIR, TASK_STATUS_FOLDERS)


def scan_epics() -> list[dict]:
    # Epic files have the same folder layout; distinguish by `id` prefix.
    all_items = scan_folder(TASKS_DIR, TASK_STATUS_FOLDERS)
    return [i for i in all_items if str(i.get("id", "")).startswith("EPIC-")]


def scan_task_items_only(items: list[dict]) -> list[dict]:
    return [i for i in items if str(i.get("id", "")).startswith("TASK-")]


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def derive_epic_status(epic_name: str, tasks: list[dict]) -> str | None:
    """Return derived status for an epic, or None if the epic has no tasks.

    Paused does not propagate — an all-paused epic still derives to active
    (and an open+paused epic still derives to active). Paused only contributes
    to per-epic counts in the rendered tables.
    """
    statuses = {t.get("status") for t in tasks if t.get("epic") == epic_name}
    statuses.discard(None)
    if not statuses:
        return None
    if statuses == {"closed"}:
        return "closed"
    if statuses == {"open"}:
        return "open"
    return "active"  # mixed open/closed/active/paused → in progress


def plan_moves_for_items(items: list[dict]) -> list[Move]:
    moves: list[Move] = []
    for item in items:
        status = item.get("status")
        folder = item["_folder"]
        path: Path = item["_path"]
        if status not in TASK_STATUS_FOLDERS:
            continue
        if status == folder:
            continue
        dst = path.parent.parent / status / path.name
        moves.append(Move(src=path, dst=dst,
                          reason=f"{item.get('id', path.name)} status={status}"))
    return moves


def plan_epic_moves(epics: list[dict], tasks: list[dict]) -> list[Move]:
    moves: list[Move] = []
    for epic in epics:
        epic_name = epic.get("epic") or epic.get("name") or epic.get("id", "")
        derived = derive_epic_status(epic_name, tasks)
        if derived is None:
            continue
        folder = epic["_folder"]
        if derived == folder:
            continue
        path: Path = epic["_path"]
        dst = path.parent.parent / derived / path.name
        moves.append(Move(src=path, dst=dst,
                          reason=f"epic {epic.get('id')} derived={derived}"))
    return moves


def build_plan(tasks_dir: Path = TASKS_DIR,
               status_folders: tuple[str, ...] = TASK_STATUS_FOLDERS,
               epics_enabled: bool = True) -> Plan:
    plan = Plan()
    items = scan_folder(tasks_dir, status_folders)
    tasks = scan_task_items_only(items)
    plan.moves.extend(plan_moves_for_items(tasks))
    if epics_enabled:
        epics = [i for i in items if str(i.get("id", "")).startswith("EPIC-")]
        plan.moves.extend(plan_epic_moves(epics, tasks))
    plan.regen = True
    return plan


# ---------------------------------------------------------------------------
# Shared display helpers
# ---------------------------------------------------------------------------

STATUS_ICON = {"open": "⚪", "active": "🔵", "closed": "🟢", "paused": "🟡"}


def _md_cell(text: str) -> str:
    """Escape free-text frontmatter fields for safe rendering in a markdown table cell.

    Markdownlint rules guarded:
      MD033 (no-inline-html) — `<word>` placeholders in titles like
        `archive/<version>/` would otherwise be parsed as raw HTML.
        Replace `<` / `>` with HTML entities so the rendered glyph is
        identical but the linter sees no tag.
      Table column separators — escape `|` so a stray pipe in a title
        does not split the cell.
    """
    return (
        str(text)
        .replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _progress_bar(pct: int, width: int = 10) -> str:
    filled = round(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


def _status_badge(status: str | None) -> str:
    icon = STATUS_ICON.get(status or "open", "⚪")
    label = {
        "closed": "closed",
        "active": "**active**",
        "paused": "**paused**",
    }.get(status or "", f"_{status}_")
    return f"{icon} {label}"


# Overview regeneration (delegates to existing update_task_overview.py logic)
# ---------------------------------------------------------------------------

def regenerate_overview() -> None:
    # Delegate to the existing generator so the output format stays in
    # one place until TASK-220 folds the full logic in here.
    script = Path(__file__).resolve().parent / "update_task_overview.py"
    subprocess.run([sys.executable, str(script)], check=True)
    _refresh_burnup_section()


def regenerate_idea_overview() -> None:
    """Regenerate ideas/OVERVIEW.md by delegating to update_idea_overview.py.

    Same delegate-to-existing-script pattern as `regenerate_overview()`
    for the tasks side — keeps the rendering format in one place.
    """
    script = Path(__file__).resolve().parent / "update_idea_overview.py"
    subprocess.run([sys.executable, str(script)], check=True)


def _refresh_burnup_section() -> None:
    """Regenerate (or remove) the BURNUP block in OVERVIEW.md.

    Delegated to release_burnup.render_block() / update_overview_section().
    Idempotent: if the new bytes match the existing slice, OVERVIEW.md is
    not touched.

    When `visualizations.burnup.enabled` is false, any previously-written
    BURNUP block is stripped instead — toggling the flag off cleans up
    rather than freezing stale content.
    """
    try:
        import release_burnup  # type: ignore
    except ImportError:
        return
    overview = TASKS_DIR / "OVERVIEW.md"
    if not _BURNUP_ENABLED:
        release_burnup.remove_overview_section(overview)
        return
    repo_root = Path.cwd()
    block = release_burnup.render_block(repo_root)
    release_burnup.update_overview_section(overview, block)


# ---------------------------------------------------------------------------
# EPICS.md generation
# ---------------------------------------------------------------------------

_EFFORT_DAYS = {
    "trivial": "1d",
    "small": "2d",
    "medium": "5d",
    "large": "12d",
    "extra large": "20d",
    "extra-large": "20d",
}

_PREREQ_RE = re.compile(r"TASK-\d+")


def _parse_prereqs(raw: str) -> list[str]:
    """Extract TASK-NNN ids from a prerequisites: field value like '[TASK-210, TASK-211]'."""
    return _PREREQ_RE.findall(raw)


def _node_id(task_id: str) -> str:
    return task_id.replace("-", "_")


def _graph_direction(task_ids: set[str], edges: list[tuple[str, str]]) -> str:
    """Auto-detect Mermaid graph direction.

    Rules (in priority order):
    1. No edges at all → LR (flat row of nodes).
    2. More than 4 root nodes (no predecessors within the epic) → LR
       (very wide fan — horizontal avoids a towering column).
    3. Otherwise → LR when depth > width, TD when width >= depth.
    """
    from collections import deque

    local_ids = task_ids
    successors: dict[str, list[str]] = {t: [] for t in local_ids}
    in_degree: dict[str, int] = {t: 0 for t in local_ids}
    for src, dst in edges:
        if src in local_ids and dst in local_ids:
            successors[src].append(dst)
            in_degree[dst] += 1

    roots = [t for t in local_ids if in_degree[t] == 0]

    # Rule 1 — no dependencies
    if not edges:
        return "LR"

    # Rule 2 — wide fan
    if len(roots) > 4:
        return "LR"

    # Rule 3 — depth vs width heuristic
    dist: dict[str, int] = {t: 0 for t in local_ids}
    queue: deque[str] = deque(roots)
    temp_in = dict(in_degree)
    while queue:
        node = queue.popleft()
        for nxt in successors[node]:
            dist[nxt] = max(dist[nxt], dist[node] + 1)
            temp_in[nxt] -= 1
            if temp_in[nxt] == 0:
                queue.append(nxt)

    depth = max(dist.values(), default=0) + 1
    width = len(roots)
    return "LR" if depth > width else "TD"


_CLASS_FOR_STATUS = {
    "open":   "open",
    "active": "active",
    "closed": "closed",
    "paused": "paused",
}


def _dep_graph_section(tasks: list[dict],
                       all_tasks: list[dict] | None = None) -> list[str]:
    """Render a Mermaid dependency graph for the given epic's tasks.

    Direction is auto-detected: LR for deep chains, TD for wide fans.

    `all_tasks` (optional) lets the renderer style and link cross-epic
    prerequisite nodes (e.g. TASK-108 referenced from EPIC-003) using the
    referenced task's real status and file path.
    """
    task_ids: set[str] = {str(t.get("id", "")) for t in tasks}
    edges: list[tuple[str, str]] = []
    for t in tasks:
        tid = str(t.get("id", "?"))
        for prereq in _parse_prereqs(str(t.get("prerequisites", ""))):
            edges.append((prereq, tid))

    direction = _graph_direction(task_ids, edges)
    lines = ["```mermaid", f"graph {direction}"]

    by_id: dict[str, dict] = {}
    if all_tasks:
        for t in all_tasks:
            by_id[str(t.get("id", ""))] = t

    click_lines: list[str] = []

    def _emit_node(tid: str, status: str, *, external: bool) -> None:
        # Label is the task ID only — full titles bloat the box and force
        # Mermaid to shrink the SVG, which makes the colored borders look
        # like hairlines for large epics. The flat list below the graph
        # carries the full titles.
        nid = _node_id(tid)
        base = _CLASS_FOR_STATUS.get(status, "open")
        cls = f"{base}Ext" if external else base
        lines.append(f'    {nid}["{tid}"]:::{cls}')

    for t in tasks:
        tid = str(t.get("id", "?"))
        _emit_node(tid, t.get("status", "open"), external=False)
        fname = Path(str(t.get("_path", tid))).name
        folder = {"closed": "closed", "active": "active"}.get(
            t.get("status", "open"), "open")
        click_lines.append(f'    click {_node_id(tid)} "{folder}/{fname}"')

    # External (cross-epic) prerequisite nodes — referenced by id but never
    # declared as in-epic tasks. Style by their real status when known, and
    # link to their task file so the diagram is navigable.
    referenced = {src for src, _ in edges} | {dst for _, dst in edges}
    external = sorted(referenced - task_ids)
    for tid in external:
        meta = by_id.get(tid)
        if meta:
            status = meta.get("status", "open")
            _emit_node(tid, status, external=True)
            fname = Path(str(meta.get("_path", tid))).name
            folder = {"closed": "closed", "active": "active"}.get(status, "open")
            click_lines.append(f'    click {_node_id(tid)} "{folder}/{fname}"')
        else:
            _emit_node(tid, "open", external=True)

    for src, dst in edges:
        lines.append(f"    {_node_id(src)} --> {_node_id(dst)}")

    # Chain nodes that have no predecessor within the epic with invisible edges
    # so Dagre places them in a row rather than stacking them vertically.
    has_predecessor = {dst for _, dst in edges if dst in task_ids}
    floating = [t for t in task_ids if t not in has_predecessor]
    if len(floating) > 1:
        chain = " ~~~ ".join(_node_id(t) for t in sorted(floating))
        lines.append(f"    {chain}")

    lines += click_lines

    # In-epic nodes: light fill, bold border in the status color.
    # External nodes: same bold colored border, black fill, light ink.
    # Status palette — open/gray, active/blue, closed/green, paused/amber.
    lines += [
        "    classDef open    fill:#FAFAFA,stroke:#555,stroke-width:8px,color:#000",
        "    classDef active  fill:#FAFAFA,stroke:#1A6FA8,stroke-width:8px,color:#000",
        "    classDef closed  fill:#FAFAFA,stroke:#3F8B53,stroke-width:8px,color:#000",
        "    classDef paused  fill:#FAFAFA,stroke:#B07810,stroke-width:8px,color:#000",
        "    classDef openExt    fill:#000,stroke:#888,stroke-width:8px,color:#FFF",
        "    classDef activeExt  fill:#000,stroke:#3FA9F5,stroke-width:8px,color:#FFF",
        "    classDef closedExt  fill:#000,stroke:#7CC68A,stroke-width:8px,color:#FFF",
        "    classDef pausedExt  fill:#000,stroke:#F0B030,stroke-width:8px,color:#FFF",
        "```",
    ]
    return lines


_STATUS_SORT_RANK = {"open": 0, "paused": 1, "active": 2, "closed": 3}


def _flat_list_sort_key(t: dict) -> tuple[int, int]:
    """Primary by status (open > paused > active > closed), secondary by order:."""
    status = t.get("status", "open")
    rank = _STATUS_SORT_RANK.get(status, 99)
    try:
        order = int(t.get("order", 999))
    except (TypeError, ValueError):
        order = 999
    return (rank, order)


def _flat_list_section(tasks: list[dict]) -> list[str]:
    lines = [
        "| Order | ID | Title | Status | Effort |",
        "|-------|----|-------|--------|--------|",
    ]
    for t in sorted(tasks, key=_flat_list_sort_key):
        tid = t.get("id", "?")
        title = _md_cell(t.get("title", "?"))
        status = t.get("status", "open")
        effort = _md_cell(t.get("effort", "?"))
        fname = Path(str(t.get("_path", tid))).name
        folder = {"closed": "closed", "active": "active",
                  "paused": "paused"}.get(status, "open")
        status_display = _status_badge(status)
        title_display = f"~~{title}~~" if status == "closed" else title
        id_display = f"~~[{tid}]({folder}/{fname})~~" if status == "closed" else f"[{tid}]({folder}/{fname})"
        lines.append(f"| {t.get('order','?')} | {id_display} |"
                     f" {title_display} | {status_display} | {effort} |")
    return lines


def _gantt_section(tasks: list[dict]) -> list[str]:
    lines = ["```mermaid", "gantt", "    dateFormat YYYY-MM-DD",
             "    title Epic tasks"]
    for t in sorted(tasks, key=lambda t: int(t.get("order", 999))):
        tid = t.get("id", "?")
        title = t.get("title", tid)
        effort_raw = t.get("effort", "").lower().split("(")[0].strip()
        duration = _EFFORT_DAYS.get(effort_raw, "3d")
        status = t.get("status", "open")
        done = "done, " if status == "closed" else ""
        active = "active, " if status == "active" else ""
        lines.append(f"    {title} ({tid}) :{done}{active}{_node_id(tid)}, 0d, {duration}")
    lines.append("```")
    return lines


def generate_epics_md(tasks_dir: Path = TASKS_DIR,
                      status_folders: tuple[str, ...] = TASK_STATUS_FOLDERS,
                      cfg: dict | None = None) -> None:
    """Generate EPICS.md with one section per epic."""
    if cfg is None:
        cfg = _CFG
    epics_viz_enabled = bool(tsc.get(cfg, "visualizations", "epics", "enabled", default=True))
    if not epics_viz_enabled:
        return
    style = tsc.get(cfg, "visualizations", "epics", "style", default="dependency-graph")

    all_items = scan_folder(tasks_dir, status_folders)
    tasks = scan_task_items_only(all_items)
    epics = [i for i in all_items if str(i.get("id", "")).startswith("EPIC-")]

    # Group tasks by epic name
    by_epic: dict[str, list[dict]] = {}
    for t in tasks:
        epic_name = t.get("epic")
        if epic_name:
            by_epic.setdefault(epic_name, []).append(t)

    lines = [
        "# Epics",
        "",
        "_Auto-generated by `housekeep.py`. Do not edit manually._",
        "",
    ]

    if not epics and not by_epic:
        lines.append("_No epics defined._")
    else:
        # Build a lookup from epic name → epic file metadata
        epic_meta: dict[str, dict] = {}
        for e in epics:
            name = e.get("epic") or e.get("name") or str(e.get("id", ""))
            epic_meta[name] = e

        # Index table — sorted by EPIC-NNN id numerically
        def _epic_sort_key(name: str) -> int:
            meta = epic_meta.get(name, {})
            eid = str(meta.get("id", "EPIC-999"))
            try:
                return int(eid.split("-")[1])
            except (IndexError, ValueError):
                return 999

        def _task_counts(epic_name: str) -> tuple[int, int, int, int, int]:
            """Return (n_open, n_active, n_paused, n_closed, pct_closed) for an epic."""
            ts = by_epic.get(epic_name, [])
            n_open   = sum(1 for t in ts if t.get("status") == "open")
            n_active = sum(1 for t in ts if t.get("status") == "active")
            n_paused = sum(1 for t in ts if t.get("status") == "paused")
            n_closed = sum(1 for t in ts if t.get("status") == "closed")
            total = n_open + n_active + n_paused + n_closed
            pct = round(100 * n_closed / total) if total else 0
            return n_open, n_active, n_paused, n_closed, pct

        show_paused_col = _PAUSED_ENABLED

        index_rows = []
        total_open = total_active = total_paused = total_closed = 0
        for epic_name in sorted(by_epic.keys(), key=_epic_sort_key):
            meta = epic_meta.get(epic_name, {})
            epic_id = meta.get("id", epic_name)
            epic_title_raw = meta.get("title", epic_name)
            epic_title = _md_cell(epic_title_raw)
            epic_status = derive_epic_status(epic_name, tasks)
            badge = _status_badge(epic_status)
            anchor = re.sub(r"[^a-z0-9 _-]", "", f"{epic_id}-{epic_title_raw}".lower()).replace(" ", "-")
            n_open, n_active, n_paused, n_closed, pct = _task_counts(epic_name)
            bar = _progress_bar(pct)
            paused_cell = f" {n_paused} |" if show_paused_col else ""
            index_rows.append(
                f"| [{epic_id}](#{anchor}) | {epic_title} | {badge}"
                f" | {n_open} | {n_active} |{paused_cell} {n_closed} | {bar} {pct}% |"
            )
            total_open   += n_open
            total_active += n_active
            total_paused += n_paused
            total_closed += n_closed

        # Add unassigned row to index
        unepiced_all = [t for t in tasks if not t.get("epic")]
        if unepiced_all:
            u_open   = sum(1 for t in unepiced_all if t.get("status") == "open")
            u_active = sum(1 for t in unepiced_all if t.get("status") == "active")
            u_paused = sum(1 for t in unepiced_all if t.get("status") == "paused")
            u_closed = sum(1 for t in unepiced_all if t.get("status") == "closed")
            u_total  = u_open + u_active + u_paused + u_closed
            u_pct    = round(100 * u_closed / u_total) if u_total else 0
            if u_open == 0 and u_active == 0 and u_paused == 0:
                u_status = "closed"
            elif u_closed == 0 and u_active == 0 and u_paused == 0:
                u_status = "open"
            else:
                u_status = "active"
            u_badge  = _status_badge(u_status)
            u_bar    = _progress_bar(u_pct)
            paused_cell = f" {u_paused} |" if show_paused_col else ""
            index_rows.append(
                f"| [—](#unassigned) | _(no epic)_ | {u_badge}"
                f" | {u_open} | {u_active} |{paused_cell} {u_closed} | {u_bar} {u_pct}% |"
            )
            total_open   += u_open
            total_active += u_active
            total_paused += u_paused
            total_closed += u_closed

        # Overall totals — summary across all epics + unassigned, shown above the index
        grand_total = total_open + total_active + total_paused + total_closed
        summary_lines: list[str] = []
        if grand_total:
            t_pct    = round(100 * total_closed / grand_total)
            if total_open == 0 and total_active == 0 and total_paused == 0:
                t_status = "closed"
            elif total_closed == 0 and total_active == 0 and total_paused == 0:
                t_status = "open"
            else:
                t_status = "active"
            t_badge  = _status_badge(t_status)
            t_bar    = _progress_bar(t_pct)
            n_groups = len(by_epic) + (1 if unepiced_all else 0)
            groups_label = f"{n_groups} group" + ("s" if n_groups != 1 else "")
            paused_segment = f" · {total_paused} paused" if show_paused_col else ""
            summary_lines = [
                f"**Overall:** {t_badge} — {t_bar} {total_closed}/{grand_total} ({t_pct}%)"
                f" across {groups_label} — {total_open} open · {total_active} active{paused_segment} · {total_closed} closed",
                "",
            ]

        if show_paused_col:
            header_row = "| Epic | Title | Status | Open | Active | Paused | Closed | Done |"
            sep_row    = "|------|-------|--------|-----:|-------:|-------:|-------:|------|"
        else:
            header_row = "| Epic | Title | Status | Open | Active | Closed | Done |"
            sep_row    = "|------|-------|--------|-----:|-------:|-------:|------|"

        lines += summary_lines + [
            "## Index",
            "",
            header_row,
            sep_row,
        ] + index_rows + ["", "---", ""]

        # Per-epic sections render in the same order as the index above
        # (numerical EPIC-NNN ascending), not alphabetical. Keeps the
        # page top-to-bottom navigation consistent with the index links.
        for epic_name in sorted(by_epic.keys(), key=_epic_sort_key):
            meta = epic_meta.get(epic_name, {})
            epic_id = meta.get("id", epic_name)
            epic_title = _md_cell(meta.get("title", epic_name))
            epic_status = derive_epic_status(epic_name, tasks)
            assigned = meta.get("assigned", "")
            assigned_str = f" — @{assigned}" if assigned else ""
            n_open, n_active, n_paused, n_closed, pct = _task_counts(epic_name)
            bar = _progress_bar(pct)
            denom = n_open + n_active + n_paused + n_closed

            badge = _status_badge(epic_status)
            lines += [
                f"## {epic_id}: {epic_title}",
                "",
                "[↑ back to top](#index)",
                "",
                f"**Status:** {badge}{assigned_str} — "
                f"{bar} {n_closed}/{denom} ({pct}%)",
                "",
            ]

            epic_tasks = by_epic[epic_name]
            if style == "gantt":
                lines += _gantt_section(epic_tasks)
            else:
                lines += _dep_graph_section(epic_tasks, all_tasks=tasks)
                lines.append("")
                lines += _flat_list_section(epic_tasks)
            lines.append("")

        # Tasks without an epic
        unepiced = [t for t in tasks if not t.get("epic")]
        if unepiced:
            n_open   = sum(1 for t in unepiced if t.get("status") == "open")
            n_active = sum(1 for t in unepiced if t.get("status") == "active")
            n_paused = sum(1 for t in unepiced if t.get("status") == "paused")
            n_closed = sum(1 for t in unepiced if t.get("status") == "closed")
            total    = n_open + n_active + n_paused + n_closed
            pct      = round(100 * n_closed / total) if total else 0
            bar      = _progress_bar(pct)
            if n_open == 0 and n_active == 0 and n_paused == 0:
                status = "closed"
            elif n_closed == 0 and n_active == 0 and n_paused == 0:
                status = "open"
            else:
                status = "active"
            badge    = _status_badge(status)
            lines += [
                "## Unassigned",
                "",
                "[↑ back to top](#index)",
                "",
                f"**Status:** {badge} — {bar} {n_closed}/{total} ({pct}%)",
                "",
            ]
            lines += _dep_graph_section(unepiced, all_tasks=tasks)
            lines.append("")
            lines += _flat_list_section(unepiced)
            lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    out_path = tasks_dir / "EPICS.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


STUB_CONTENT = {
    "EPICS.md": (
        "# Epics\n\n"
        "_Auto-generated by `housekeep.py`._\n"
    ),
    "KANBAN.md": (
        "# Kanban Board\n\n"
        "_Stub — full kanban board is generated by `housekeep.py` once"
        " TASK-220 lands._\n"
    ),
}


def write_stubs(paths: list[Path]) -> None:
    for p in paths:
        p.write_text(STUB_CONTENT.get(p.name, ""), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_plan(plan: Plan, stream=sys.stdout) -> None:
    if plan.is_empty():
        print("housekeep: nothing to do.", file=stream)
        return
    if plan.moves:
        print(f"housekeep: {len(plan.moves)} file move(s) planned:", file=stream)
        for m in plan.moves:
            print(f"  {m.describe()}", file=stream)
    if plan.stubs:
        print(f"housekeep: {len(plan.stubs)} stub file(s) will be created:",
              file=stream)
        for p in plan.stubs:
            print(f"  CREATE {p}", file=stream)
    if plan.regen:
        regen_files = ["tasks/OVERVIEW.md"]
        if _EPICS_ENABLED:
            regen_files.append("tasks/EPICS.md")
        if _KANBAN_ENABLED:
            regen_files.append("tasks/KANBAN.md")
        if _IDEAS_ENABLED:
            regen_files.append("ideas/OVERVIEW.md")
        print(f"housekeep: {', '.join(regen_files)} will be regenerated.", file=stream)


_KANBAN_ENABLED = bool(tsc.get(_CFG, "visualizations", "kanban", "enabled", default=True))


def generate_kanban_md(tasks_dir: Path = TASKS_DIR,
                       status_folders: tuple[str, ...] = TASK_STATUS_FOLDERS,
                       cfg: dict | None = None) -> None:
    """Generate KANBAN.md — one kanban block per epic (alphabetical) plus Others.

    Each section has an index at the top and a stats line (open/active/closed).
    Labels use Mermaid quoted syntax so special characters are preserved.
    """
    if cfg is None:
        cfg = _CFG
    kanban_enabled = bool(tsc.get(cfg, "visualizations", "kanban", "enabled", default=True))
    if not kanban_enabled:
        return

    active_enabled = bool(tsc.get(cfg, "tasks", "active", "enabled", default=True))
    paused_enabled = tsc.paused_enabled(cfg)

    all_items = scan_folder(tasks_dir, status_folders)
    tasks = scan_task_items_only(all_items)

    valid_statuses = {"open", "active", "closed"}
    if paused_enabled:
        valid_statuses.add("paused")

    def _empty_buckets() -> dict[str, list[dict]]:
        b = {"open": [], "active": [], "paused": [], "closed": []}
        return b

    # Bucket tasks by epic, then by status
    by_epic: dict[str, dict[str, list[dict]]] = {}
    no_epic: dict[str, list[dict]] = _empty_buckets()

    for t in tasks:
        status = t.get("status", "open")
        if status not in valid_statuses:
            continue
        epic = t.get("epic", "")
        if epic:
            if epic not in by_epic:
                by_epic[epic] = _empty_buckets()
            by_epic[epic][status].append(t)
        else:
            no_epic[status].append(t)

    def _has_unfinished(buckets: dict[str, list[dict]]) -> bool:
        return bool(buckets["open"] or buckets["active"] or buckets["paused"])

    # Only include epics that have at least one open / active / paused task
    active_epics = sorted(
        (e for e in by_epic if _has_unfinished(by_epic[e])),
        key=str.casefold,
    )

    def card(t: dict) -> str:
        tid = t.get("id", "?")
        title = t.get("title", tid)
        assigned = t.get("assigned", "")
        label = f"{title} @{assigned}" if assigned else title
        # Mermaid kanban: `"` ends the quoted label; a leading `` ` `` after `["`
        # switches mermaid into markdown-string mode and breaks parsing on
        # subsequent backticks (CI failure mode in TASK-321 — task titles like
        # ``/ts-task-active` nags…``). Strip both. Angle brackets are also
        # stripped — inside a fenced ```mermaid block markdownlint does not flag
        # them, but Mermaid itself can mis-parse `<` in labels in some renderers.
        label = label.replace('"', "").replace("`", "").replace("<", "").replace(">", "")
        return f'    {_node_id(tid)}["{label}"]'

    columns: list[tuple[str, str]] = [("open", "Open")]
    if active_enabled:
        columns.append(("active", "Active"))
    if paused_enabled:
        columns.append(("paused", "Paused"))
    columns.append(("closed", "Closed"))

    def kanban_block(buckets: dict[str, list[dict]]) -> list[str]:
        lines = ["```mermaid", "kanban"]
        for status_key, col_label in columns:
            lines.append(f"  {col_label}")
            for t in sorted(buckets.get(status_key, []), key=lambda x: x.get("id", "")):
                lines.append(card(t))
        lines.append("```")
        return lines

    def stats(buckets: dict[str, list[dict]]) -> str:
        n_open   = len(buckets["open"])
        n_active = len(buckets["active"])
        n_paused = len(buckets["paused"])
        n_closed = len(buckets["closed"])
        total = n_open + n_active + n_paused + n_closed
        pct = round(100 * n_closed / total) if total else 0
        bar = _progress_bar(pct)
        parts = [f"{STATUS_ICON['open']} {n_open} open"]
        if active_enabled:
            parts.append(f"{STATUS_ICON['active']} {n_active} active")
        if paused_enabled:
            parts.append(f"{STATUS_ICON['paused']} {n_paused} paused")
        parts.append(f"{STATUS_ICON['closed']} {n_closed} closed")
        parts.append(f"{bar} {pct}%")
        return f"_{' · '.join(parts)}_"

    # Build index
    index_entries = [
        f"[{_md_cell(e)}](#{e.lower().replace(' ', '-')})"
        for e in active_epics
    ]
    if _has_unfinished(no_epic):
        index_entries.append("[Other](#other)")

    epics_line = (
        "**Epics:** " + " · ".join(index_entries)
        if index_entries
        else "**Epics:** _none_"
    )
    out: list[str] = [
        "# Kanban Board",
        "",
        "_Auto-generated by `housekeep.py`. Do not edit manually._",
        "",
        epics_line,
        "",
    ]

    for epic in active_epics:
        buckets = by_epic[epic]
        out.append(f"## {_md_cell(epic)}")
        out.append("")
        out.append(stats(buckets))
        out.append("")
        out.extend(kanban_block(buckets))
        out.append("")

    if _has_unfinished(no_epic):
        out.append("## Other")
        out.append("")
        out.append(stats(no_epic))
        out.append("")
        out.extend(kanban_block(no_epic))
        out.append("")

    while out and out[-1] == "":
        out.pop()
    out_path = tasks_dir / "KANBAN.md"
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def apply_plan(plan: Plan) -> None:
    for move in plan.moves:
        move.apply()
    write_stubs(plan.stubs)
    if plan.regen:
        regenerate_overview()
        if _EPICS_ENABLED:
            generate_epics_md()
        if _KANBAN_ENABLED:
            generate_kanban_md()
        if _IDEAS_ENABLED:
            regenerate_idea_overview()


def run_init(cfg: dict) -> int:
    """Create the folder structure and stub files needed by the task system.

    Idempotent — existing folders are left alone, existing overview
    files are kept (a warning is printed for each one so the user
    knows it was not overwritten).
    """
    tasks_enabled = bool(tsc.get(cfg, "tasks", "enabled", default=True))
    ideas_enabled = bool(tsc.get(cfg, "ideas", "enabled", default=True))
    active_enabled = bool(tsc.get(cfg, "tasks", "active", "enabled", default=True))
    paused_enabled = tsc.paused_enabled(cfg)
    epics_enabled = bool(tsc.get(cfg, "tasks", "epics", "enabled", default=True))
    releases_enabled = bool(tsc.get(cfg, "tasks", "releases", "enabled", default=True))
    kanban_enabled = bool(tsc.get(cfg, "visualizations", "kanban", "enabled", default=True))

    tasks_dir = Path(tsc.get(cfg, "tasks", "base_folder", default="docs/developers/tasks"))
    ideas_dir = Path(tsc.get(cfg, "ideas", "base_folder", default="docs/developers/ideas"))

    created: list[Path] = []
    skipped: list[Path] = []

    def ensure_dir(p: Path) -> None:
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(p)

    def ensure_file(p: Path, content: str) -> None:
        if p.exists():
            skipped.append(p)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            created.append(p)

    if tasks_enabled:
        ensure_dir(tasks_dir / "open")
        ensure_dir(tasks_dir / "closed")
        if active_enabled:
            ensure_dir(tasks_dir / "active")
        if paused_enabled:
            ensure_dir(tasks_dir / "paused")
        if releases_enabled:
            ensure_dir(tasks_dir / "archive")
        ensure_file(
            tasks_dir / "OVERVIEW.md",
            "# Tasks Overview\n\n<!-- GENERATED -->\n<!-- END GENERATED -->\n",
        )
        if epics_enabled:
            ensure_file(tasks_dir / "EPICS.md", STUB_CONTENT["EPICS.md"])
        if kanban_enabled:
            ensure_file(tasks_dir / "KANBAN.md", STUB_CONTENT["KANBAN.md"])

    if ideas_enabled:
        ensure_dir(ideas_dir / "open")
        ensure_dir(ideas_dir / "archived")
        ensure_file(
            ideas_dir / "OVERVIEW.md",
            "# Ideas Overview\n\n_No open ideas._\n",
        )

    for p in created:
        print(f"housekeep --init: CREATED {p}")
    for p in skipped:
        print(f"housekeep --init: SKIPPED {p} (already exists)")
    if not created:
        print("housekeep --init: nothing to create — structure already present.")
    return 0


def _epic_order_field(item: dict) -> str | None:
    """Return the raw `order:` field value, or None if missing/blank/`?`."""
    raw = item.get("order")
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s == "?":
        return None
    return s


def validate_order_fields(tasks: list[dict]) -> list[str]:
    """Return a list of human-readable failure messages for `order:` violations.

    Rules (per epic):
      - every task with `epic:` set must have a non-blank, non-`?` `order:`
      - `order:` values must be unique within the epic
      - `order:` values must be integers (rendering relies on numeric sort)

    Returns an empty list when the corpus is clean.
    """
    by_epic: dict[str, list[dict]] = {}
    for t in tasks:
        epic = t.get("epic")
        if not epic:
            continue
        by_epic.setdefault(str(epic).strip(), []).append(t)

    failures: list[str] = []
    for epic, members in sorted(by_epic.items()):
        seen: dict[int, list[str]] = {}
        for t in members:
            tid = str(t.get("id", "<unknown>"))
            raw = _epic_order_field(t)
            if raw is None:
                failures.append(
                    f"epic '{epic}': task {tid} has missing/blank/'?' order:"
                )
                continue
            try:
                n = int(raw)
            except ValueError:
                failures.append(
                    f"epic '{epic}': task {tid} has non-integer order: '{raw}'"
                )
                continue
            seen.setdefault(n, []).append(tid)
        for n, owners in sorted(seen.items()):
            if len(owners) > 1:
                failures.append(
                    f"epic '{epic}': order:{n} is duplicated across "
                    f"{', '.join(sorted(owners))}"
                )
    return failures


def _rewrite_order_field(path: Path, new_value: int) -> None:
    """Rewrite the `order:` field in the frontmatter of `path` to `new_value`.

    If `order:` is absent, insert it immediately after `epic:` (or at the end
    of the frontmatter block if `epic:` is also absent — caller should not do
    this case because the validator demands `epic:` first).
    """
    content = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(content)
    if not m:
        return
    fm = m.group(1)
    if re.search(r"^order:\s*.*$", fm, re.MULTILINE):
        new_fm = re.sub(
            r"^order:\s*.*$", f"order: {new_value}", fm, count=1, flags=re.MULTILINE
        )
    elif re.search(r"^epic:\s*.*$", fm, re.MULTILINE):
        new_fm = re.sub(
            r"^(epic:\s*.*)$", rf"\1\norder: {new_value}", fm, count=1,
            flags=re.MULTILINE,
        )
    else:
        new_fm = fm.rstrip() + f"\norder: {new_value}"
    path.write_text(content[:m.start(1)] + new_fm + content[m.end(1):],
                    encoding="utf-8")


def fix_order_fields(tasks: list[dict]) -> list[tuple[Path, int]]:
    """Renumber `order:` contiguously from 1 within each epic.

    Sort key: existing `order:` if present and integer (else +inf), then by
    file path for determinism. Returns the list of (path, new_order) pairs
    that were rewritten.
    """
    by_epic: dict[str, list[dict]] = {}
    for t in tasks:
        epic = t.get("epic")
        if not epic:
            continue
        by_epic.setdefault(str(epic).strip(), []).append(t)

    changes: list[tuple[Path, int]] = []
    for epic, members in sorted(by_epic.items()):
        def _sort_key(t: dict) -> tuple[int, str]:
            raw = _epic_order_field(t)
            try:
                n = int(raw) if raw is not None else 10**9
            except ValueError:
                n = 10**9
            return (n, str(t.get("_path", "")))

        ordered = sorted(members, key=_sort_key)
        for new_n, t in enumerate(ordered, start=1):
            raw = _epic_order_field(t)
            current = None
            try:
                current = int(raw) if raw is not None else None
            except ValueError:
                current = None
            if current == new_n:
                continue
            path = t.get("_path")
            if not isinstance(path, Path):
                continue
            _rewrite_order_field(path, new_n)
            changes.append((path, new_n))
    return changes


def _read_version() -> str:
    """Return version from VERSION file next to this script, or 'unknown'."""
    for candidate in (
        Path(__file__).resolve().parent / "VERSION",
        Path(__file__).resolve().parent.parent / "awesome-task-system" / "VERSION",
    ):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan task/epic files, move them to match status,"
                    " and regenerate overviews."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Execute the plan (default is dry-run).")
    parser.add_argument("--init", action="store_true",
                        help="Create folder structure and stub files for a"
                             " fresh repo (idempotent).")
    parser.add_argument("--version", action="store_true",
                        help="Print version and exit.")
    parser.add_argument("--fix-order", action="store_true",
                        help="Renumber `order:` contiguously from 1 within "
                             "each epic, then exit. Writes to disk; no other "
                             "housekeep actions are taken.")
    args = parser.parse_args(argv)

    if args.version:
        print(f"housekeep {_read_version()}")
        return 0

    if args.init:
        with acquire_lock():
            return run_init(_CFG)

    if args.fix_order:
        with acquire_lock():
            tasks = scan_task_items_only(scan_tasks())
            changes = fix_order_fields(tasks)
            if not changes:
                print("housekeep --fix-order: order: fields already contiguous.")
            else:
                for path, n in changes:
                    print(f"housekeep --fix-order: {path} -> order: {n}")
                print(f"housekeep --fix-order: rewrote {len(changes)} file(s).")
            return 0

    if _EPICS_ENABLED:
        tasks_for_validation = scan_task_items_only(scan_tasks())
        order_failures = validate_order_fields(tasks_for_validation)
        if order_failures:
            print("housekeep: order: validation failed.", file=sys.stderr)
            for msg in order_failures:
                print(f"  {msg}", file=sys.stderr)
            print("\nFix: edit the offending tasks, or run "
                  "`python scripts/housekeep.py --fix-order` to renumber "
                  "contiguously per epic.", file=sys.stderr)
            return 1

    if args.apply:
        with acquire_lock():
            plan = build_plan(epics_enabled=_EPICS_ENABLED)
            print_plan(plan)
            apply_plan(plan)
            print("housekeep: applied.")
    else:
        plan = build_plan(epics_enabled=_EPICS_ENABLED)
        print_plan(plan)
        print("housekeep: dry-run — pass --apply to execute.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
