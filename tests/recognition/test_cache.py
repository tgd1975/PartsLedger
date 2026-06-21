"""Tests for partsledger.recognition.cache — TASK-040.

Each test uses an isolated tmp-path cache file. Vectors are synthetic 768-D
unit vectors at known angular separations — no real backbone, no images.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.recognition import cache as cache_mod  # noqa: E402
from partsledger.recognition.cache import (  # noqa: E402
    CacheHashMismatch,
    EmbeddingCache,
)

np = pytest.importorskip("numpy")

HASH_A = "dinov2_vits14#sha256:" + "a" * 64
HASH_B = "dinov2_vits14#sha256:" + "b" * 64


def _unit(*, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(cache_mod.EMBED_DIM).astype(np.float32)
    return v / np.linalg.norm(v)


def _basis(index: int) -> np.ndarray:
    v = np.zeros(cache_mod.EMBED_DIM, dtype=np.float32)
    v[index] = 1.0
    return v


def _open(tmp_path, model_hash=HASH_A) -> EmbeddingCache:
    return EmbeddingCache(model_hash, path=tmp_path / "vectors.sqlite")


# ---------------------------------------------------------------------------
# insert + nearest round-trip


def test_insert_then_nearest_finds_exact_match(tmp_path):
    with _open(tmp_path) as c:
        v = _unit(seed=1)
        rid = c.insert(v, "lm358n", "LM358N", "hash1")
        hits = c.nearest(v, k=1)
        assert len(hits) == 1
        assert hits[0].row_id == rid
        assert hits[0].label == "lm358n"
        assert hits[0].marking_text == "LM358N"
        assert hits[0].distance < 1e-5


def test_nearest_sorts_ascending_distance(tmp_path):
    with _open(tmp_path) as c:
        c.insert(_basis(0), "near", None, "h0")
        c.insert(_basis(1), "mid", None, "h1")
        c.insert(_basis(2), "far", None, "h2")
        # Query close to basis-0 but tilted toward basis-1.
        q = np.zeros(cache_mod.EMBED_DIM, dtype=np.float32)
        q[0] = 0.9
        q[1] = 0.1
        hits = c.nearest(q, k=3)
        labels = [h.label for h in hits]
        assert labels[0] == "near"
        dists = [h.distance for h in hits]
        assert dists == sorted(dists)


def test_nearest_respects_k(tmp_path):
    with _open(tmp_path) as c:
        for i in range(5):
            c.insert(_basis(i), f"l{i}", None, f"h{i}")
        assert len(c.nearest(_basis(0), k=2)) == 2


def test_empty_cache_nearest_returns_empty(tmp_path):
    with _open(tmp_path) as c:
        assert c.nearest(_unit(seed=3), k=3) == []


# ---------------------------------------------------------------------------
# idempotency on image_hash


def test_insert_idempotent_on_image_hash(tmp_path):
    with _open(tmp_path) as c:
        r1 = c.insert(_unit(seed=4), "a", None, "samehash")
        r2 = c.insert(_unit(seed=5), "b", None, "samehash")
        assert r1 == r2
        assert len(c) == 1


# ---------------------------------------------------------------------------
# delete_last_inserted


def test_delete_last_inserted_pops_most_recent(tmp_path):
    with _open(tmp_path) as c:
        c.insert(_basis(0), "first", None, "h0")
        last = c.insert(_basis(1), "second", None, "h1")
        assert c.delete_last_inserted() is True
        remaining = c.nearest(_basis(0), k=5)
        assert all(h.row_id != last for h in remaining)
        assert len(c) == 1


def test_delete_last_inserted_on_empty_returns_false(tmp_path):
    with _open(tmp_path) as c:
        assert c.delete_last_inserted() is False


# ---------------------------------------------------------------------------
# model-hash mismatch gate


def test_hash_mismatch_refuses_nearest(tmp_path):
    p = tmp_path / "vectors.sqlite"
    with EmbeddingCache(HASH_A, path=p) as c:
        c.insert(_basis(0), "x", None, "h0")
    # Reopen with a different backbone hash.
    with EmbeddingCache(HASH_B, path=p) as c2:
        assert c2.hash_mismatch is True
        with pytest.raises(CacheHashMismatch):
            c2.nearest(_basis(0), k=1)
        # Clearing rebuilds — nearest allowed again, cache now empty.
        assert c2.clear_if_hash_mismatch(HASH_B) is True
        assert c2.nearest(_basis(0), k=1) == []


def test_matching_hash_does_not_refuse(tmp_path):
    p = tmp_path / "vectors.sqlite"
    with EmbeddingCache(HASH_A, path=p) as c:
        c.insert(_basis(0), "x", None, "h0")
    with EmbeddingCache(HASH_A, path=p) as c2:
        assert c2.hash_mismatch is False
        assert len(c2.nearest(_basis(0), k=1)) == 1


# ---------------------------------------------------------------------------
# persistence across process restart


def test_persistence_across_reopen(tmp_path):
    p = tmp_path / "vectors.sqlite"
    with EmbeddingCache(HASH_A, path=p) as c:
        rid = c.insert(_basis(7), "persisted", "MARK", "h7")
    # Simulated process B.
    with EmbeddingCache(HASH_A, path=p) as c2:
        hits = c2.nearest(_basis(7), k=1)
        assert hits[0].row_id == rid
        assert hits[0].label == "persisted"
        assert hits[0].marking_text == "MARK"


def test_default_cache_path_points_into_inventory():
    p = cache_mod.default_cache_path()
    assert p.name == "vectors.sqlite"
    assert p.parent.name == ".embeddings"
