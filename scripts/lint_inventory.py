"""Pre-commit shim for ``partsledger.inventory.lint``.

Reads ``inventory/INVENTORY.md`` (or a path passed on the command
line) and exits non-zero when the schema-invariant lint reports
diagnostics.

Usage::

    python scripts/lint_inventory.py [PATH ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.inventory.lint import lint_path  # noqa: E402


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]] or [REPO_ROOT / "inventory" / "INVENTORY.md"]
    total = 0
    for p in paths:
        if not p.exists():
            print(f"lint_inventory: missing {p}", file=sys.stderr)
            return 2
        diagnostics = lint_path(p)
        for d in diagnostics:
            print(d, file=sys.stderr)
        total += len(diagnostics)
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
