"""MPN family-sibling heuristic — IDEA-005 § Stage 2.

Two skills use this:

- ``/inventory-add <new-mpn> <qty>`` calls :func:`find_siblings` after
  locating the destination section. If the function returns a
  non-empty list, the skill offers the family-page pattern (mark
  both rows' Notes with *"Shares page with …"* and generate / defer
  a family page).
- ``/inventory-page <mpn>`` calls :func:`find_sibling_pages` before
  generating a fresh page. If a sibling page exists, the skill
  proposes joining it instead of creating a new file.

Both helpers are mechanical. The decision to merge belongs to the
maker; the heuristic only surfaces the candidate set.

Heuristic (per IDEA-005 § Stage 2):

1. **Length gate.** The common prefix is at least 4 alphanumeric
   characters. Drops ``LM358`` vs ``LM2904`` (prefix ``LM``, 2
   chars) and ``LM358N`` vs ``LM386N`` (prefix ``LM3``, 3 chars).
2. **Suffix-only divergence.** Once the common prefix is stripped,
   each remainder is either empty or a pure package/grade suffix:
   a single letter, optionally followed by a digit and optionally
   by a trailing letter. A bare digit is not a suffix — drops
   ``LM358`` vs ``LM3580`` (remainder ``0`` is part of a different
   stem, not a suffix).

Both conditions must hold. IDEA-004's family-boundary worked
examples are the ground truth — if the regex disagrees with them,
the examples win. Conservative beats generous.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = [
    "family_sibling",
    "find_siblings",
    "find_sibling_pages",
]


_SUFFIX_RE = re.compile(r"^[A-Z]\d?[A-Z]?$")
_MIN_PREFIX = 4


def _suffix_ok(s: str) -> bool:
    return s == "" or bool(_SUFFIX_RE.match(s))


def _common_alnum_prefix(a: str, b: str) -> str:
    out: list[str] = []
    for ca, cb in zip(a, b):
        if ca == cb and ca.isalnum():
            out.append(ca)
        else:
            break
    return "".join(out)


def family_sibling(a: str, b: str) -> bool:
    """Return True iff ``a`` and ``b`` are MPN family siblings.

    Comparison is case-insensitive; exact-equal MPNs return False
    (the same part is not a sibling of itself).
    """

    if not a or not b:
        return False
    au, bu = a.upper(), b.upper()
    if au == bu:
        return False
    common = _common_alnum_prefix(au, bu)
    if len(common) < _MIN_PREFIX:
        return False
    return _suffix_ok(au[len(common):]) and _suffix_ok(bu[len(common):])


def find_siblings(new_mpn: str, existing_mpns: list[str]) -> list[str]:
    """Return the subset of ``existing_mpns`` that are siblings of ``new_mpn``.

    Order is preserved from the input list so the caller can render
    a deterministic suggestion.
    """

    return [m for m in existing_mpns if family_sibling(new_mpn, m)]


def find_sibling_pages(new_mpn: str, parts_dir: str | Path) -> list[Path]:
    """Return the parts/<*.md> files whose stems are siblings of ``new_mpn``.

    Used by ``/inventory-page`` to propose family-joins. The match is
    against the file stem (uppercased), so ``parts/lm358n.md`` is a
    candidate for ``LM358P``.
    """

    parts_path = Path(parts_dir)
    if not parts_path.is_dir():
        return []
    return sorted(
        p for p in parts_path.glob("*.md") if family_sibling(new_mpn, p.stem)
    )
