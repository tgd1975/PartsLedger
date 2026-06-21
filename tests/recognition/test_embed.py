"""Tests for partsledger.recognition.embed — TASK-039.

The heavy DINOv2 forward pass and the ~80 MB weight download are network-
and torch-bound; these host tests drive the pure post-processing and the
injected model/loader seams with fakes, so they run on an air-gapped,
torch-free runner. The one network-touching path (a real backbone load and
``MODEL_HASH`` read) is exercised only behind a skip-if-unavailable guard.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.recognition import embed  # noqa: E402

np = pytest.importorskip("numpy")


@pytest.fixture(autouse=True)
def _reset_model_cache():
    """Each test starts with an unloaded backbone."""
    embed._MODEL = None
    embed._MODEL_HASH = None
    yield
    embed._MODEL = None
    embed._MODEL_HASH = None


class _FakeModel:
    """Stand-in backbone: returns a fixed raw feature, records a state_dict."""

    def __init__(self, feature, state=None):
        self._feature = feature
        self._state = state or {"w": np.arange(4, dtype=np.float32)}

    def __call__(self, _tensor):
        return self._feature

    def state_dict(self):
        return self._state


# ---------------------------------------------------------------------------
# _postprocess — the pure normalisation core


def test_postprocess_shape_dtype_and_unit_norm():
    raw = np.linspace(1.0, 2.0, embed.EMBED_DIM).astype(np.float64)
    out = embed._postprocess(raw)
    assert out.shape == (embed.EMBED_DIM,)
    assert out.dtype == np.float32
    assert abs(float(np.linalg.norm(out)) - 1.0) < 1e-6


def test_postprocess_is_deterministic():
    raw = np.random.default_rng(0).standard_normal(embed.EMBED_DIM)
    a = embed._postprocess(raw)
    b = embed._postprocess(raw.copy())
    assert np.array_equal(a, b)


def test_postprocess_rejects_wrong_dim():
    with pytest.raises(ValueError):
        embed._postprocess(np.ones(10, dtype=np.float32))


def test_postprocess_rejects_zero_vector():
    with pytest.raises(ValueError):
        embed._postprocess(np.zeros(embed.EMBED_DIM, dtype=np.float32))


# ---------------------------------------------------------------------------
# embed() with injected model + preprocess — torch-free


def test_embed_returns_unit_768_vector():
    feature = np.random.default_rng(1).standard_normal(embed.EMBED_DIM)
    fake = _FakeModel(feature)
    out = embed.embed(np.zeros((8, 8, 3)), model=fake, preprocess=lambda im: im)
    assert out.shape == (embed.EMBED_DIM,)
    assert out.dtype == np.float32
    assert abs(float(np.linalg.norm(out)) - 1.0) < 1e-6


def test_embed_is_deterministic_on_identical_input():
    feature = np.random.default_rng(2).standard_normal(embed.EMBED_DIM)
    fake = _FakeModel(feature)
    a = embed.embed(np.zeros((8, 8, 3)), model=fake, preprocess=lambda im: im)
    b = embed.embed(np.zeros((8, 8, 3)), model=fake, preprocess=lambda im: im)
    assert np.array_equal(a, b)


# ---------------------------------------------------------------------------
# load_model idempotency


def test_load_model_loads_once():
    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return _FakeModel(np.ones(embed.EMBED_DIM, dtype=np.float32))

    m1 = embed.load_model(loader=loader)
    m2 = embed.load_model(loader=loader)
    assert m1 is m2
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# MODEL_HASH shape + provenance


def test_compute_model_hash_shape():
    fake = _FakeModel(np.ones(embed.EMBED_DIM, dtype=np.float32))
    h = embed.compute_model_hash(fake)
    assert h.startswith("dinov2_vits14#sha256:")
    hexpart = h.split(":", 1)[1]
    assert len(hexpart) == 64
    assert all(c in "0123456789abcdef" for c in hexpart)


def test_compute_model_hash_changes_with_weights():
    a = embed.compute_model_hash(
        _FakeModel(np.ones(1), state={"w": np.arange(4, dtype=np.float32)})
    )
    b = embed.compute_model_hash(
        _FakeModel(np.ones(1), state={"w": np.arange(4, dtype=np.float32) + 1})
    )
    assert a != b


def test_model_hash_constant_via_getattr():
    """``embed.MODEL_HASH`` resolves through the cached loaded model."""
    feature = np.ones(embed.EMBED_DIM, dtype=np.float32)
    embed.load_model(loader=lambda: _FakeModel(feature))
    assert embed.MODEL_HASH.startswith("dinov2_vits14#sha256:")
    assert embed.MODEL_HASH == embed.model_hash()


def test_unknown_module_attribute_raises():
    with pytest.raises(AttributeError):
        embed.NOT_A_REAL_ATTR  # noqa: B018


# ---------------------------------------------------------------------------
# Network path — real backbone, guarded


@pytest.mark.skipif(
    os.environ.get("PL_RUN_NETWORK_TESTS") != "1",
    reason="network/torch path — set PL_RUN_NETWORK_TESTS=1 to run",
)
def test_real_backbone_load():  # pragma: no cover - network
    vec = embed.embed(np.zeros((224, 224, 3), dtype=np.uint8))
    assert vec.shape == (embed.EMBED_DIM,)
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-5
