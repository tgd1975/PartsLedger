"""Pre-commit shim for ``partsledger.inventory.hedge_lint``.

Walks ``inventory/parts/*.md`` (or the paths passed on the command
line) and exits non-zero when the lint reports diagnostics.

Usage::

    python scripts/lint_hedge_language.py [PATH ...]

With no arguments, lints every file matching
``inventory/parts/*.md`` under the repo root.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.inventory.hedge_lint import lint_path  # noqa: E402


def main(argv: list[str]) -> int:
    if argv[1:]:
        paths = [Path(a) for a in argv[1:]]
    else:
        paths = sorted((REPO_ROOT / "inventory" / "parts").glob("*.md"))

    total = 0
    for p in paths:
        if not p.exists():
            print(f"lint_hedge_language: missing {p}", file=sys.stderr)
            return 2
        diagnostics = lint_path(p)
        for d in diagnostics:
            print(d, file=sys.stderr)
        total += len(diagnostics)
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
