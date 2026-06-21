"""Tests for partsledger.enrichment.cache — TASK-046."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.enrichment.cache import TTL_SECONDS, NexarCache  # noqa: E402

NOW = 1_700_000_000  # fixed reference epoch
DAY = 86_400
PAYLOAD = {
    "mpn": "LM358N",
    "manufacturer": "Texas Instruments",
    "datasheet_url": "https://ti.com/lm358.pdf",
    "category_path": "ICs / Linear / Amplifiers",
    "lifecycle_status": "Active",
}


def _cache(tmp_path):
    return NexarCache(path=tmp_path / "nexar_cache.sqlite")


# ---------------------------------------------------------------------------
# round-trip


def test_put_get_roundtrip(tmp_path):
    with _cache(tmp_path) as c:
        c.put("LM358N", PAYLOAD, "Active", now=NOW)
        got = c.get("LM358N", now=NOW)
        assert got == PAYLOAD


def test_get_missing_returns_none(tmp_path):
    with _cache(tmp_path) as c:
        assert c.get("NOPE", now=NOW) is None


# ---------------------------------------------------------------------------
# TTL for Active rows


def test_active_within_ttl_returns_payload(tmp_path):
    with _cache(tmp_path) as c:
        c.put("LM358N", PAYLOAD, "Active", now=NOW - 29 * DAY)
        assert c.get("LM358N", now=NOW) == PAYLOAD


def test_active_past_ttl_returns_none(tmp_path):
    with _cache(tmp_path) as c:
        c.put("LM358N", PAYLOAD, "Active", now=NOW - 31 * DAY)
        assert c.get("LM358N", now=NOW) is None


def test_ttl_constant_is_30_days(tmp_path):
    assert TTL_SECONDS == 30 * DAY


# ---------------------------------------------------------------------------
# frozen lifecycles never expire


def test_obsolete_never_expires(tmp_path):
    with _cache(tmp_path) as c:
        c.put("OLDPART", PAYLOAD, "Obsolete", now=NOW - 365 * DAY)
        assert c.get("OLDPART", now=NOW) == PAYLOAD


def test_nrnd_never_expires(tmp_path):
    with _cache(tmp_path) as c:
        c.put("OLDPART", PAYLOAD, "NRND", now=NOW - 365 * DAY)
        assert c.get("OLDPART", now=NOW) == PAYLOAD


# ---------------------------------------------------------------------------
# persistence


def test_persistence_across_reopen(tmp_path):
    p = tmp_path / "nexar_cache.sqlite"
    with NexarCache(path=p) as c:
        c.put("LM358N", PAYLOAD, "Active", now=NOW)
    with NexarCache(path=p) as c2:
        assert c2.get("LM358N", now=NOW) == PAYLOAD


# ---------------------------------------------------------------------------
# expire_stale only removes stale Active rows


def test_expire_stale_removes_only_stale_active(tmp_path):
    with _cache(tmp_path) as c:
        c.put("STALE", PAYLOAD, "Active", now=NOW - 31 * DAY)
        c.put("FRESH", PAYLOAD, "Active", now=NOW - 1 * DAY)
        c.put("OBSOLETE", PAYLOAD, "Obsolete", now=NOW - 365 * DAY)
        c.put("NRND", PAYLOAD, "NRND", now=NOW - 365 * DAY)
        removed = c.expire_stale(now=NOW)
        assert removed == 1
        assert c.get("STALE", now=NOW) is None
        assert c.get("FRESH", now=NOW) == PAYLOAD
        assert c.get("OBSOLETE", now=NOW) == PAYLOAD
        assert c.get("NRND", now=NOW) == PAYLOAD
