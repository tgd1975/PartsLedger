"""Metadata enrichment — EPIC-007 (IDEA-008).

Assembles the Nexar transport (TASK-045), the SQLite response cache
(TASK-046), and the static family-datasheet fallback (TASK-047) behind a
single :func:`enrich` entry point, and fills the ``INVENTORY.md`` row's
metadata cells through the TASK-016 writer with a **no-clobber** overlay.

``enrich(part_id) -> EnrichmentResult`` returns either :class:`Enriched`
(payload + cells written) or :class:`NoEnrichment(reason)`. The four soft-
fail reasons are the ones from IDEA-008 § *Failure is not a gate*:
``offline`` / ``network_unreachable`` / ``unknown_mpn`` / ``fallback_missed``.
Enrichment failure is never a gate — the camera path's silent qty++ has
already landed; an empty cell is the only signal that metadata did not.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Callable, Literal

from . import family_datasheets
from .nexar import EnrichmentDisabledError, NexarClient

__all__ = [
    "Enriched",
    "NoEnrichment",
    "EnrichmentResult",
    "NoEnrichmentReason",
    "enrich",
    "build_cells",
]

NoEnrichmentReason = Literal["offline", "network_unreachable", "unknown_mpn", "fallback_missed"]


@dataclass(frozen=True)
class Enriched:
    payload: dict


@dataclass(frozen=True)
class NoEnrichment:
    reason: NoEnrichmentReason


EnrichmentResult = "Enriched | NoEnrichment"


def build_cells(payload: dict) -> dict[str, str]:
    """Map a Nexar/family payload to the INVENTORY.md cells enrichment fills.

    Only Description / Datasheet / Notes — manufacturer lives in the
    response cache (page generation reads it there), never as a column.
    Notes carries the lifecycle only when it is **not** ``Active`` (an
    obsolescence flag is worth surfacing; "Active" is noise).
    """
    cells: dict[str, str] = {}
    category = payload.get("category_path")
    if category:
        cells["Description"] = str(category)
    datasheet = payload.get("datasheet_url")
    if datasheet:
        cells["Datasheet"] = f"[datasheet]({datasheet})"
    lifecycle = payload.get("lifecycle_status")
    if lifecycle and str(lifecycle).strip().lower() != "active":
        cells["Notes"] = str(lifecycle)
    return cells


def _payload_with_datasheet(payload: dict, url: str) -> dict:
    out = dict(payload)
    out["datasheet_url"] = url
    return out


def enrich(
    part_id: str,
    *,
    source: str = "manual",
    client: Any = None,
    cache: Any = None,
    family_lookup: Callable[[str], str | None] | None = None,
    writer_upsert: Callable[..., Any] | None = None,
) -> Any:
    """Enrich ``part_id`` and fill its empty INVENTORY.md metadata cells.

    ``source`` is the row's existing ``Source`` value (``"manual"`` on the
    skill path, ``"camera"`` on the camera path); it is passed to the
    writer so the no-clobber fill never rewrites the provenance column.
    Every collaborator is injectable for testing.
    """
    mpn = part_id.strip()
    family_lookup = family_lookup or family_datasheets.lookup_family
    if cache is None:
        from .cache import NexarCache

        cache = NexarCache()
    if client is None:
        client = NexarClient()
    if writer_upsert is None:
        from ..inventory.writer import upsert_row as writer_upsert

    payload = cache.get(mpn)
    if payload is None:
        # Cache miss → Nexar, then family fallback.
        if not getattr(client, "enabled", True):
            return NoEnrichment("offline")
        try:
            part = client.lookup_mpn(mpn)
        except EnrichmentDisabledError:
            return NoEnrichment("offline")
        except Exception:  # noqa: BLE001 — any transport failure is a soft fail
            return NoEnrichment("network_unreachable")

        if part is None:
            fam = family_lookup(mpn)
            if fam is None:
                return NoEnrichment("unknown_mpn")
            payload = {
                "mpn": mpn,
                "manufacturer": None,
                "datasheet_url": fam,
                "category_path": None,
                "lifecycle_status": None,
            }
        else:
            payload = dataclasses.asdict(part) if dataclasses.is_dataclass(part) else dict(part)
            cache.put(mpn, part, payload.get("lifecycle_status"))
            if not payload.get("datasheet_url"):
                fam = family_lookup(mpn)
                if fam is None:
                    return NoEnrichment("fallback_missed")
                payload = _payload_with_datasheet(payload, fam)

    cells = build_cells(payload)
    if cells:
        writer_upsert(mpn, 0, source=source, cells_if_empty=cells)
    return Enriched(payload)
