"""Tests for partsledger.enrichment.chain — TASK-050."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.enrichment import Enriched, NoEnrichment  # noqa: E402
from partsledger.enrichment.chain import chain_on_new_row, enrich_and_page  # noqa: E402


def _enriched(pid, source="manual"):
    return Enriched({"mpn": pid})


# ---------------------------------------------------------------------------
# skill-path first sighting: enrich + page-gen both fire


def test_first_sighting_runs_enrich_then_page(tmp_path):
    pages = []
    res = enrich_and_page(
        "LM358N",
        enrich_fn=_enriched,
        page_gen=lambda pid: pages.append(pid),
        page_exists=lambda pid: False,
    )
    assert isinstance(res.enrichment, Enriched)
    assert res.page_generated is True
    assert pages == ["LM358N"]


# ---------------------------------------------------------------------------
# idempotency: page already exists → no regeneration


def test_existing_page_skips_pagegen(tmp_path):
    pages = []
    res = enrich_and_page(
        "LM358N",
        enrich_fn=_enriched,
        page_gen=lambda pid: pages.append(pid),
        page_exists=lambda pid: True,
    )
    assert res.page_generated is False
    assert pages == []


# ---------------------------------------------------------------------------
# no enrichment → no page-gen


def test_no_enrichment_skips_pagegen(tmp_path):
    pages = []
    res = enrich_and_page(
        "ZZZ",
        enrich_fn=lambda pid, source="manual": NoEnrichment("unknown_mpn"),
        page_gen=lambda pid: pages.append(pid),
        page_exists=lambda pid: False,
    )
    assert isinstance(res.enrichment, NoEnrichment)
    assert res.page_generated is False
    assert pages == []


# ---------------------------------------------------------------------------
# TASK-020 — new-row gate on /inventory-add disposition


def test_new_row_triggers_chain():
    pages = []
    res = chain_on_new_row(
        "inserted", "LM358N",
        enrich_fn=_enriched, page_gen=lambda p: pages.append(p),
        page_exists=lambda p: False,
    )
    assert res is not None
    assert res.page_generated is True
    assert pages == ["LM358N"]


def test_qty_bump_does_not_chain():
    enriched_calls = []
    res = chain_on_new_row(
        "bumped", "LM358N",
        enrich_fn=lambda p, source="manual": enriched_calls.append(p) or _enriched(p),
        page_gen=lambda p: None,
        page_exists=lambda p: False,
    )
    assert res is None
    assert enriched_calls == []  # no re-enrichment on a bump


def test_no_page_still_enriches_but_skips_page():
    pages = []
    res = chain_on_new_row(
        "inserted", "LM358N", no_page=True,
        enrich_fn=_enriched, page_gen=lambda p: pages.append(p),
        page_exists=lambda p: False,
    )
    assert isinstance(res.enrichment, Enriched)
    assert res.page_generated is False
    assert pages == []
