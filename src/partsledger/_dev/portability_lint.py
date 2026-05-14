"""Portability lint for ``src/partsledger/``.

Enforces the portability contract from ADR-0001 (library as
installable package): files inside the package must be free of
host-project coupling so the published wheel works in any consumer
repo.

Forbidden inside ``src/partsledger/``:

- ``from scripts.<...>`` / ``import scripts.<...>`` — `scripts/` is
  host-side, not packaged.
- ``from .claude.<...>`` — `.claude/` configuration is project-local.
- Relative paths that escape the package
  (``Path(__file__).parent.parent.parent`` and similar).
- Hard-coded references to repo-root paths (``inventory/``,
  ``docs/``) outside of strings that flow through a configurable
  interface (currently surfaced as findings; legitimate paths must
  be opted-in via ``.portability-allow.txt``).
- The sibling project name ``CircuitSmith`` outside a docs path —
  CircuitSmith is the sibling toolchain; references in code are
  almost always a leak.

Usage::

    python scripts/portability_lint.py <package_dir>

Exit 0 if clean. Exit 1 with a list of findings if not. An empty or
missing ``<package_dir>`` is a no-op (exit 0) — the lint is meant to
be in place before package code arrives, not after.

Allow-list (escape hatch for genuine exceptions):
    A file ``.portability-allow.txt`` at the root of ``<package_dir>``
    can carry exceptions, one per line::

        <relative-path>:<pattern-substring>:<reason>

    The reason is free text and makes the exception auditable. Lines
    starting with ``#`` are comments.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

__all__ = ["PATTERNS", "lint", "main"]


# Files the lint inspects. Binaries and other formats are skipped.
TEXT_EXTENSIONS = {
    ".py", ".md", ".json", ".yml", ".yaml", ".toml", ".txt",
    ".sh", ".bash", ".zsh", ".ts", ".js", ".mjs", ".cjs",
}


# Pattern table. Each entry: (regex, message, docs_exception)
#
#   - regex: compiled pattern searched per-line.
#   - message: human-readable description embedded in findings.
#   - docs_exception: when True, skip matches in files whose relative
#     path under the linted root starts with ``docs/`` — used for
#     sibling-project names that are fine to mention in narrative docs
#     but not in code.
PATTERNS: list[tuple[re.Pattern[str], str, bool]] = [
    (re.compile(r"/home/[a-zA-Z0-9_-]+"),
     "absolute path (Linux/macOS home)", False),
    (re.compile(r"\bC:\\\\[^\s\"']+"),
     "absolute path (Windows)", False),
    (re.compile(r"~/Dokumente"),
     "user-home path", False),
    (re.compile(r"^\s*from\s+scripts\."),
     "import of project-side `scripts.` module", False),
    (re.compile(r"\bimport\s+scripts\."),
     "import of project-side `scripts.` module", False),
    (re.compile(r"^\s*from\s+\.claude\."),
     "import from project-side `.claude/` tree", False),
    (re.compile(r"(?<![a-zA-Z0-9_/-])inventory/[a-zA-Z]"),
     "hard-coded repo path `inventory/...`", False),
    (re.compile(r"(?<![a-zA-Z0-9_/-])docs/[a-zA-Z]"),
     "hard-coded repo path `docs/...`", False),
    (re.compile(r"\.parent\.parent\.parent"),
     "escape-out-of-package path traversal", False),
    (re.compile(r"\bCircuitSmith\b"),
     "sibling project name `CircuitSmith` (allowed under docs/)", True),
    (re.compile(r"\bAwesomeStudioPedal\b"),
     "sibling project name `AwesomeStudioPedal` (allowed under docs/)", True),
]


def load_allow(allow_file: Path) -> list[tuple[str, str]]:
    """Read the allow-list file and return ``[(rel_path, pattern_sub), ...]``.

    Missing files yield an empty list; malformed lines are skipped.
    """

    if not allow_file.exists():
        return []
    out: list[tuple[str, str]] = []
    for raw in allow_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 2)
        if len(parts) < 2:
            continue
        rel_path = parts[0].strip()
        pattern_sub = parts[1].strip()
        if rel_path and pattern_sub:
            out.append((rel_path, pattern_sub))
    return out


def is_allowed(rel_path: str, finding: str,
               allow: list[tuple[str, str]]) -> bool:
    return any(ap == rel_path and sub in finding for ap, sub in allow)


def walk_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield p


def lint(root: Path) -> list[str]:
    if not root.exists() or not root.is_dir():
        return []
    allow = load_allow(root / ".portability-allow.txt")
    findings: list[str] = []
    for path in walk_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rx, msg, docs_exception in PATTERNS:
                if docs_exception and rel.startswith("docs/"):
                    continue
                if rx.search(line):
                    finding = f"{rel}:{lineno}: {msg}"
                    if not is_allowed(rel, finding, allow):
                        findings.append(finding)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Lint a package directory for PartsLedger portability "
            "contract violations."
        ),
    )
    parser.add_argument(
        "package_dir",
        help=(
            "path to the package directory to lint "
            "(e.g. src/partsledger)"
        ),
    )
    args = parser.parse_args(argv)
    root = Path(args.package_dir).resolve()
    findings = lint(root)
    if findings:
        sys.stderr.write(
            f"portability-lint: {len(findings)} finding(s) in {root}:\n"
        )
        for f in findings:
            sys.stderr.write(f"  {f}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
