"""Tests for partsledger.enrichment.chain — TASK-050."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.enrichment import Enriched, NoEnrichment  # noqa: E402
from partsledger.enrichment.chain import enrich_and_page  # noqa: E402


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
