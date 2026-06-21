"""Tests for partsledger.recognition.pipeline.Pipeline.run — TASK-043.

Cache, VLM, writer, enrichment, and journal are all faked; every branch of
the routing table and the two failure edges (soft enrichment, hard writer)
are covered with no torch, no camera, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.recognition import pipeline as pl  # noqa: E402
from partsledger.recognition.cache import Neighbour  # noqa: E402
from partsledger.recognition.vlm import HedgedID, NeedsReframe, NoIdea  # noqa: E402

VEC = [1.0, 0.0, 0.0]
TH = pl.Thresholds()  # tight 0.10, medium 0.25


class FakeCache:
    def __init__(self, neighbours):
        self.neighbours = neighbours
        self.inserted = []
        self.deleted = []
        self._rid = 1000

    def nearest(self, vector, k=3):
        return self.neighbours[:k]

    def insert(self, vector, label, marking, image_hash):
        self._rid += 1
        self.inserted.append((label, marking, image_hash))
        return self._rid

    def delete_row(self, row_id):
        self.deleted.append(row_id)
        return True


class FakeWriter:
    def __init__(self, qty=4, fail=False):
        self.calls = []
        self.qty = qty
        self.fail = fail

    def __call__(self, part_id, qty_delta, *, source):
        self.calls.append((part_id, qty_delta, source))
        if self.fail:
            raise RuntimeError("simulated disk failure")
        return SimpleNamespace(qty=self.qty, disposition="bumped", section="ICs")


def _pipeline(cache, *, vlm=None, writer=None, enrich=None, journal=None, **kw):
    return pl.Pipeline(
        cache=cache,
        vlm_identify=vlm or (lambda img, hints: NoIdea()),
        writer_upsert=writer or FakeWriter(),
        enrich=enrich,
        journal=journal,
        embed_fn=lambda img: VEC,
        thresholds=TH,
        **kw,
    )


def _n(label, distance):
    return Neighbour(row_id=1, label=label, marking_text=None, distance=distance)


# ---------------------------------------------------------------------------
# tight → cache write


def test_tight_writes_from_cache():
    cache = FakeCache([_n("lm358n", 0.02)])
    writer = FakeWriter()
    p = _pipeline(cache, writer=writer)
    out = p.run(object())
    assert isinstance(out, pl.Wrote)
    assert out.label == "lm358n"
    assert out.source == "cache"
    assert writer.calls == [("lm358n", 1, "cache")]
    assert len(cache.inserted) == 1  # cache-learn happened


# ---------------------------------------------------------------------------
# tight_ambiguous → VLM → write (source vlm)


def test_tight_ambiguous_routes_to_vlm():
    cache = FakeCache([_n("lm358n", 0.02), _n("lm358p", 0.05)])

    def vlm(img, hints):
        return HedgedID(label="LM358N", marking="LM358N", hedge="likely")

    writer = FakeWriter()
    p = _pipeline(cache, vlm=vlm, writer=writer)
    out = p.run(object())
    assert isinstance(out, pl.Wrote)
    assert out.source == "vlm"
    assert writer.calls[0][2] == "vlm"
    assert len(cache.inserted) == 1


# ---------------------------------------------------------------------------
# medium → reframe loop → escalate on third attempt


def test_medium_reframes_then_escalates():
    cache = FakeCache([_n("x", 0.15)])
    writer = FakeWriter()
    p = _pipeline(cache, writer=writer)
    out1 = p.run(object())
    out2 = p.run(object())
    out3 = p.run(object())
    assert isinstance(out1, pl.Reframing)
    assert out1.hint == pl.GENERIC_HINT
    assert isinstance(out2, pl.Reframing)
    assert isinstance(out3, pl.EscalatedToManual)
    assert writer.calls == []  # never wrote
    assert cache.inserted == []


# ---------------------------------------------------------------------------
# miss + VLM no-idea → escalate, no side-effects


def test_miss_no_idea_escalates():
    cache = FakeCache([])  # empty → miss
    writer = FakeWriter()
    p = _pipeline(cache, vlm=lambda img, hints: NoIdea(), writer=writer)
    out = p.run(object())
    assert isinstance(out, pl.EscalatedToManual)
    assert writer.calls == []
    assert cache.inserted == []


def test_miss_vlm_needs_reframe():
    cache = FakeCache([])

    def vlm(img, hints):
        return NeedsReframe(hint="too dark", family="lighting")

    p = _pipeline(cache, vlm=vlm)
    out = p.run(object())
    assert isinstance(out, pl.Reframing)
    assert out.family == "lighting"


# ---------------------------------------------------------------------------
# enrichment failure is soft


def test_enrichment_failure_does_not_roll_back():
    cache = FakeCache([_n("lm358n", 0.02)])
    writer = FakeWriter()

    def boom(part_id):
        raise RuntimeError("nexar down")

    p = _pipeline(cache, writer=writer, enrich=boom)
    out = p.run(object())
    assert isinstance(out, pl.Wrote)  # write + cache-learn still landed
    assert len(writer.calls) == 1
    assert len(cache.inserted) == 1


# ---------------------------------------------------------------------------
# writer failure aborts before cache-learn


def test_writer_failure_aborts_before_cache_learn():
    cache = FakeCache([_n("lm358n", 0.02)])
    writer = FakeWriter(fail=True)
    p = _pipeline(cache, writer=writer)
    with pytest.raises(RuntimeError):
        p.run(object())
    assert cache.inserted == []  # cache and inventory never diverge


# ---------------------------------------------------------------------------
# journal hand-off


def test_journal_records_on_write():
    cache = FakeCache([_n("lm358n", 0.02)])
    recorded = []
    journal = SimpleNamespace(record=lambda e: recorded.append(e))
    p = _pipeline(cache, journal=journal)
    p.run(object())
    assert len(recorded) == 1
    entry = recorded[0]
    assert entry.part_id == "lm358n"
    assert entry.qty_before == 3
    assert entry.qty_after == 4


# ---------------------------------------------------------------------------
# distinct-part resets the reframe counter


def test_distinct_part_resets_reframe_counter():
    cache = FakeCache([_n("x", 0.15)])  # medium
    p = pl.Pipeline(
        cache=cache,
        vlm_identify=lambda img, hints: NoIdea(),
        writer_upsert=FakeWriter(),
        embed_fn=lambda img: img,  # the image *is* the vector here
        thresholds=TH,
        max_reframes=2,
    )
    assert isinstance(p.run([1.0, 0.0, 0.0]), pl.Reframing)
    assert isinstance(p.run([1.0, 0.0, 0.0]), pl.Reframing)
    # A distinct part (orthogonal vector, distance 1.0 >= 0.25) resets.
    assert isinstance(p.run([0.0, 1.0, 0.0]), pl.Reframing)
    assert isinstance(p.run([0.0, 1.0, 0.0]), pl.Reframing)
