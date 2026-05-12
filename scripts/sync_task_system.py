#!/usr/bin/env python3
"""Sync the task-system source-of-truth from awesome-task-system/ to live copies.

The package directory `awesome-task-system/` is the canonical source for the
task-system scripts, skills, config, and tests. This script copies those files
into their live locations under `scripts/`, `.claude/skills/`, and
`docs/developers/task-system.yaml`.

Sync direction is one-way: package → live. Editing the live copy and
forgetting to sync back is exactly the failure mode the divergence guard
in `scripts/pre-commit` catches at commit time.

Usage:
    python scripts/sync_task_system.py            # dry-run; prints what would change
    python scripts/sync_task_system.py --apply    # actually copy files
    python scripts/sync_task_system.py --check    # exit 1 if any pair diverges
    python scripts/sync_task_system.py --apply --force  # overwrite live even if dirty

Exit codes:
    0  in sync, or sync applied
    1  divergence found (--check) or refused to clobber dirty live (--apply)
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PKG = REPO_ROOT / "awesome-task-system"

# Mirror set: list of (package_path, live_path) pairs, all relative to REPO_ROOT.
# Every pair listed here is enforced byte-identical by the pre-commit divergence
# guard. Add new mirrored files to this list when they are introduced.
MIRRORS: list[tuple[str, str]] = [
    # --- scripts ---
    ("awesome-task-system/scripts/housekeep.py",
     "scripts/housekeep.py"),
    ("awesome-task-system/scripts/task_system_config.py",
     "scripts/task_system_config.py"),
    ("awesome-task-system/scripts/update_idea_overview.py",
     "scripts/update_idea_overview.py"),
    ("awesome-task-system/scripts/update_task_overview.py",
     "scripts/update_task_overview.py"),
    ("awesome-task-system/scripts/sync_task_system.py",
     "scripts/sync_task_system.py"),
    ("awesome-task-system/scripts/release_burnup.py",
     "scripts/release_burnup.py"),
    ("awesome-task-system/scripts/release_snapshot.py",
     "scripts/release_snapshot.py"),

    # --- script tests ---
    ("awesome-task-system/scripts/tests/test_release_burnup.py",
     "scripts/tests/test_release_burnup.py"),
    ("awesome-task-system/scripts/tests/test_release_snapshot.py",
     "scripts/tests/test_release_snapshot.py"),
    ("awesome-task-system/scripts/tests/test_housekeep.py",
     "scripts/tests/test_housekeep.py"),
    ("awesome-task-system/scripts/tests/test_housekeep_concurrency.py",
     "scripts/tests/test_housekeep_concurrency.py"),
    ("awesome-task-system/scripts/tests/test_task_system_config.py",
     "scripts/tests/test_task_system_config.py"),
    ("awesome-task-system/scripts/tests/test_update_idea_overview.py",
     "scripts/tests/test_update_idea_overview.py"),

    # --- config ---
    ("awesome-task-system/config/task-system.yaml",
     "docs/developers/task-system.yaml"),

    # --- skills ---
    ("awesome-task-system/skills/tasks/SKILL.md",
     ".claude/skills/tasks/SKILL.md"),
    ("awesome-task-system/skills/ts-epic-list/SKILL.md",
     ".claude/skills/ts-epic-list/SKILL.md"),
    ("awesome-task-system/skills/ts-epic-new/SKILL.md",
     ".claude/skills/ts-epic-new/SKILL.md"),
    ("awesome-task-system/skills/ts-idea-archive/SKILL.md",
     ".claude/skills/ts-idea-archive/SKILL.md"),
    ("awesome-task-system/skills/ts-idea-list/SKILL.md",
     ".claude/skills/ts-idea-list/SKILL.md"),
    ("awesome-task-system/skills/ts-idea-new/SKILL.md",
     ".claude/skills/ts-idea-new/SKILL.md"),
    ("awesome-task-system/skills/ts-task-active/SKILL.md",
     ".claude/skills/ts-task-active/SKILL.md"),
    ("awesome-task-system/skills/ts-task-done/SKILL.md",
     ".claude/skills/ts-task-done/SKILL.md"),
    ("awesome-task-system/skills/ts-task-list/SKILL.md",
     ".claude/skills/ts-task-list/SKILL.md"),
    ("awesome-task-system/skills/ts-task-new/SKILL.md",
     ".claude/skills/ts-task-new/SKILL.md"),
    ("awesome-task-system/skills/ts-task-pause/SKILL.md",
     ".claude/skills/ts-task-pause/SKILL.md"),
    ("awesome-task-system/skills/ts-task-reopen/SKILL.md",
     ".claude/skills/ts-task-reopen/SKILL.md"),
]


def _is_dirty_in_git(path: Path) -> bool:
    """Return True if the live file has uncommitted modifications.

    Any tracked-and-modified, staged-but-unmatching, or untracked state counts
    as dirty. Used to refuse clobbering an in-flight live edit unless --force.
    """
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", str(rel)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    return bool(result.stdout.strip())


def find_divergences() -> list[tuple[Path, Path, str]]:
    """Return list of (pkg, live, reason) for every diverged pair.

    Reasons: 'pkg-missing', 'live-missing', 'differ'.
    """
    out: list[tuple[Path, Path, str]] = []
    for pkg_rel, live_rel in MIRRORS:
        pkg = REPO_ROOT / pkg_rel
        live = REPO_ROOT / live_rel
        if not pkg.exists():
            out.append((pkg, live, "pkg-missing"))
            continue
        if not live.exists():
            out.append((pkg, live, "live-missing"))
            continue
        if not filecmp.cmp(pkg, live, shallow=False):
            out.append((pkg, live, "differ"))
    return out


def cmd_check() -> int:
    div = find_divergences()
    if not div:
        print("sync_task_system: in sync.")
        return 0
    print("sync_task_system: divergence detected:", file=sys.stderr)
    for pkg, live, reason in div:
        rel_pkg = pkg.relative_to(REPO_ROOT)
        rel_live = live.relative_to(REPO_ROOT)
        if reason == "pkg-missing":
            print(f"  MISSING in package: {rel_pkg}", file=sys.stderr)
        elif reason == "live-missing":
            print(f"  MISSING in live:    {rel_live}", file=sys.stderr)
        else:
            print(f"  DIFFER: {rel_pkg}  !=  {rel_live}", file=sys.stderr)
    print("\nFix: edit the package copy, then run "
          "`python scripts/sync_task_system.py --apply`.", file=sys.stderr)
    return 1


def cmd_sync(*, apply: bool, force: bool) -> int:
    div = find_divergences()
    if not div:
        print("sync_task_system: already in sync.")
        return 0

    # Refuse to clobber dirty live copies unless --force.
    dirty_blockers: list[Path] = []
    for pkg, live, reason in div:
        if reason == "live-missing":
            continue
        if _is_dirty_in_git(live):
            dirty_blockers.append(live)
    if dirty_blockers and not force:
        print("sync_task_system: refusing to overwrite dirty live copies "
              "(pass --force to override):", file=sys.stderr)
        for p in dirty_blockers:
            print(f"  DIRTY: {p.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1

    for pkg, live, reason in div:
        if reason == "pkg-missing":
            print(f"  SKIP (pkg-missing): {pkg.relative_to(REPO_ROOT)}",
                  file=sys.stderr)
            continue
        rel_pkg = pkg.relative_to(REPO_ROOT)
        rel_live = live.relative_to(REPO_ROOT)
        if apply:
            live.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pkg, live)
            print(f"  COPIED: {rel_pkg} -> {rel_live}")
        else:
            print(f"  WOULD COPY: {rel_pkg} -> {rel_live}")

    if apply:
        print("sync_task_system: applied.")
    else:
        print("sync_task_system: dry-run — pass --apply to copy.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync awesome-task-system/ (source of truth) to live copies."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually copy files (default is dry-run).")
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if any pair diverges. "
                             "Used by pre-commit.")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite live copies even if they have "
                             "uncommitted modifications.")
    args = parser.parse_args(argv)

    if args.check:
        if args.apply or args.force:
            print("sync_task_system: --check is exclusive with --apply/--force.",
                  file=sys.stderr)
            return 2
        return cmd_check()

    return cmd_sync(apply=args.apply, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
