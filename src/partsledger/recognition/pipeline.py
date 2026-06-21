"""Recognition pipeline — TASK-041 (classify) + TASK-043 (run).

This module is built in two passes:

- TASK-041 (IDEA-007 Stage 2): :func:`classify` — a read-only banded
  classifier. Given an image (or a precomputed embedding) it returns a
  :class:`Verdict` of ``band`` + ``top1_candidate`` + ``neighbour_labels``.
  No VLM, no MD writes.
- TASK-043 (IDEA-007 Stage 4): :func:`run` — the full glue that turns a
  capture into an inventory side-effect, routing through the VLM, the
  ``INVENTORY.md`` writer, and the enrichment hand-off.

Both entry points are built on injected seams (``cache``, ``embed_fn``,
``vlm``, ``writer``, ``enrich``) so the routing logic is unit-testable with
fakes — no torch backbone, no camera, no network.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Sequence

try:  # py3.11+
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]

__all__ = [
    "Band",
    "Thresholds",
    "Verdict",
    "load_thresholds",
    "classify_vector",
    "classify",
]

Band = Literal["tight", "tight_ambiguous", "medium", "miss"]

CONFIG_PATH_ENV = "PL_CONFIG_PATH"

# IDEA-007 § Confidence bands — placeholder defaults; overridable per-maker
# via the [recognition] section of ~/.config/partsledger/config.toml.
DEFAULT_TIGHT_DISTANCE = 0.10
DEFAULT_MEDIUM_DISTANCE = 0.25


@dataclass(frozen=True)
class Thresholds:
    """Cosine-distance band boundaries (smaller = closer match)."""

    tight: float = DEFAULT_TIGHT_DISTANCE
    medium: float = DEFAULT_MEDIUM_DISTANCE


@dataclass(frozen=True)
class Verdict:
    """Outcome of :func:`classify` — pure recognition, no side-effects."""

    band: Band
    top1_candidate: str | None
    neighbour_labels: list[str] = field(default_factory=list)


def _config_path() -> Path:
    override = os.environ.get(CONFIG_PATH_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "partsledger" / "config.toml"


def load_thresholds(*, config_path: Path | None = None) -> Thresholds:
    """Read ``[recognition]`` thresholds from config, else documented defaults."""
    path = config_path or _config_path()
    if not path.is_file():
        return Thresholds()
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    rec = data.get("recognition") or {}
    return Thresholds(
        tight=float(rec.get("tight_distance", DEFAULT_TIGHT_DISTANCE)),
        medium=float(rec.get("medium_distance", DEFAULT_MEDIUM_DISTANCE)),
    )


def _distinct_in_order(labels: Sequence[str]) -> list[str]:
    seen: dict[str, None] = {}
    for lab in labels:
        seen.setdefault(lab, None)
    return list(seen)


def classify_vector(vector: Sequence[float], cache: Any, *, thresholds: Thresholds | None = None) -> Verdict:
    """Band a precomputed embedding against ``cache``.

    ``cache`` only needs a ``nearest(vector, k) -> [Neighbour]`` method, so
    a real :class:`~partsledger.recognition.cache.EmbeddingCache` or a stub
    both work. Banding per IDEA-007 § Confidence bands:

    - ``tight`` — nearest distance ``< tight`` and a single distinct label
      inside the tight neighbourhood.
    - ``tight_ambiguous`` — nearest distance ``< tight`` but more than one
      distinct label sits inside the tight threshold (the LM358N-vs-LM358P
      collision); VLM disambiguation is required downstream.
    - ``medium`` — ``tight <= distance < medium``; VLM mandatory, no
      auto-pick.
    - ``miss`` — ``distance >= medium`` or empty cache.
    """
    th = thresholds or load_thresholds()
    neighbours = list(cache.nearest(vector, k=3))
    if not neighbours:
        return Verdict(band="miss", top1_candidate=None, neighbour_labels=[])

    nearest = neighbours[0]
    all_labels = _distinct_in_order([n.label for n in neighbours])
    top1 = nearest.label

    if nearest.distance < th.tight:
        tight_labels = _distinct_in_order(
            [n.label for n in neighbours if n.distance < th.tight]
        )
        band: Band = "tight_ambiguous" if len(tight_labels) > 1 else "tight"
    elif nearest.distance < th.medium:
        band = "medium"
    else:
        band = "miss"

    return Verdict(band=band, top1_candidate=top1, neighbour_labels=all_labels)


def classify(
    image: Any,
    *,
    cache: Any = None,
    embed_fn: Callable[[Any], Any] | None = None,
    thresholds: Thresholds | None = None,
) -> Verdict:
    """Embed ``image`` and band it against the cache.

    ``cache`` and ``embed_fn`` are injected; by default the canonical
    :class:`EmbeddingCache` and :func:`partsledger.recognition.embed.embed`
    are used. Tests inject both to stay backbone- and image-free.
    """
    if embed_fn is None:
        from . import embed as embed_mod

        embed_fn = embed_mod.embed
    if cache is None:
        from . import embed as embed_mod
        from .cache import EmbeddingCache

        cache = EmbeddingCache(embed_mod.model_hash())
    vector = embed_fn(image)
    return classify_vector(vector, cache, thresholds=thresholds)
