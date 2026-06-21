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

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Sequence

from .hints import GENERIC_FAMILY, GENERIC_HINT
from .vlm import HedgedID, NeedsReframe, NoIdea

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
    "Wrote",
    "Reframing",
    "EscalatedToManual",
    "Outcome",
    "WriteEntry",
    "Pipeline",
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


# ===========================================================================
# TASK-043 — full pipeline glue: run(image) -> Outcome
# ===========================================================================


@dataclass(frozen=True)
class Wrote:
    """Silent qty++ happened; a cache row was inserted.

    ``source`` is ``"cache"`` (tight DINOv2 hit) or ``"vlm"`` (the
    viewfinder annotates the confirmation flash *via VLM* in the latter
    case).
    """

    label: str
    source: Literal["cache", "vlm"]


@dataclass(frozen=True)
class Reframing:
    """Viewfinder shows the *R retry / X abort* prompt with ``hint``."""

    hint: str
    family: str = GENERIC_FAMILY


@dataclass(frozen=True)
class EscalatedToManual:
    """Hand off to ``/inventory-add``; no write, no cache row."""


Outcome = "Wrote | Reframing | EscalatedToManual"


@dataclass(frozen=True)
class WriteEntry:
    """The undo-journal payload handed off after every successful write."""

    part_id: str
    qty_before: int
    qty_after: int
    cache_row_id: int
    source: str
    label: str


def _part_id_of(label: str) -> str:
    """Normalise a VLM/cache label into an inventory ``part_id`` token."""
    return label.strip()


def _image_hash_of(vector: Sequence[float]) -> str:
    import numpy as np

    arr = np.asarray(vector, dtype=np.float32).reshape(-1)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    import numpy as np

    va = np.asarray(a, dtype=np.float32).reshape(-1)
    vb = np.asarray(b, dtype=np.float32).reshape(-1)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na == 0.0 or nb == 0.0:
        return 1.0
    return 1.0 - float((va / na) @ (vb / nb))


class Pipeline:
    """Stateful camera-path glue — IDEA-007 Stage 4 (TASK-043).

    Owns the re-frame loop (IDEA-006 stays loop-less): up to ``max_reframes``
    re-frame prompts per physical part before the abort path triggers
    automatically. The counter resets when a physically distinct part shows
    up (embedding distance ``>= distinct_distance``) or after any part
    resolves.

    All five upstream collaborators are injected:

    - ``cache`` — :class:`~partsledger.recognition.cache.EmbeddingCache`-like
      (``nearest``, ``insert``).
    - ``vlm_identify`` — ``identify(image, neighbour_hints)`` (TASK-042).
    - ``writer_upsert`` — the ``INVENTORY.md`` writer (TASK-016); lint runs
      pre-flush inside it (TASK-017).
    - ``enrich`` — best-effort enrichment hand-off (TASK-048); failures never
      roll back the write.
    - ``journal`` — optional undo journal (TASK-044) with a ``record(entry)``
      method.
    """

    def __init__(
        self,
        *,
        cache: Any,
        vlm_identify: Callable[..., Any],
        writer_upsert: Callable[..., Any],
        enrich: Callable[[str], Any] | None = None,
        journal: Any | None = None,
        embed_fn: Callable[[Any], Any] | None = None,
        thresholds: Thresholds | None = None,
        max_reframes: int = 2,
        distinct_distance: float | None = None,
    ) -> None:
        self._cache = cache
        self._vlm_identify = vlm_identify
        self._writer_upsert = writer_upsert
        self._enrich = enrich
        self._journal = journal
        self._embed_fn = embed_fn
        self._thresholds = thresholds or load_thresholds()
        self._max_reframes = max_reframes
        self._distinct_distance = (
            distinct_distance if distinct_distance is not None else self._thresholds.medium
        )
        self._reframe_count = 0
        self._last_vector: Any | None = None

    # -- public ------------------------------------------------------------

    def run(self, image: Any) -> Any:
        """Turn one capture into an :data:`Outcome`."""
        vector = self._embed(image)
        self._maybe_reset_for_distinct_part(vector)

        verdict = classify_vector(vector, self._cache, thresholds=self._thresholds)
        if verdict.band == "tight":
            return self._commit(verdict.top1_candidate, "cache", vector, marking=None)
        if verdict.band == "medium":
            return self._reframe(GENERIC_HINT, GENERIC_FAMILY, vector)
        # tight_ambiguous and miss both go to the VLM.
        return self._via_vlm(image, vector, verdict.neighbour_labels)

    # -- internals ---------------------------------------------------------

    def _embed(self, image: Any) -> Any:
        if self._embed_fn is not None:
            return self._embed_fn(image)
        from . import embed as embed_mod

        return embed_mod.embed(image)

    def _maybe_reset_for_distinct_part(self, vector: Any) -> None:
        if self._last_vector is None:
            return
        if _cosine_distance(vector, self._last_vector) >= self._distinct_distance:
            self._reframe_count = 0

    def _via_vlm(self, image: Any, vector: Any, neighbour_labels: list[str]) -> Any:
        verdict = self._vlm_identify(image, neighbour_labels)
        if isinstance(verdict, HedgedID):
            return self._commit(verdict.label, "vlm", vector, marking=verdict.marking)
        if isinstance(verdict, NeedsReframe):
            return self._reframe(verdict.hint, verdict.family, vector)
        assert isinstance(verdict, NoIdea)
        return self._escalate()

    def _reframe(self, hint: str, family: str, vector: Any) -> Any:
        if self._reframe_count >= self._max_reframes:
            return self._escalate()
        self._reframe_count += 1
        self._last_vector = vector
        return Reframing(hint=hint, family=family)

    def _escalate(self) -> Any:
        self._reset()
        return EscalatedToManual()

    def _reset(self) -> None:
        self._reframe_count = 0
        self._last_vector = None

    def _commit(self, label: str | None, source: str, vector: Any, *, marking: str | None) -> Any:
        assert label is not None
        part_id = _part_id_of(label)

        # MD write first. A writer failure aborts BEFORE cache-learn so the
        # cache and inventory can never diverge (TASK-016/017 contract).
        result = self._writer_upsert(part_id, 1, source=source)
        qty_after = int(getattr(result, "qty", 1))

        # Cache-learn — only after the write landed.
        row_id = self._cache.insert(vector, part_id, marking, _image_hash_of(vector))

        # Undo-journal hand-off (TASK-044), best-effort.
        if self._journal is not None:
            self._journal.record(
                WriteEntry(
                    part_id=part_id,
                    qty_before=qty_after - 1,
                    qty_after=qty_after,
                    cache_row_id=row_id,
                    source=source,
                    label=label,
                )
            )

        # Best-effort enrichment hand-off — never rolls back the write.
        if self._enrich is not None:
            try:
                self._enrich(part_id)
            except Exception:
                pass

        self._reset()
        return Wrote(label=part_id, source=source)  # type: ignore[arg-type]
