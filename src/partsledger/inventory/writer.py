"""Single ``INVENTORY.md`` writer shared by three call-sites.

Per IDEA-004 § ``INVENTORY.md`` writer contract — this module is the
**one** place ``inventory/INVENTORY.md`` gets mutated. The three
callers (``/inventory-add`` skill path, camera-path Stage 4, and the
enrichment integrator) all import :func:`upsert_row`.

Contract summary:

- **Idempotent on ``part_id``** — same args twice produces the same
  end state, except ``qty_delta`` accumulates by design.
- **Atomic** — one call, one file write, via the temp-file-plus-
  ``os.replace`` pattern. A crash mid-write leaves the file in
  either the pre- or post-call state.
- **Pre-flush invariant check** — every mutation is run through
  :mod:`partsledger.inventory.lint` before flushing. A lint
  violation raises rather than producing a malformed file.

Errors (see :class:`InventoryWriteError` subclasses):

- ``MalformedPreStateError`` — the existing file does not parse.
- ``SectionUnresolvableError`` — ``section=None`` and no ``## …``
  headings exist, or ``section="Foo"`` but no ``## Foo`` exists.
- ``SourceShapeError`` — ``source`` empty / whitespace / mixed-case.
- ``InventoryLintError`` (re-raised from the lint module) — the
  post-state lint rejected the mutated representation.

The writer does **not** raise on negative final qty, on a section
that is well-defined but absent from the maker's typical bucket
list, or on extra keys in ``cells`` (silently ignored).
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .lint import (
    PARTS_LINK_RE,
    SOURCE_TOKEN_RE,
    InventoryLintError,
    lint_text,
)

__all__ = [
    "Disposition",
    "WriteResult",
    "InventoryWriteError",
    "MalformedPreStateError",
    "SectionUnresolvableError",
    "SourceShapeError",
    "upsert_row",
]


Disposition = Literal["inserted", "bumped", "metadata_updated", "no_op"]


@dataclass(frozen=True)
class WriteResult:
    """Outcome of one :func:`upsert_row` call."""

    disposition: Disposition
    qty: int
    section: str


class InventoryWriteError(Exception):
    """Base for writer-side errors."""


class MalformedPreStateError(InventoryWriteError):
    """``INVENTORY.md`` did not parse as the documented shape."""


class SectionUnresolvableError(InventoryWriteError):
    """``section=None`` with no ``## …`` headings, or ``section="X"`` with no ``## X``."""


class SourceShapeError(InventoryWriteError):
    """``source`` is empty, contains whitespace, or has uppercase."""


# --------------------------------------------------------------------------
# Parsing — line-based representation that round-trips through write
# --------------------------------------------------------------------------


@dataclass
class _Row:
    cells: list[str]


@dataclass
class _Table:
    """One markdown table within a section, with its header / separator / rows."""

    header: list[str]
    rows: list[_Row]

    def col_index(self, name: str) -> int | None:
        try:
            return self.header.index(name)
        except ValueError:
            return None


@dataclass
class _Section:
    name: str  # e.g. "ICs" — text after `## `
    heading_line: str  # the literal `## ICs` line (preserves any trailing decoration)
    body_lines: list[str]  # everything between this heading and the next H2 (or EOF)


def _split_cells(line: str) -> list[str]:
    inner = line.strip().strip("|")
    return [c.strip() for c in inner.split("|")]


def _is_table_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("|") and stripped.rstrip().endswith("|")


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c) and any(cells)


def _format_table(header: list[str], rows: list[list[str]]) -> str:
    """Format header + rows as a markdownlint-clean aligned table."""

    widths = [len(h) for h in header]
    for row in rows:
        for idx, cell in enumerate(row):
            if idx < len(widths):
                widths[idx] = max(widths[idx], len(cell))
    # Separator must be at least 3 dashes for markdownlint MD060 to be happy.
    widths = [max(w, 3) for w in widths]
    lines = []
    lines.append("| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(header)) + " |")
    lines.append("| " + " | ".join("-" * widths[i] for i in range(len(header))) + " |")
    for row in rows:
        padded = [(row[i] if i < len(row) else "").ljust(widths[i]) for i in range(len(header))]
        lines.append("| " + " | ".join(padded) + " |")
    return "\n".join(lines)


def _parse_sections(text: str) -> tuple[list[str], list[_Section]]:
    """Split the file into preamble + one ``_Section`` per ``## …`` heading."""

    lines = text.splitlines()
    preamble: list[str] = []
    sections: list[_Section] = []
    current: _Section | None = None
    for line in lines:
        if line.startswith("## "):
            name = line[3:].strip()
            current = _Section(name=name, heading_line=line, body_lines=[])
            sections.append(current)
        elif current is None:
            preamble.append(line)
        else:
            current.body_lines.append(line)
    return preamble, sections


def _find_first_parts_table(section: _Section) -> tuple[int, int, _Table] | None:
    """Locate the first parts table (header has both ``Part`` and ``Source``).

    Returns ``(start_idx, end_idx_exclusive, table)`` indices into
    ``section.body_lines``, or ``None`` if no parts table exists.
    """

    lines = section.body_lines
    i = 0
    while i < len(lines):
        if (
            _is_table_line(lines[i])
            and i + 1 < len(lines)
            and _is_table_line(lines[i + 1])
            and _is_separator_row(_split_cells(lines[i + 1]))
        ):
            header = _split_cells(lines[i])
            if "Part" in header and "Source" in header:
                start = i
                j = i + 2
                rows = []
                while j < len(lines) and _is_table_line(lines[j]):
                    rows.append(_Row(cells=_split_cells(lines[j])))
                    j += 1
                return start, j, _Table(header=header, rows=rows)
            # Non-parts table — skip past it.
            j = i + 2
            while j < len(lines) and _is_table_line(lines[j]):
                j += 1
            i = j
        else:
            i += 1
    return None


def _part_match(cell: str, part_id: str) -> bool:
    """Match the Part cell against a literal part_id (handles ``[X](parts/Y.md)``)."""

    stripped = cell.strip()
    match = PARTS_LINK_RE.match(stripped)
    visible = match.group(1) if match else stripped
    return visible == part_id


def _part_sort_key(cell: str) -> str:
    match = PARTS_LINK_RE.match(cell.strip())
    visible = match.group(1) if match else cell.strip()
    return visible.casefold()


def _validate_source(source: str) -> None:
    if not source:
        raise SourceShapeError("source must be non-empty")
    if source != source.strip():
        raise SourceShapeError(f"source has whitespace: {source!r}")
    if not SOURCE_TOKEN_RE.fullmatch(source):
        raise SourceShapeError(f"source must be a lowercase token (got {source!r})")


def _resolve_inventory_path() -> Path:
    """Resolve ``inventory/INVENTORY.md`` from env or repo-root discovery."""

    env = os.environ.get("PL_INVENTORY_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent / "inventory" / "INVENTORY.md"
    raise InventoryWriteError("could not resolve inventory path — set PL_INVENTORY_PATH")


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def upsert_row(
    part_id: str,
    qty_delta: int,
    *,
    source: str,
    section: str | None = None,
    cells: dict[str, str] | None = None,
) -> WriteResult:
    """Insert or update a row in ``inventory/INVENTORY.md``.

    See module docstring for the contract. The path is resolved via
    the ``PL_INVENTORY_PATH`` env var (when set) or by walking up to
    the repo root.
    """

    return _upsert_row_at(part_id, qty_delta, source=source, section=section, cells=cells, path=_resolve_inventory_path())


def _upsert_row_at(
    part_id: str,
    qty_delta: int,
    *,
    source: str,
    section: str | None,
    cells: dict[str, str] | None,
    path: Path,
) -> WriteResult:
    """Path-aware backend — pulled out for testability."""

    _validate_source(source)

    cells = dict(cells or {})
    cells.setdefault("Part", part_id)

    if not path.is_file():
        raise MalformedPreStateError(f"inventory file does not exist: {path}")
    original_text = path.read_text(encoding="utf-8")
    preamble, sections = _parse_sections(original_text)

    if not sections:
        raise SectionUnresolvableError("INVENTORY.md has no ## headings yet")

    # Locate any existing row for part_id across all sections.
    found_section_idx: int | None = None
    found_table_start: int | None = None
    found_table_end: int | None = None
    found_table: _Table | None = None
    found_row_idx: int | None = None

    for si, sec in enumerate(sections):
        parts_table = _find_first_parts_table(sec)
        if parts_table is None:
            continue
        start, end, table = parts_table
        part_idx = table.col_index("Part")
        if part_idx is None:
            continue
        for ri, row in enumerate(table.rows):
            if part_idx >= len(row.cells):
                continue
            if _part_match(row.cells[part_idx], part_id):
                found_section_idx = si
                found_table_start = start
                found_table_end = end
                found_table = table
                found_row_idx = ri
                break
        if found_section_idx is not None:
            break

    if found_section_idx is not None:
        # Existing row — bump qty / update cells.
        assert found_table is not None
        assert found_row_idx is not None
        assert found_table_start is not None
        assert found_table_end is not None

        # If caller supplied a section that differs from where we found
        # the row, the contract is silent — match other implementations
        # by ignoring the move request and updating the row in place.
        # The caller can implement a move by deleting + re-inserting.
        sec = sections[found_section_idx]
        target_section_name = sec.name

        row = found_table.rows[found_row_idx]
        qty_idx = found_table.col_index("Qty")
        old_qty = 0
        if qty_idx is not None and qty_idx < len(row.cells):
            try:
                old_qty = int(row.cells[qty_idx])
            except ValueError:
                old_qty = 0
        new_qty = old_qty + qty_delta

        # Build the updated row from the existing cells + cells overlay.
        new_cells = list(row.cells)
        # Make sure the row has exactly the header's column count.
        while len(new_cells) < len(found_table.header):
            new_cells.append("")
        new_cells = new_cells[: len(found_table.header)]

        changed_metadata = False
        for col_name, value in cells.items():
            ci = found_table.col_index(col_name)
            if ci is None:
                continue  # silently ignore extra keys
            if col_name == "Part":
                # Don't clobber an existing linked Part cell with the bare ID.
                if not new_cells[ci]:
                    new_cells[ci] = value
                continue
            if new_cells[ci] != value:
                changed_metadata = True
                new_cells[ci] = value

        if qty_idx is not None:
            new_cells[qty_idx] = str(new_qty)

        # Source: respect the caller's value.
        source_idx = found_table.col_index("Source")
        if source_idx is not None:
            if new_cells[source_idx] != source:
                changed_metadata = True
                new_cells[source_idx] = source

        found_table.rows[found_row_idx].cells = new_cells

        if qty_delta != 0:
            disposition: Disposition = "bumped"
        elif changed_metadata:
            disposition = "metadata_updated"
        else:
            disposition = "no_op"
            # No state change — return without writing.
            return WriteResult(disposition="no_op", qty=new_qty, section=target_section_name)

        # Reformat the section's table back into body_lines.
        rendered = _format_table(found_table.header, [r.cells for r in found_table.rows])
        sec.body_lines[found_table_start:found_table_end] = rendered.splitlines()
        result = WriteResult(disposition=disposition, qty=new_qty, section=target_section_name)

    else:
        # No existing row — insert.
        if section is None:
            target_section_idx = 0  # first H2 section
        else:
            target_section_idx = None
            for si, sec in enumerate(sections):
                if sec.name == section:
                    target_section_idx = si
                    break
            if target_section_idx is None:
                raise SectionUnresolvableError(f"no ## {section} section in INVENTORY.md")

        sec = sections[target_section_idx]
        target_section_name = sec.name
        parts_table = _find_first_parts_table(sec)
        if parts_table is None:
            raise SectionUnresolvableError(
                f"section {sec.name!r} has no parts table to insert into"
            )
        start, end, table = parts_table

        # Build the new row from the cells dict, defaulting empty.
        new_row_cells = []
        for col in table.header:
            if col == "Qty":
                new_row_cells.append(str(qty_delta))
            elif col == "Source":
                new_row_cells.append(source)
            elif col == "Part":
                new_row_cells.append(cells.get("Part", part_id))
            else:
                new_row_cells.append(cells.get(col, ""))

        # Drop any all-empty placeholder rows before inserting.
        cleaned_rows = [r for r in table.rows if any(c.strip() for c in r.cells)]
        new_row_obj = _Row(cells=new_row_cells)

        # Insert alphabetically by Part visible text.
        part_idx = table.col_index("Part")
        new_key = _part_sort_key(new_row_cells[part_idx] if part_idx is not None else part_id)
        insert_at = len(cleaned_rows)
        for ri, row in enumerate(cleaned_rows):
            if part_idx is None or part_idx >= len(row.cells):
                continue
            if _part_sort_key(row.cells[part_idx]) > new_key:
                insert_at = ri
                break
        cleaned_rows.insert(insert_at, new_row_obj)
        table.rows = cleaned_rows

        rendered = _format_table(table.header, [r.cells for r in table.rows])
        sec.body_lines[start:end] = rendered.splitlines()
        new_qty = qty_delta
        result = WriteResult(disposition="inserted", qty=new_qty, section=target_section_name)

    # Reassemble the file.
    out_lines: list[str] = list(preamble)
    for sec in sections:
        out_lines.append(sec.heading_line)
        out_lines.extend(sec.body_lines)
    out = "\n".join(out_lines)
    if not out.endswith("\n"):
        out += "\n"

    # Pre-flush lint check.
    diagnostics = lint_text(out, inventory_path=path)
    if diagnostics:
        raise InventoryLintError(diagnostics)

    # Atomic write — temp file in the same directory + os.replace.
    fd, tmp_path = tempfile.mkstemp(
        prefix=".INVENTORY-",
        suffix=".md.tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(out)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return result
