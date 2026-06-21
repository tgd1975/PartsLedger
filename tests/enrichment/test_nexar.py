"""Tests for partsledger.enrichment.nexar — TASK-045.

The OAuth + GraphQL HTTP is injected via a fake transport, so auth, token
caching, parsing, the junk-MPN path, and secrets redaction run with no live
Nexar account.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.enrichment import nexar  # noqa: E402
from partsledger.enrichment.nexar import (  # noqa: E402
    EnrichmentDisabledError,
    NexarAuthError,
    NexarClient,
    NexarPart,
)

SECRET = "super-secret-value-9876"


def _part_response(mpn="LM358N", datasheet="https://ti.com/lm358.pdf"):
    return {
        "data": {
            "supSearchMpn": {
                "results": [
                    {
                        "part": {
                            "mpn": mpn,
                            "manufacturer": {"name": "Texas Instruments"},
                            "bestDatasheet": {"url": datasheet},
                            "category": {"path": "ICs / Linear / Amplifiers"},
                            "specs": [
                                {"attribute": {"name": "Lifecycle Status"}, "displayValue": "Active"}
                            ],
                        }
                    }
                ]
            }
        }
    }


class FakeTransport:
    """Records calls; serves token then GraphQL responses."""

    def __init__(self, graphql_response, *, auth_status=200):
        self.calls = []
        self._graphql = graphql_response
        self._auth_status = auth_status

    def __call__(self, url, *, data=None, json_body=None, headers=None):
        self.calls.append(url)
        if url == nexar.IDENTITY_URL:
            if self._auth_status == 401:
                raise NexarAuthError("auth failed against https://identity.nexar.com")
            return {"access_token": "tok-abc-123", "expires_in": 3600}
        return self._graphql


def _client(transport, secret=SECRET):
    return NexarClient(client_id="cid", client_secret=secret, transport=transport)


# ---------------------------------------------------------------------------
# successful auth + lookup


def test_lookup_returns_nexar_part():
    t = FakeTransport(_part_response())
    part = _client(t).lookup_mpn("LM358N")
    assert isinstance(part, NexarPart)
    assert part.manufacturer == "Texas Instruments"
    assert part.datasheet_url.endswith("lm358.pdf")
    assert "Amplifiers" in part.category_path
    assert part.lifecycle_status == "Active"


def test_junk_mpn_returns_none():
    empty = {"data": {"supSearchMpn": {"results": []}}}
    assert _client(FakeTransport(empty)).lookup_mpn("XYZJUNK999") is None


# ---------------------------------------------------------------------------
# token caching


def test_token_cached_across_lookups():
    t = FakeTransport(_part_response())
    c = _client(t)
    c.lookup_mpn("LM358N")
    c.lookup_mpn("LM358N")
    # Identity endpoint hit exactly once across two lookups.
    assert t.calls.count(nexar.IDENTITY_URL) == 1


# ---------------------------------------------------------------------------
# disabled / missing credentials


def test_missing_client_id_raises_disabled(monkeypatch):
    monkeypatch.delenv("PL_NEXAR_CLIENT_ID", raising=False)
    monkeypatch.delenv("PL_NEXAR_CLIENT_SECRET", raising=False)
    c = NexarClient()
    assert c.enabled is False
    with pytest.raises(EnrichmentDisabledError):
        c.lookup_mpn("LM358N")


# ---------------------------------------------------------------------------
# auth failure redaction


def test_401_is_redacted():
    t = FakeTransport(_part_response(), auth_status=401)
    with pytest.raises(NexarAuthError) as exc:
        _client(t).lookup_mpn("LM358N")
    msg = str(exc.value)
    assert SECRET not in msg
    assert "9876" not in msg
    assert "auth failed against https://identity.nexar.com" == msg


def test_redact_helper_scrubs_secret_and_token():
    out = nexar._redact(f"failed with {SECRET} and Bearer tok-xyz", SECRET)
    assert SECRET not in out
    assert "tok-xyz" not in out
