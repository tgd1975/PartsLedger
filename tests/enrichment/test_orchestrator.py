"""Tests for partsledger.enrichment.enrich — TASK-048.

Nexar transport and the family fallback are mocked; the cache is a temp-dir
SQLite; the writer runs for real against a temp INVENTORY.md so the
no-clobber cell-fill is exercised end-to-end.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.enrichment import Enriched, NoEnrichment, enrich  # noqa: E402
from partsledger.enrichment.cache import NexarCache  # noqa: E402
from partsledger.enrichment.nexar import NexarPart  # noqa: E402
from partsledger.inventory.writer import _upsert_row_at  # noqa: E402

TEMPLATE = """\
# Inventory

## ICs

| Part   | Qty | Description | Datasheet | Octopart | Source | Notes |
| ------ | --- | ----------- | --------- | -------- | ------ | ----- |
| LM358N | 1   |             |           |          | manual |       |
"""

PART = NexarPart(
    mpn="LM358N",
    manufacturer="Texas Instruments",
    datasheet_url="https://www.ti.com/lit/ds/symlink/lm358.pdf",
    category_path="ICs / Linear / Amplifiers",
    lifecycle_status="Active",
)


class FakeClient:
    def __init__(self, part=None, *, enabled=True, raises=None):
        self._part = part
        self.enabled = enabled
        self._raises = raises
        self.calls = 0

    def lookup_mpn(self, mpn):
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return self._part


@pytest.fixture()
def inv(tmp_path):
    p = tmp_path / "INVENTORY.md"
    p.write_text(TEMPLATE)
    return p


@pytest.fixture()
def writer(inv):
    def _writer(part_id, qty, *, source, cells=None, cells_if_empty=None, section=None):
        return _upsert_row_at(
            part_id, qty, source=source, section=section,
            cells=cells, cells_if_empty=cells_if_empty, path=inv,
        )

    return _writer


def _cache(tmp_path):
    return NexarCache(path=tmp_path / "nexar_cache.sqlite")


# ---------------------------------------------------------------------------
# happy path


def test_fresh_enrich_fills_empty_cells(tmp_path, inv, writer):
    res = enrich(
        "LM358N",
        client=FakeClient(PART),
        cache=_cache(tmp_path),
        family_lookup=lambda m: None,
        writer_upsert=writer,
    )
    assert isinstance(res, Enriched)
    text = inv.read_text()
    assert "Amplifiers" in text  # Description ← category_path
    assert "lm358.pdf" in text  # Datasheet ← link


def test_rerun_is_noop(tmp_path, inv, writer):
    cache = _cache(tmp_path)
    enrich("LM358N", client=FakeClient(PART), cache=cache, family_lookup=lambda m: None, writer_upsert=writer)
    before = inv.read_text()
    # Re-run: cache hit, cells already populated → writer no-op.
    res = enrich("LM358N", client=FakeClient(PART, raises=AssertionError("nexar must not be hit")),
                 cache=cache, family_lookup=lambda m: None, writer_upsert=writer)
    assert isinstance(res, Enriched)
    assert inv.read_text() == before


def test_no_clobber_handedit(tmp_path, inv, writer):
    # Maker hand-edited Description first.
    inv.write_text(TEMPLATE.replace("|             |", "| Dual op-amp |"))
    enrich("LM358N", client=FakeClient(PART), cache=_cache(tmp_path), family_lookup=lambda m: None, writer_upsert=writer)
    text = inv.read_text()
    assert "Dual op-amp" in text
    assert "Amplifiers" not in text  # category did NOT clobber the hand-edit


# ---------------------------------------------------------------------------
# soft-fail reasons


def test_offline_when_disabled(tmp_path, inv, writer):
    before = inv.read_text()
    res = enrich("LM358N", client=FakeClient(PART, enabled=False), cache=_cache(tmp_path),
                 family_lookup=lambda m: None, writer_upsert=writer)
    assert isinstance(res, NoEnrichment)
    assert res.reason == "offline"
    assert inv.read_text() == before  # zero MD writes


def test_network_unreachable(tmp_path, inv, writer):
    res = enrich("LM358N", client=FakeClient(raises=ConnectionError("boom")), cache=_cache(tmp_path),
                 family_lookup=lambda m: None, writer_upsert=writer)
    assert isinstance(res, NoEnrichment)
    assert res.reason == "network_unreachable"


def test_unknown_mpn(tmp_path, inv, writer):
    res = enrich("ZZZ999", client=FakeClient(part=None), cache=_cache(tmp_path),
                 family_lookup=lambda m: None, writer_upsert=writer)
    assert isinstance(res, NoEnrichment)
    assert res.reason == "unknown_mpn"


def test_fallback_missed(tmp_path, inv, writer):
    no_ds = NexarPart(mpn="LM358N", manufacturer="TI", datasheet_url=None,
                      category_path="ICs", lifecycle_status="Active")
    res = enrich("LM358N", client=FakeClient(no_ds), cache=_cache(tmp_path),
                 family_lookup=lambda m: None, writer_upsert=writer)
    assert isinstance(res, NoEnrichment)
    assert res.reason == "fallback_missed"


def test_nexar_none_but_family_hit_enriches(tmp_path, inv, writer):
    res = enrich("LM358N", client=FakeClient(part=None), cache=_cache(tmp_path),
                 family_lookup=lambda m: "https://ti.com/lm358.pdf", writer_upsert=writer)
    assert isinstance(res, Enriched)
    assert "lm358.pdf" in inv.read_text()


# ---------------------------------------------------------------------------
# pipeline ordering: cache first, then nexar


def test_cache_consulted_before_nexar(tmp_path, inv, writer):
    cache = _cache(tmp_path)
    cache.put("LM358N", {"mpn": "LM358N", "datasheet_url": "https://x/cached.pdf",
                         "category_path": "Cached", "lifecycle_status": "Active",
                         "manufacturer": "TI"}, "Active")
    client = FakeClient(PART, raises=AssertionError("nexar must not be hit on cache hit"))
    res = enrich("LM358N", client=client, cache=cache, family_lookup=lambda m: None, writer_upsert=writer)
    assert isinstance(res, Enriched)
    assert client.calls == 0
    assert "cached.pdf" in inv.read_text()
