"""Tests for partsledger.recognition.vlm — TASK-042.

The HTTP transport and image encoding are injected, so the verdict parsing,
hedge-grammar retry loop, and secrets-redaction logic run with no live
endpoint and no cv2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.recognition import vlm  # noqa: E402
from partsledger.recognition.vlm import (  # noqa: E402
    HedgedID,
    NeedsReframe,
    NoIdea,
    VLMAuthError,
    VLMConfig,
)

CFG = VLMConfig(base_url="https://api.example/v1", model="test-model", api_key="sk-secret-12345")


def NO_ENC(img):  # noqa: N802 — test stub for the image encoder seam
    return "BASE64DATA"


def _resp(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def _transport_returning(*contents):
    """Transport that yields the given response contents in order."""
    calls = {"n": 0}

    def transport(payload, config):
        i = min(calls["n"], len(contents) - 1)
        calls["n"] += 1
        return _resp(contents[i])

    transport.calls = calls  # type: ignore[attr-defined]
    return transport


# ---------------------------------------------------------------------------
# Three verdict variants


def test_hedged_id_parsed():
    t = _transport_returning(
        json.dumps({"verdict": "identified", "label": "LM358N", "marking": "LM358N", "hedge": "likely"})
    )
    v = vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC)
    assert isinstance(v, HedgedID)
    assert v.label == "LM358N"
    assert v.hedge == "likely"


def test_needs_reframe_parsed_and_tokenised():
    t = _transport_returning(json.dumps({"verdict": "needs_reframe", "hint": "glare on the marking"}))
    v = vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC)
    assert isinstance(v, NeedsReframe)
    assert v.family == "lighting"
    assert v.hint == "glare on the marking"


def test_no_idea_parsed():
    t = _transport_returning(json.dumps({"verdict": "no_idea"}))
    v = vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC)
    assert isinstance(v, NoIdea)


def test_needs_reframe_unknown_hint_collapses_to_generic():
    t = _transport_returning(json.dumps({"verdict": "needs_reframe", "hint": "abcdef nonsense"}))
    v = vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC)
    assert isinstance(v, NeedsReframe)
    assert v.family == "generic"
    assert v.hint == vlm.GENERIC_HINT


# ---------------------------------------------------------------------------
# Hedge grammar + retry cap


def test_missing_hedge_retries_then_no_idea():
    # Identification with no hedging adverb on every attempt.
    bad = json.dumps({"verdict": "identified", "label": "LM358N", "hedge": "it is the LM358N"})
    t = _transport_returning(bad)
    v = vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC, max_retries=2)
    assert isinstance(v, NoIdea)
    assert t.calls["n"] == 3  # initial + 2 retries


def test_forbidden_modal_rejected():
    bad = json.dumps({"verdict": "identified", "label": "LM358N", "hedge": "must be LM358N"})
    t = _transport_returning(bad)
    v = vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC, max_retries=1)
    assert isinstance(v, NoIdea)
    assert t.calls["n"] == 2


def test_retry_then_success():
    bad = json.dumps({"verdict": "identified", "label": "X", "hedge": "definitely X"})
    good = json.dumps({"verdict": "identified", "label": "LM358N", "hedge": "probably"})
    t = _transport_returning(bad, good)
    v = vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC, max_retries=2)
    assert isinstance(v, HedgedID)
    assert v.label == "LM358N"


# ---------------------------------------------------------------------------
# Structured path vs lenient fallback parser


def test_structured_json_path():
    t = _transport_returning(json.dumps({"verdict": "no_idea"}))
    assert isinstance(vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC), NoIdea)


def test_lenient_parser_extracts_embedded_json():
    prose = 'Sure! Here you go: {"verdict": "no_idea"} — hope that helps.'
    t = _transport_returning(prose)
    assert isinstance(vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC), NoIdea)


def test_unparseable_response_retries_to_no_idea():
    t = _transport_returning("not json at all")
    v = vlm.identify(object(), config=CFG, transport=t, encode_image=NO_ENC, max_retries=1)
    assert isinstance(v, NoIdea)
    assert t.calls["n"] == 2


# ---------------------------------------------------------------------------
# Secrets redaction


class _FakeResp:
    def __init__(self, status):
        self.status_code = status

    def json(self):
        return {}


class _FakeRequests:
    def __init__(self, status):
        self._status = status
        self.seen = {}

    def post(self, url, headers=None, json=None, timeout=None):
        self.seen["headers"] = headers
        return _FakeResp(self._status)


def test_401_redacts_bearer_token():
    payload = {"model": "m"}
    fake = _FakeRequests(401)
    with pytest.raises(VLMAuthError) as exc:
        vlm._default_transport(payload, CFG, requests_mod=fake)
    msg = str(exc.value)
    assert "sk-secret" not in msg
    assert "12345" not in msg
    assert "auth failed against https://api.example/v1" == msg


def test_non_200_error_redacts_key():
    fake = _FakeRequests(500)
    with pytest.raises(vlm.VLMError) as exc:
        vlm._default_transport({"model": "m"}, CFG, requests_mod=fake)
    assert "sk-secret-12345" not in str(exc.value)


def test_describe_secret_hides_value():
    desc = CFG.describe_secret()
    assert "sk-secret-12345" not in desc
    assert "len=15" in desc


def test_unset_key_describe():
    cfg = VLMConfig(base_url="x", model="m", api_key="")
    assert "unset" in cfg.describe_secret()


# ---------------------------------------------------------------------------
# No vendor SDK in the module


def test_no_vendor_sdk_imported():
    src = Path(vlm.__file__).read_text(encoding="utf-8")
    for vendor in ("import anthropic", "import mistralai", "from anthropic", "from mistralai", "import openai"):
        assert vendor not in src
