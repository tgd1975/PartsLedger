"""Hedge-language lint for ``inventory/parts/*.md``.

IDEA-005 § Stage 1 — a mechanical backstop for the sincere-language
convention. The convention is enforced today by prompt examples
inside ``/inventory-add`` and ``/inventory-page``; prompt-example
enforcement drifts, lint doesn't.

The lint walks parts pages and flags **absolute-claim phrasing** that
should be hedged. Scope is parts pages only — ``INVENTORY.md`` is
deliberately exempt (its Notes cells are short and frequently quote
datasheet language verbatim, where a table-cell lint would generate
mostly noise).

Patterns flagged (per task body):

- ``is the`` — bare identity claim. The convention prefers
  ``appears to be``, ``looks like the``, or a qualifying lead.
- ``must`` — modal absolute. Prefer ``should`` / ``needs to`` when
  the claim is engineering advice rather than datasheet-derived.
- ``always`` / ``never`` — temporal absolute. Prefer ``typically``
  / ``rarely`` when the claim is observational.

Exempt contexts (no diagnostic fires):

- Fenced code blocks (``` ``` … ``` ```), regardless of language.
- Block quotes (lines starting with ``>``) — quoted datasheet
  excerpts.
- HTML comments (``<!-- … -->``) inline.
- A line carrying ``<!-- lint: ok -->`` — per-line override for
  genuinely-true absolute claims (industry-standard pinouts,
  hard datasheet facts).

See ADR-0002 for the pattern-set rationale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Diagnostic",
    "lint_text",
    "lint_path",
    "lint_paths",
]


PATTERNS: dict[str, re.Pattern[str]] = {
    "is-the": re.compile(r"\bis\s+the\b", re.IGNORECASE),
    "must": re.compile(r"\bmust\b", re.IGNORECASE),
    "always": re.compile(r"\balways\b", re.IGNORECASE),
    "never": re.compile(r"\bnever\b", re.IGNORECASE),
}

SUPPRESS_MARKER = "<!-- lint: ok -->"
FENCE_RE = re.compile(r"^\s*```")
COMMENT_BLOCK_RE = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass(frozen=True)
class Diagnostic:
    """One lint diagnostic. ``line`` is 1-indexed."""

    path: Path
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] {self.message}"


def _strip_inline_comments(line: str) -> str:
    return COMMENT_BLOCK_RE.sub("", line)


def lint_text(text: str, *, path: Path | None = None) -> list[Diagnostic]:
    """Return diagnostics for ``text`` (a single parts page).

    ``path`` is used only to populate :attr:`Diagnostic.path` for
    rendering. Pass ``None`` for in-memory uses.
    """

    diagnostics: list[Diagnostic] = []
    src = path if path is not None else Path("<text>")
    in_fence = False

    for i, raw_line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(raw_line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if raw_line.lstrip().startswith(">"):
            continue
        if SUPPRESS_MARKER in raw_line:
            continue

        scan = _strip_inline_comments(raw_line)
        for rule, pattern in PATTERNS.items():
            if pattern.search(scan):
                diagnostics.append(
                    Diagnostic(
                        path=src,
                        line=i,
                        rule=rule,
                        message=(
                            f"absolute-claim phrasing {rule!r} — hedge "
                            f"(~ / up to / typically) or annotate with "
                            f"'{SUPPRESS_MARKER}' if intentional"
                        ),
                    )
                )

    return diagnostics


def lint_path(path: str | Path) -> list[Diagnostic]:
    """Lint the single parts page at ``path``."""

    p = Path(path)
    return lint_text(p.read_text(encoding="utf-8"), path=p)


def lint_paths(paths: list[str | Path]) -> list[Diagnostic]:
    """Lint every path in ``paths``; return the concatenated diagnostics."""

    out: list[Diagnostic] = []
    for p in paths:
        out.extend(lint_path(p))
    return out
