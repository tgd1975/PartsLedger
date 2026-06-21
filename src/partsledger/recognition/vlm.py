"""VLM adapter — TASK-042 (IDEA-007 Stage 3).

A single OpenAI-compatible REST adapter that speaks to whatever VLM endpoint
``$PL_VLM_BASE_URL`` resolves to. Default is Claude Opus Vision via the
Anthropic API; the same code talks to Pixtral via Mistral / Ollama / vLLM
with an env-var swap and no code change — the OpenAI ``/chat/completions``
shape is the only transport. **No vendor SDK** is imported.

``identify(image, neighbour_hints=None)`` returns one of three structured
verdicts (IDEA-007 § Where the VLM still earns its keep):

- :class:`HedgedID` — single-best identification, hedge phrasing enforced.
- :class:`NeedsReframe` — reframe required; the hint is tokenised into one
  of the seven IDEA-006 hint families (or the generic fallback).
- :class:`NoIdea` — genuine cold-start; no retry.

Guarantees:

1. **Structured output** — requests a JSON-schema ``response_format``; falls
   back to a tolerant JSON-substring parser when the provider ignores it.
2. **Hedge grammar** — an identification must lead with a hedging adverb
   (``likely`` / ``probably`` / ``appears to be`` / …) and must not contain
   the forbidden modals ``must`` / ``always`` / ``never``. A violation
   triggers a retry; after the cap the verdict collapses to :class:`NoIdea`.
3. **Secrets redaction** — ``$PL_VLM_API_KEY`` is never logged, echoed at
   startup, or leaked in an error / traceback. A failed auth is reported as
   ``"auth failed against <base_url>"``.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable

from .hints import GENERIC_HINT, classify_hint

__all__ = [
    "HedgedID",
    "NeedsReframe",
    "NoIdea",
    "VLMVerdict",
    "VLMConfig",
    "VLMError",
    "VLMAuthError",
    "load_config",
    "identify",
    "HEDGE_ADVERBS",
    "FORBIDDEN_MODALS",
]

# Hedge grammar (IDEA-007 § Hedge-language enforcement).
HEDGE_ADVERBS = ("likely", "probably", "appears to be", "possibly", "may be", "looks like")
FORBIDDEN_MODALS = ("must", "always", "never")
_FORBIDDEN_RE = re.compile(r"\b(must|always|never)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Verdict variants


@dataclass(frozen=True)
class HedgedID:
    label: str
    marking: str | None
    hedge: str


@dataclass(frozen=True)
class NeedsReframe:
    hint: str
    family: str


@dataclass(frozen=True)
class NoIdea:
    pass


VLMVerdict = "HedgedID | NeedsReframe | NoIdea"


# ---------------------------------------------------------------------------
# Errors


class VLMError(RuntimeError):
    """Transport or protocol error talking to the VLM endpoint."""


class VLMAuthError(VLMError):
    """Authentication failed — never carries the bearer token."""


# ---------------------------------------------------------------------------
# Config


@dataclass(frozen=True)
class VLMConfig:
    base_url: str
    model: str
    api_key: str = ""

    def describe_secret(self) -> str:
        """Verbose-mode safe: presence + length only, never the value."""
        if not self.api_key:
            return "PL_VLM_API_KEY: (unset)"
        return f"PL_VLM_API_KEY: set (len={len(self.api_key)})"


def load_config() -> VLMConfig:
    """Read the three ``$PL_VLM_*`` env vars. No other env is consulted."""
    return VLMConfig(
        base_url=os.environ.get("PL_VLM_BASE_URL", "").rstrip("/"),
        model=os.environ.get("PL_VLM_MODEL", ""),
        api_key=os.environ.get("PL_VLM_API_KEY", ""),
    )


def _redact(text: str, secret: str) -> str:
    if secret:
        text = text.replace(secret, "***REDACTED***")
    # Defensive: scrub anything that looks like a bearer token.
    return re.sub(r"sk-[A-Za-z0-9_\-]+", "***REDACTED***", text)


# ---------------------------------------------------------------------------
# JSON-schema request shape (best-effort; providers that ignore it still parse)

_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "part_verdict",
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["identified", "needs_reframe", "no_idea"]},
                "label": {"type": "string"},
                "marking": {"type": "string"},
                "hedge": {"type": "string"},
                "hint": {"type": "string"},
            },
            "required": ["verdict"],
        },
    },
}

_SYSTEM_PROMPT = (
    "You identify a single electronic component from one photo. Respond ONLY "
    "with JSON matching the schema. If you can identify it, set verdict to "
    "'identified' and lead the 'hedge' field with a hedging adverb (likely, "
    "probably, appears to be); never use must/always/never. If the photo is "
    "unusable, set verdict to 'needs_reframe' and put a short re-frame hint in "
    "'hint'. If you genuinely cannot tell, set verdict to 'no_idea'."
)


def _encode_image_default(image: Any) -> str:
    """BGR ``np.ndarray`` → base64 PNG. Lazy heavy imports."""
    import base64

    import cv2  # type: ignore[import-not-found]

    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise VLMError("failed to PNG-encode the capture for the VLM request")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _build_payload(
    image: Any,
    config: VLMConfig,
    neighbour_hints: list[str] | None,
    encode_image: Callable[[Any], str],
) -> dict:
    b64 = encode_image(image)
    user_text = "Identify this component."
    if neighbour_hints:
        user_text += " Cache near-neighbours suggest it may be one of: " + ", ".join(
            neighbour_hints
        )
    return {
        "model": config.model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            },
        ],
        "response_format": _RESPONSE_SCHEMA,
        "max_tokens": 512,
    }


def _default_transport(payload: dict, config: VLMConfig, *, requests_mod: Any = None) -> dict:
    """POST to ``{base_url}/chat/completions``; return parsed JSON.

    Auth failures are re-raised redacted. The bearer token never appears in
    any raised message.
    """
    if requests_mod is None:
        import requests as requests_mod  # local import keeps module cheap

    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    url = f"{config.base_url}/chat/completions"
    try:
        resp = requests_mod.post(url, headers=headers, json=payload, timeout=60)
    except Exception as exc:  # transport-level failure
        raise VLMError(_redact(f"VLM request failed: {exc}", config.api_key)) from None
    status = getattr(resp, "status_code", 200)
    if status == 401:
        raise VLMAuthError(f"auth failed against {config.base_url}")
    if status >= 400:
        raise VLMError(_redact(f"VLM HTTP {status} from {config.base_url}", config.api_key))
    return resp.json()


# ---------------------------------------------------------------------------
# Response parsing


def _extract_content(response: dict) -> str:
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise VLMError("VLM response missing choices[0].message.content") from None


def _parse_json_lenient(content: str) -> dict | None:
    """Parse strict JSON, else extract the first ``{...}`` block (fallback)."""
    content = content.strip()
    try:
        obj = json.loads(content)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _hedge_ok(hedge: str, label: str, marking: str | None) -> bool:
    low = (hedge or "").strip().lower()
    if not any(low.startswith(adv) for adv in HEDGE_ADVERBS):
        return False
    blob = " ".join(filter(None, [hedge, label, marking or ""]))
    if _FORBIDDEN_RE.search(blob):
        return False
    return True


def _interpret(obj: dict) -> tuple[str, Any]:
    """Map a parsed verdict dict to ('return'|'retry', payload)."""
    verdict = str(obj.get("verdict", "")).strip().lower()
    if verdict == "needs_reframe":
        hint = str(obj.get("hint") or "").strip() or GENERIC_HINT
        family = classify_hint(hint)
        if family == "generic":
            hint = GENERIC_HINT
        return "return", NeedsReframe(hint=hint, family=family)
    if verdict == "no_idea":
        return "return", NoIdea()
    if verdict == "identified":
        label = str(obj.get("label") or "").strip()
        marking = obj.get("marking")
        marking = str(marking).strip() if marking else None
        hedge = str(obj.get("hedge") or "").strip()
        if label and _hedge_ok(hedge, label, marking):
            return "return", HedgedID(label=label, marking=marking, hedge=hedge)
        return "retry", None  # hedge grammar / missing label → retry
    return "retry", None  # unknown / malformed → retry


# ---------------------------------------------------------------------------
# Public entry point


def identify(
    image: Any,
    neighbour_hints: list[str] | None = None,
    *,
    config: VLMConfig | None = None,
    transport: Callable[[dict, VLMConfig], dict] | None = None,
    encode_image: Callable[[Any], str] | None = None,
    max_retries: int = 2,
) -> Any:
    """Identify the component in ``image`` via the configured VLM.

    Returns a :class:`HedgedID`, :class:`NeedsReframe`, or :class:`NoIdea`.
    ``transport`` and ``encode_image`` are injected seams so the parsing /
    retry / redaction logic is unit-tested without a live endpoint.
    """
    cfg = config or load_config()
    send = transport or _default_transport
    enc = encode_image or _encode_image_default

    payload = _build_payload(image, cfg, neighbour_hints, enc)
    last_reason = "no response"
    for _ in range(max_retries + 1):
        response = send(payload, cfg)
        content = _extract_content(response)
        obj = _parse_json_lenient(content)
        if obj is None:
            last_reason = "unparseable response"
            continue
        action, result = _interpret(obj)
        if action == "return":
            return result
        last_reason = "hedge-grammar or schema violation"
    # Retries exhausted on malformed / hedge-failing identifications.
    del last_reason
    return NoIdea()
