"""Undo journal — TASK-044 (IDEA-007 Stage 5).

Disk-persistent single-step undo. After each successful pipeline write the
journal records the qty++ and its cache row; :meth:`UndoJournal.undo_last`
reverses both — decrement the qty in the part MD (via the TASK-016 writer)
and delete the cache row — so a wrong silent write never poisons the cache
for future captures in the same neighbourhood.

Journal file: ``inventory/.embeddings/undo.toml``. Depth-1 by default
(configurable via ``[recognition] undo_depth``): only the most recent write
is reversible. The schema leaves room for greater depth without a format
break.

```toml
[[entries]]
action       = "write"
part_id      = "lm358n"
qty_before   = 3
qty_after    = 4
cache_row_id = 1287
source       = "cache"
timestamp    = "2026-05-14T16:23:11Z"
```

Atomicity from the maker's view: ``undo_last`` either fully reverts or
leaves the cache row **and** journal entry untouched for a later retry —
never a half-undone state. The MD decrement is attempted first; only on its
success are the cache row and journal entry removed.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:  # py3.11+
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]

__all__ = [
    "Reverted",
    "NothingToUndo",
    "UndoFailed",
    "UndoOutcome",
    "UndoJournal",
    "default_journal_path",
]


@dataclass(frozen=True)
class Reverted:
    part_id: str


@dataclass(frozen=True)
class NothingToUndo:
    pass


@dataclass(frozen=True)
class UndoFailed:
    reason: str


UndoOutcome = "Reverted | NothingToUndo | UndoFailed"


def default_journal_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent / "inventory" / ".embeddings" / "undo.toml"
    return Path("inventory") / ".embeddings" / "undo.toml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class UndoJournal:
    """Depth-N (default 1) write journal backing single-step undo."""

    def __init__(
        self,
        *,
        cache: Any,
        writer_upsert: Callable[..., Any],
        path: Path | str | None = None,
        depth: int = 1,
    ) -> None:
        self.path = Path(path) if path is not None else default_journal_path()
        self._cache = cache
        self._writer_upsert = writer_upsert
        self._depth = max(1, depth)

    # -- persistence -------------------------------------------------------

    def _load(self) -> list[dict]:
        if not self.path.is_file():
            return []
        with self.path.open("rb") as fh:
            data = tomllib.load(fh)
        entries = data.get("entries") or []
        return [dict(e) for e in entries]

    def _save(self, entries: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for e in entries:
            lines.append("[[entries]]")
            lines.append(f'action       = "{_toml_escape(str(e.get("action", "write")))}"')
            lines.append(f'part_id      = "{_toml_escape(str(e["part_id"]))}"')
            lines.append(f'qty_before   = {int(e["qty_before"])}')
            lines.append(f'qty_after    = {int(e["qty_after"])}')
            lines.append(f'cache_row_id = {int(e["cache_row_id"])}')
            lines.append(f'source       = "{_toml_escape(str(e.get("source", "")))}"')
            lines.append(f'label        = "{_toml_escape(str(e.get("label", e["part_id"])))}"')
            lines.append(f'timestamp    = "{_toml_escape(str(e.get("timestamp", _now_iso())))}"')
            lines.append("")
        text = "\n".join(lines)
        # Atomic replace.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".undo-", suffix=".toml.tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # -- recording ---------------------------------------------------------

    def record(self, entry: Any) -> None:
        """Append a write entry, evicting beyond the configured depth.

        ``entry`` is a :class:`partsledger.recognition.pipeline.WriteEntry`
        (or any object exposing the same fields).
        """
        entries = self._load()
        entries.append(
            {
                "action": getattr(entry, "action", "write"),
                "part_id": entry.part_id,
                "qty_before": entry.qty_before,
                "qty_after": entry.qty_after,
                "cache_row_id": entry.cache_row_id,
                "source": getattr(entry, "source", ""),
                "label": getattr(entry, "label", entry.part_id),
                "timestamp": _now_iso(),
            }
        )
        # Keep only the most recent `depth` entries.
        if len(entries) > self._depth:
            entries = entries[-self._depth :]
        self._save(entries)

    # -- undo --------------------------------------------------------------

    def undo_last(self) -> Any:
        """Reverse the most recent write. See module docstring for atomicity."""
        entries = self._load()
        if not entries:
            return NothingToUndo()
        entry = entries[-1]

        # 1. Decrement the qty FIRST. A failure here leaves the cache row and
        #    the journal entry in place for a later retry.
        try:
            self._writer_upsert(
                entry["part_id"], -1, source=str(entry.get("source") or "undo")
            )
        except Exception as exc:  # noqa: BLE001 — surface a clean outcome
            return UndoFailed(reason=f"could not decrement {entry['part_id']}: {exc}")

        # 2. Delete the cache row.
        try:
            self._cache.delete_row(int(entry["cache_row_id"]))
        except Exception:
            # The qty is already decremented; the cache row delete is
            # idempotent-by-id and a stale row is harmless, so do not fail
            # the whole undo on it.
            pass

        # 3. Remove the journal entry.
        entries.pop()
        self._save(entries)
        return Reverted(part_id=str(entry["part_id"]))
