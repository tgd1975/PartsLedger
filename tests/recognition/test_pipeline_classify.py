"""Tests for partsledger.recognition.pipeline.classify — TASK-041.

A stub cache returns neighbours with exact, controlled cosine distances so
the band boundaries (0.05 / 0.10 / 0.20 / 0.25 / 0.30) can be asserted
precisely. No real images, no real backbone.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.recognition import pipeline as pl  # noqa: E402
from partsledger.recognition.cache import Neighbour  # noqa: E402


class StubCache:
    def __init__(self, neighbours):
        self._neighbours = neighbours

    def nearest(self, vector, k=3):
        return self._neighbours[:k]


def _n(label, distance, row_id=1, marking=None):
    return Neighbour(row_id=row_id, label=label, marking_text=marking, distance=distance)


DEFAULT_TH = pl.Thresholds()  # tight=0.10, medium=0.25


# ---------------------------------------------------------------------------
# Band boundaries (parametric)


@pytest.mark.parametrize(
    "distance,expected",
    [
        (0.05, "tight"),
        (0.099, "tight"),
        (0.10, "medium"),   # boundary: tight is strict <
        (0.20, "medium"),
        (0.249, "medium"),
        (0.25, "miss"),     # boundary: medium is strict <
        (0.30, "miss"),
    ],
)
def test_band_at_boundaries(distance, expected):
    cache = StubCache([_n("lm358n", distance)])
    v = pl.classify_vector([0.0], cache, thresholds=DEFAULT_TH)
    assert v.band == expected
    assert v.top1_candidate == "lm358n"


# ---------------------------------------------------------------------------
# tight_ambiguous


def test_tight_ambiguous_two_distinct_labels_within_tight():
    cache = StubCache([_n("lm358n", 0.02), _n("lm358p", 0.05), _n("lm358n", 0.07)])
    v = pl.classify_vector([0.0], cache, thresholds=DEFAULT_TH)
    assert v.band == "tight_ambiguous"
    assert set(v.neighbour_labels) == {"lm358n", "lm358p"}


def test_tight_single_label_repeated_is_not_ambiguous():
    cache = StubCache([_n("lm358n", 0.02), _n("lm358n", 0.06)])
    v = pl.classify_vector([0.0], cache, thresholds=DEFAULT_TH)
    assert v.band == "tight"


def test_second_label_outside_tight_is_not_ambiguous():
    # Nearest is tight, but the second distinct label sits in the medium band.
    cache = StubCache([_n("lm358n", 0.02), _n("ne555", 0.18)])
    v = pl.classify_vector([0.0], cache, thresholds=DEFAULT_TH)
    assert v.band == "tight"


# ---------------------------------------------------------------------------
# empty cache


def test_empty_cache_is_miss():
    v = pl.classify_vector([0.0], StubCache([]), thresholds=DEFAULT_TH)
    assert v.band == "miss"
    assert v.top1_candidate is None
    assert v.neighbour_labels == []


# ---------------------------------------------------------------------------
# threshold loading from config


def test_thresholds_load_from_config(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        "[recognition]\ntight_distance = 0.30\nmedium_distance = 0.50\n",
        encoding="utf-8",
    )
    th = pl.load_thresholds(config_path=cfg)
    assert th.tight == 0.30
    assert th.medium == 0.50
    # A distance of 0.25 is now 'tight' under the loosened config.
    cache = StubCache([_n("x", 0.25)])
    assert pl.classify_vector([0.0], cache, thresholds=th).band == "tight"


def test_thresholds_default_when_no_config(tmp_path):
    th = pl.load_thresholds(config_path=tmp_path / "absent.toml")
    assert th.tight == pl.DEFAULT_TIGHT_DISTANCE
    assert th.medium == pl.DEFAULT_MEDIUM_DISTANCE


# ---------------------------------------------------------------------------
# classify() wires embed_fn + cache together


def test_classify_uses_injected_embed_and_cache():
    cache = StubCache([_n("lm358n", 0.01)])
    v = pl.classify(
        object(),
        cache=cache,
        embed_fn=lambda img: [0.0],
        thresholds=DEFAULT_TH,
    )
    assert v.band == "tight"
    assert v.top1_candidate == "lm358n"
