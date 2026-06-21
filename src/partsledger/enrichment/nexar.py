"""Nexar GraphQL adapter — TASK-045 (IDEA-008 Stage 1).

Bare HTTP/GraphQL transport against the Nexar (Octopart) API in isolation:
OAuth client-credentials against the identity endpoint, an in-session bearer
cache, then a single ``supSearchMpn`` GraphQL query parsed into a
:class:`NexarPart`. No caching, no orchestrator, no writer wiring — those
are TASK-046 / TASK-048.

Credentials come from ``$PL_NEXAR_CLIENT_ID`` / ``$PL_NEXAR_CLIENT_SECRET``
(never typed inline). Secrets discipline mirrors the VLM adapter: the bearer
token and client secret are redacted in every log line, error, and
traceback. A failed auth reports ``"auth failed against
https://identity.nexar.com"`` — never the credential value.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Callable

__all__ = [
    "NexarPart",
    "NexarClient",
    "EnrichmentDisabledError",
    "NexarError",
    "NexarAuthError",
    "IDENTITY_URL",
    "API_URL",
]

IDENTITY_URL = "https://identity.nexar.com/connect/token"
API_URL = "https://api.nexar.com/graphql"

CLIENT_ID_ENV = "PL_NEXAR_CLIENT_ID"
CLIENT_SECRET_ENV = "PL_NEXAR_CLIENT_SECRET"

# Exactly the fields from IDEA-008's *Primary path* table. bestImage is
# deliberately NOT queried (IDEA-008 closed *Image upload* question).
_SUP_SEARCH_QUERY = """
query supSearchMpn($q: String!) {
  supSearchMpn(q: $q, limit: 1) {
    results {
      part {
        mpn
        manufacturer { name }
        bestDatasheet { url }
        category { path }
        specs { attribute { name } displayValue }
      }
    }
  }
}
""".strip()


@dataclass(frozen=True)
class NexarPart:
    mpn: str
    manufacturer: str | None
    datasheet_url: str | None
    category_path: str | None
    lifecycle_status: str | None


class EnrichmentDisabledError(RuntimeError):
    """Nexar credentials are not configured — enrichment is unavailable.

    Callers ``except`` this to take the offline path without parsing a
    traceback.
    """


class NexarError(RuntimeError):
    """Transport or protocol error talking to Nexar."""


class NexarAuthError(NexarError):
    """Authentication failed — never carries the client secret or token."""


def _redact(text: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***REDACTED***")
    return re.sub(
        r"(Bearer\s+|access_token\"?\s*[:=]\s*\"?)\S+",
        r"\1***REDACTED***",
        text,
    )


def _lifecycle_from_specs(specs: list[dict]) -> str | None:
    for spec in specs or []:
        attr = (spec.get("attribute") or {}).get("name", "")
        if attr and attr.lower() in ("lifecycle status", "lifecycle"):
            return spec.get("displayValue")
    return None


class NexarClient:
    """Session-scoped Nexar client with an in-memory bearer cache."""

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        transport: Callable[..., Any] | None = None,
    ) -> None:
        self._client_id = client_id if client_id is not None else os.environ.get(CLIENT_ID_ENV, "")
        self._client_secret = (
            client_secret if client_secret is not None else os.environ.get(CLIENT_SECRET_ENV, "")
        )
        self._transport = transport  # injected (url, *, data/json, headers) -> dict
        self._token: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._client_id and self._client_secret)

    # -- transport ---------------------------------------------------------

    def _post(self, url: str, *, data: dict | None = None, json_body: dict | None = None, headers: dict | None = None) -> dict:
        if self._transport is not None:
            return self._transport(url, data=data, json_body=json_body, headers=headers)
        import requests  # local import keeps module cheap

        resp = requests.post(url, data=data, json=json_body, headers=headers, timeout=30)
        status = getattr(resp, "status_code", 200)
        if status == 401:
            raise NexarAuthError(f"auth failed against {IDENTITY_URL.rsplit('/', 2)[0]}")
        if status >= 400:
            raise NexarError(_redact(f"Nexar HTTP {status}", self._client_secret))
        return resp.json()

    # -- auth --------------------------------------------------------------

    def _ensure_token(self) -> str:
        if self._token is not None:
            return self._token
        if not self.enabled:
            raise EnrichmentDisabledError(
                f"{CLIENT_ID_ENV} / {CLIENT_SECRET_ENV} not set — Nexar enrichment disabled"
            )
        try:
            payload = self._post(
                IDENTITY_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except NexarAuthError:
            raise NexarAuthError("auth failed against https://identity.nexar.com") from None
        token = payload.get("access_token")
        if not token:
            raise NexarAuthError("auth failed against https://identity.nexar.com")
        self._token = token
        return token

    # -- lookup ------------------------------------------------------------

    def lookup_mpn(self, mpn: str) -> NexarPart | None:
        """Return a :class:`NexarPart` for ``mpn``, or ``None`` if not found.

        Raises :class:`EnrichmentDisabledError` when credentials are unset.
        The bearer token is fetched once and reused across calls.
        """
        token = self._ensure_token()
        response = self._post(
            API_URL,
            json_body={"query": _SUP_SEARCH_QUERY, "variables": {"q": mpn}},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            results = response["data"]["supSearchMpn"]["results"]
        except (KeyError, TypeError):
            return None
        if not results:
            return None
        part = results[0].get("part") or {}
        if not part.get("mpn"):
            return None
        manufacturer = (part.get("manufacturer") or {}).get("name")
        datasheet_url = (part.get("bestDatasheet") or {}).get("url")
        category_path = (part.get("category") or {}).get("path")
        if isinstance(category_path, list):
            category_path = " / ".join(str(p) for p in category_path)
        lifecycle = _lifecycle_from_specs(part.get("specs") or [])
        return NexarPart(
            mpn=part["mpn"],
            manufacturer=manufacturer,
            datasheet_url=datasheet_url,
            category_path=category_path,
            lifecycle_status=lifecycle,
        )
