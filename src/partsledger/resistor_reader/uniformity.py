"""Batch uniformity check — TASK-053 (IDEA-011 Motivation #2).

Given the decoded results for N resistors the maker believes are all the same
value, report whether the batch is uniform and, if mixed, list every
deviation with its frame position. The check is **strict**: clustering is on
the raw decoded value with no confidence weighting and no averaging — a
low-confidence outlier is itself a reason to surface it (re-shoot / inspect),
not a reason to discount it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Deviation", "UniformityReport", "check_uniformity"]


@dataclass(frozen=True)
class Deviation:
    value: str
    position: tuple[int, int]
    confidence: float
    bands: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class UniformityReport:
    modal_value: str
    uniform: bool
    deviations: list[Deviation] = field(default_factory=list)
    count: int = 0


def check_uniformity(
    decoded: list[Any],
    positions: list[tuple[int, int]] | None = None,
) -> UniformityReport:
    """Cluster ``decoded`` on raw value; flag every off-modal resistor.

    ``decoded`` is a list of :class:`~partsledger.resistor_reader.decode.DecodedResistor`.
    ``positions`` (bbox centres, parallel to ``decoded``) annotate each
    deviation; when omitted, positions default to ``(-1, -1)``.
    """
    if not decoded:
        return UniformityReport(modal_value="", uniform=True, deviations=[], count=0)

    positions = positions or [(-1, -1)] * len(decoded)
    values = [d.value for d in decoded]
    # Strict clustering: most common raw value is the mode. Ties resolve to
    # the first-seen value (Counter.most_common is insertion-stable in 3.7+).
    modal_value = Counter(values).most_common(1)[0][0]

    deviations = [
        Deviation(
            value=d.value,
            position=positions[i],
            confidence=getattr(d, "confidence", 0.0),
            bands=list(getattr(d, "bands", [])),
        )
        for i, d in enumerate(decoded)
        if d.value != modal_value
    ]
    return UniformityReport(
        modal_value=modal_value,
        uniform=not deviations,
        deviations=deviations,
        count=len(decoded),
    )
