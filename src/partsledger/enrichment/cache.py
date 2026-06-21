"""Per-MPN Nexar response cache — TASK-046 (IDEA-008 Stage 2).

Wraps the Nexar transport so repeat enrichment of the same part is instant
and survives process restart. Pure stdlib ``sqlite3``; the cache is
regenerable from MD + live re-fetches, same ethos as the embedding cache.

Schema: ``(mpn TEXT PRIMARY KEY, payload_json TEXT, lifecycle TEXT,
cached_at INTEGER)``. File: ``inventory/.embeddings/nexar_cache.sqlite``.

TTL policy (IDEA-008 *Cache policy*): 30 days for ``Active`` parts; **never**
for ``Obsolete`` / ``NRND`` (their metadata is frozen). :meth:`expire_stale`
is the only deletion path — never bulk-clear.
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

__all__ = ["NexarCache", "default_cache_path", "TTL_SECONDS", "FROZEN_LIFECYCLES"]

TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days

# Lifecycles whose metadata is frozen — cached entries never expire.
FROZEN_LIFECYCLES = frozenset({"obsolete", "nrnd"})


def default_cache_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent / "inventory" / ".embeddings" / "nexar_cache.sqlite"
    return Path("inventory") / ".embeddings" / "nexar_cache.sqlite"


def _is_frozen(lifecycle: str | None) -> bool:
    return bool(lifecycle) and lifecycle.strip().lower() in FROZEN_LIFECYCLES


class NexarCache:
    """SQLite per-MPN response cache with lifecycle-aware TTL."""

    def __init__(self, *, path: Path | str | None = None, connect: Any | None = None) -> None:
        self.path = Path(path) if path is not None else default_cache_path()
        if connect is not None:
            self._conn = connect(str(self.path))
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nexar_cache (
                mpn          TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                lifecycle    TEXT,
                cached_at    INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "NexarCache":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- API ---------------------------------------------------------------

    def put(self, mpn: str, payload: Any, lifecycle: str | None, *, now: float | None = None) -> None:
        """Cache a payload for ``mpn``. ``payload`` may be a dataclass or dict."""
        if dataclasses.is_dataclass(payload) and not isinstance(payload, type):
            payload = dataclasses.asdict(payload)
        stamp = int(now if now is not None else time.time())
        self._conn.execute(
            "INSERT INTO nexar_cache (mpn, payload_json, lifecycle, cached_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(mpn) DO UPDATE SET "
            "payload_json = excluded.payload_json, "
            "lifecycle = excluded.lifecycle, "
            "cached_at = excluded.cached_at",
            (mpn, json.dumps(payload), lifecycle, stamp),
        )
        self._conn.commit()

    def get(self, mpn: str, *, now: float | None = None) -> dict | None:
        """Return the cached payload for ``mpn``, honouring the TTL policy.

        An ``Active`` (non-frozen) row past 30 days returns ``None`` so the
        next caller refetches; frozen rows never expire.
        """
        row = self._conn.execute(
            "SELECT payload_json, lifecycle, cached_at FROM nexar_cache WHERE mpn = ?",
            (mpn,),
        ).fetchone()
        if row is None:
            return None
        if not _is_frozen(row["lifecycle"]):
            stamp = now if now is not None else time.time()
            if stamp - row["cached_at"] > TTL_SECONDS:
                return None
        return json.loads(row["payload_json"])

    def expire_stale(self, *, now: float | None = None) -> int:
        """Delete only non-frozen rows past TTL. Returns the count removed."""
        stamp = int(now if now is not None else time.time())
        cutoff = stamp - TTL_SECONDS
        frozen = ",".join("?" for _ in FROZEN_LIFECYCLES)
        cur = self._conn.execute(
            f"DELETE FROM nexar_cache WHERE cached_at < ? "
            f"AND (lifecycle IS NULL OR LOWER(lifecycle) NOT IN ({frozen}))",
            (cutoff, *FROZEN_LIFECYCLES),
        )
        self._conn.commit()
        return cur.rowcount

    def __len__(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM nexar_cache").fetchone()["c"])
