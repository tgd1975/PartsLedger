"""Schema-invariant lint for ``inventory/INVENTORY.md``.

Two callers, one implementation:

1. ``partsledger.inventory.writer.upsert_row()`` calls
   :func:`lint_text` before atomic-rename, raising
   :class:`InventoryLintError` on diagnostics so the writer never
   produces a malformed file.
2. ``scripts/lint_inventory.py`` runs as a pre-commit shim and exits
   non-zero on diagnostics.

Invariants enforced (per IDEA-004 § Open questions to hone):

- Source-column shape — non-empty lowercase token, no allow-list.
- Alphabetical row order within each parts table.
- Hedge language in Notes for camera-path doubt one-liners.
- Link-into-``parts/`` correctness — when a Part cell carries a
  Markdown link to ``parts/<name>.md``, that file must exist.

The lint deliberately does **not** enforce markdown table padding
(MD060) — that is markdownlint-cli2's job, called separately in the
pre-commit hook.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "Diagnostic",
    "InventoryLintError",
    "lint_text",
    "lint_path",
]


SOURCE_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
PARTS_LINK_RE = re.compile(r"\[([^\]]+)\]\(parts/([^)]+\.md)\)")

# Hedge phrases that satisfy the camera-path doubt requirement. The
# list is intentionally broad — any of these phrases in the Notes
# cell is enough for the lint to accept a camera-sourced row.
HEDGE_PHRASES = (
    "likely",
    "appears",
    "probably",
    "maybe",
    "possibly",
    "uncertain",
    "tentative",
    "to confirm",
    "best guess",
    "approximately",
    "~",
    "?",
    "guess",
    "generic",
    "marking variant",
    "equiv",
)


@dataclass(frozen=True)
class Diagnostic:
    """One lint diagnostic. ``line`` is 1-indexed into the source text."""

    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"INVENTORY.md:{self.line}: [{self.rule}] {self.message}"


class InventoryLintError(Exception):
    """Raised by the writer's pre-flush check when the lint rejects a mutation."""

    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = list(diagnostics)
        body = "\n".join(str(d) for d in diagnostics)
        super().__init__(f"inventory lint rejected {len(diagnostics)} issue(s):\n{body}")


@dataclass
class _Row:
    line: int
    cells: list[str]


@dataclass
class _Table:
    start_line: int
    header: list[str]
    rows: list[_Row] = field(default_factory=list)

    @property
    def col_index(self) -> dict[str, int]:
        return {name: i for i, name in enumerate(self.header)}

    def is_parts_table(self) -> bool:
        idx = self.col_index
        return "Part" in idx and "Source" in idx


def _split_cells(line: str) -> list[str]:
    inner = line.strip().strip("|")
    return [c.strip() for c in inner.split("|")]


def _is_table_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("|") and stripped.rstrip().endswith("|")


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c) and any(cells)


def _parse_tables(text: str) -> list[_Table]:
    tables: list[_Table] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if (
            _is_table_line(lines[i])
            and i + 1 < len(lines)
            and _is_table_line(lines[i + 1])
            and _is_separator_row(_split_cells(lines[i + 1]))
        ):
            header = _split_cells(lines[i])
            t = _Table(start_line=i + 1, header=header)
            j = i + 2
            while j < len(lines) and _is_table_line(lines[j]):
                t.rows.append(_Row(line=j + 1, cells=_split_cells(lines[j])))
                j += 1
            tables.append(t)
            i = j
        else:
            i += 1
    return tables


def _part_sort_key(part_cell: str) -> str:
    """Sort key for the Part column.

    For a linked cell ``[7660S](parts/7660s.md)`` the key is the
    visible text (``7660S``). For a plain cell, the cell text itself.
    Comparison is case-insensitive so ``KF 470`` and ``KT 209`` sort
    consistently regardless of letter case.
    """

    match = PARTS_LINK_RE.match(part_cell.strip())
    visible = match.group(1) if match else part_cell.strip()
    return visible.casefold()


def _row_is_empty(row: _Row) -> bool:
    """Empty placeholder rows (all-blank data cells) are tolerated."""

    return all(cell == "" for cell in row.cells)


def _check_source_column(table: _Table, diagnostics: list[Diagnostic]) -> None:
    idx = table.col_index["Source"]
    for row in table.rows:
        if _row_is_empty(row):
            continue
        if idx >= len(row.cells):
            diagnostics.append(
                Diagnostic(row.line, "source-shape", "row is missing the Source cell")
            )
            continue
        value = row.cells[idx]
        if not value:
            diagnostics.append(
                Diagnostic(row.line, "source-shape", "Source cell is empty")
            )
        elif value != value.strip():
            diagnostics.append(
                Diagnostic(
                    row.line,
                    "source-shape",
                    f"Source cell has leading or trailing whitespace: {value!r}",
                )
            )
        elif not SOURCE_TOKEN_RE.fullmatch(value):
            diagnostics.append(
                Diagnostic(
                    row.line,
                    "source-shape",
                    f"Source must be a lowercase token (got {value!r})",
                )
            )


def _check_alphabetical(table: _Table, diagnostics: list[Diagnostic]) -> None:
    idx = table.col_index["Part"]
    prev_key: str | None = None
    prev_line: int | None = None
    for row in table.rows:
        if _row_is_empty(row) or idx >= len(row.cells):
            continue
        part_cell = row.cells[idx]
        if not part_cell:
            continue
        key = _part_sort_key(part_cell)
        if prev_key is not None and key < prev_key:
            diagnostics.append(
                Diagnostic(
                    row.line,
                    "alphabetical-order",
                    (
                        f"Part {part_cell!r} should sort before the previous "
                        f"row at line {prev_line}"
                    ),
                )
            )
        prev_key = key
        prev_line = row.line


def _check_hedge_in_notes(table: _Table, diagnostics: list[Diagnostic]) -> None:
    idx = table.col_index
    if "Notes" not in idx or "Source" not in idx:
        return
    notes_i = idx["Notes"]
    source_i = idx["Source"]
    for row in table.rows:
        if _row_is_empty(row):
            continue
        if source_i >= len(row.cells) or notes_i >= len(row.cells):
            continue
        source = row.cells[source_i]
        notes = row.cells[notes_i].strip()
        if source != "camera" or not notes:
            continue
        notes_l = notes.casefold()
        if not any(phrase in notes_l for phrase in HEDGE_PHRASES):
            diagnostics.append(
                Diagnostic(
                    row.line,
                    "hedge-language",
                    (
                        "camera-sourced row has a non-empty Notes cell with no "
                        "hedge phrase — IDEA-005 requires hedged language on "
                        "doubt one-liners"
                    ),
                )
            )


def _check_parts_link(
    table: _Table,
    diagnostics: list[Diagnostic],
    inventory_path: Path | None,
) -> None:
    if inventory_path is None:
        return
    idx = table.col_index["Part"]
    parts_dir = inventory_path.parent / "parts"
    for row in table.rows:
        if _row_is_empty(row) or idx >= len(row.cells):
            continue
        match = PARTS_LINK_RE.search(row.cells[idx])
        if not match:
            continue
        relpath = match.group(2)
        target = parts_dir / relpath
        if not target.is_file():
            diagnostics.append(
                Diagnostic(
                    row.line,
                    "parts-link",
                    f"link target does not exist: {target}",
                )
            )


def lint_text(
    text: str,
    *,
    inventory_path: Path | None = None,
) -> list[Diagnostic]:
    """Return diagnostics for the given ``INVENTORY.md`` text.

    ``inventory_path`` enables the parts-link check by giving the
    location of the file on disk (so ``parts/<name>.md`` links can
    be resolved). Pass ``None`` (the default) to skip that check,
    e.g. for an in-memory writer mutation that has not been
    flushed yet.
    """

    diagnostics: list[Diagnostic] = []
    for table in _parse_tables(text):
        if not table.is_parts_table():
            continue
        _check_source_column(table, diagnostics)
        _check_alphabetical(table, diagnostics)
        _check_hedge_in_notes(table, diagnostics)
        _check_parts_link(table, diagnostics, inventory_path)
    return diagnostics


def lint_path(path: str | Path) -> list[Diagnostic]:
    """Lint the file at ``path``. Convenience wrapper around :func:`lint_text`."""

    p = Path(path)
    return lint_text(p.read_text(encoding="utf-8"), inventory_path=p)
