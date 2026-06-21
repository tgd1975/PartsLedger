"""Embedding cache — TASK-040 (IDEA-007 Stage 1, the *cache* half).

A persistent store for DINOv2 embeddings backing the similarity search at
the heart of the recognition pipeline. Each 768-D L2-normalised vector
(from :func:`partsledger.recognition.embed.embed`) is stored as a
little-endian ``float32`` BLOB in a plain ``sqlite3`` table; nearest-
neighbour search is brute-force cosine distance in numpy.

See ADR-0004 for why this is sqlite3+numpy rather than the ``sqlite-vec``
loadable extension (extension loading is compiled out of many stdlib
``sqlite3`` builds; brute force is correct and sub-millisecond at the
hobbyist < 10k-part scale IDEA-007 targets).

Public surface (:class:`EmbeddingCache`):

- ``insert(vector, label, marking_text, image_hash) -> row_id`` — idempotent
  on ``image_hash``.
- ``nearest(vector, k=3) -> [Neighbour]`` — ascending cosine distance.
- ``delete_last_inserted() -> bool`` — pop the most recent row (undo).
- ``clear_if_hash_mismatch(model_hash)`` — rebuild-on-mismatch gate.

Storage defaults to ``inventory/.embeddings/vectors.sqlite`` (IDEA-004
directory layout); the path is injectable for tests. Concurrency / WAL is
out of scope for the single-bench workflow.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

__all__ = [
    "EMBED_DIM",
    "Neighbour",
    "CacheHashMismatch",
    "EmbeddingCache",
    "default_cache_path",
]

#: Fixed by the ViT-S/14 backbone — see embed.EMBED_DIM. Re-declared here so
#: the cache schema does not import the heavy embed module at open time.
EMBED_DIM = 768

_META_MODEL_HASH = "model_hash"


@dataclass(frozen=True)
class Neighbour:
    """One nearest-neighbour hit from :meth:`EmbeddingCache.nearest`."""

    row_id: int
    label: str
    marking_text: str | None
    distance: float


class CacheHashMismatch(RuntimeError):
    """``nearest()`` was called on a cache whose backbone hash has changed.

    The stored embeddings were produced by a different backbone, so a
    similarity query would be meaningless. Call
    :meth:`EmbeddingCache.clear_if_hash_mismatch` to rebuild before
    querying again. The file is never auto-deleted — the maker can inspect
    before-vs-after.
    """


def default_cache_path() -> Path:
    """Resolve ``inventory/.embeddings/vectors.sqlite`` from the repo root."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent / "inventory" / ".embeddings" / "vectors.sqlite"
    # Fall back to CWD-relative when running outside a checkout.
    return Path("inventory") / ".embeddings" / "vectors.sqlite"


def _vec_to_blob(vector: Sequence[float]) -> bytes:
    import numpy as np

    arr = np.asarray(vector, dtype=np.float32).reshape(-1)
    if arr.shape[0] != EMBED_DIM:
        raise ValueError(f"expected a {EMBED_DIM}-D vector, got {arr.shape[0]}-D")
    return arr.tobytes()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EmbeddingCache:
    """sqlite3-backed embedding store with brute-force cosine search."""

    def __init__(
        self,
        model_hash: str,
        *,
        path: Path | str | None = None,
        connect: Any | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else default_cache_path()
        self._model_hash = model_hash
        if connect is not None:
            self._conn = connect(str(self.path))
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._hash_mismatch = self._check_hash()

    # -- schema / lifecycle ------------------------------------------------

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vectors (
                row_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                label        TEXT NOT NULL,
                marking_text TEXT,
                image_hash   TEXT NOT NULL UNIQUE,
                vec          BLOB NOT NULL,
                created_at   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def _stored_hash(self) -> str | None:
        cur = self._conn.execute(
            "SELECT value FROM meta WHERE key = ?", (_META_MODEL_HASH,)
        )
        row = cur.fetchone()
        return row["value"] if row else None

    def _check_hash(self) -> bool:
        """Return True when the stored backbone hash differs from ours."""
        stored = self._stored_hash()
        if stored is None:
            # Fresh cache — adopt the running backbone's identity.
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                (_META_MODEL_HASH, self._model_hash),
            )
            self._conn.commit()
            return False
        return stored != self._model_hash

    @property
    def hash_mismatch(self) -> bool:
        return self._hash_mismatch

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "EmbeddingCache":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- writes ------------------------------------------------------------

    def insert(
        self,
        vector: Sequence[float],
        label: str,
        marking_text: str | None,
        image_hash: str,
    ) -> int:
        """Insert one embedding; idempotent on ``image_hash``.

        A second insert for the same ``image_hash`` returns the existing
        row id rather than appending a duplicate.
        """
        existing = self._conn.execute(
            "SELECT row_id FROM vectors WHERE image_hash = ?", (image_hash,)
        ).fetchone()
        if existing is not None:
            return int(existing["row_id"])
        cur = self._conn.execute(
            "INSERT INTO vectors (label, marking_text, image_hash, vec, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (label, marking_text, image_hash, _vec_to_blob(vector), _now_iso()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def delete_last_inserted(self) -> bool:
        """Pop the most recently inserted row. ``False`` on an empty cache."""
        row = self._conn.execute(
            "SELECT MAX(row_id) AS m FROM vectors"
        ).fetchone()
        if row is None or row["m"] is None:
            return False
        self._conn.execute("DELETE FROM vectors WHERE row_id = ?", (row["m"],))
        self._conn.commit()
        return True

    def delete_row(self, row_id: int) -> bool:
        """Delete a specific row by id. ``True`` if a row was removed."""
        cur = self._conn.execute("DELETE FROM vectors WHERE row_id = ?", (row_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def clear_if_hash_mismatch(self, model_hash: str) -> bool:
        """Rebuild gate: if the cache is in mismatch, wipe rows + re-pin hash.

        Returns ``True`` when a clear happened. After clearing, the cache
        is empty and ``nearest()`` is allowed again under the new hash.
        """
        if not self._hash_mismatch and self._stored_hash() == model_hash:
            return False
        self._conn.execute("DELETE FROM vectors")
        self._conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_META_MODEL_HASH, model_hash),
        )
        self._conn.commit()
        self._model_hash = model_hash
        self._hash_mismatch = False
        return True

    # -- reads -------------------------------------------------------------

    def __len__(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM vectors").fetchone()["c"])

    def nearest(self, vector: Sequence[float], k: int = 3) -> list[Neighbour]:
        """Up to ``k`` neighbours by ascending cosine distance.

        Raises :class:`CacheHashMismatch` when the stored backbone hash no
        longer matches the running one.
        """
        if self._hash_mismatch:
            raise CacheHashMismatch(
                f"cache at {self.path} was built by a different backbone; "
                "clear_if_hash_mismatch() to rebuild before querying"
            )
        import numpy as np

        rows = self._conn.execute(
            "SELECT row_id, label, marking_text, vec FROM vectors"
        ).fetchall()
        if not rows:
            return []
        query = np.asarray(vector, dtype=np.float32).reshape(-1)
        qnorm = float(np.linalg.norm(query))
        if qnorm == 0.0:
            raise ValueError("cannot query nearest() with a zero vector")
        query = query / qnorm

        mat = np.vstack(
            [np.frombuffer(r["vec"], dtype=np.float32) for r in rows]
        )
        # Stored vectors are already unit-norm, but renormalise defensively
        # so a non-normalised insert cannot distort the ranking.
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        sims = (mat / norms) @ query
        distances = 1.0 - sims  # cosine distance

        order = np.argsort(distances, kind="stable")[:k]
        return [
            Neighbour(
                row_id=int(rows[i]["row_id"]),
                label=str(rows[i]["label"]),
                marking_text=(
                    None if rows[i]["marking_text"] is None else str(rows[i]["marking_text"])
                ),
                distance=float(distances[i]),
            )
            for i in order
        ]
