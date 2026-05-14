"""Pre-commit / CI shim for ``partsledger._dev.portability_lint``.

See `src/partsledger/_dev/portability_lint.py` for the contract.

Usage::

    python scripts/portability_lint.py src/partsledger
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger._dev.portability_lint import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
