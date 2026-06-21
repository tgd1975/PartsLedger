"""Recognition-state hint-family tokeniser — IDEA-006 § Recognition-state hints.

A VLM *needs-re-frame* verdict carries a short free-text hint (``"rotate
90°"``, ``"glare on the marking"``, …). This module tokenises that string
into one of the **seven** families the viewfinder knows how to render, or
collapses it to the generic fallback when no family matches.

Shared by :mod:`partsledger.recognition.vlm` (TASK-042, which tags every
``NeedsReframe`` hint with its family) and the viewfinder overlay state
machine (TASK-036). Pure stdlib — no heavy deps.
"""

from __future__ import annotations

import re

__all__ = [
    "HINT_FAMILIES",
    "GENERIC_FAMILY",
    "GENERIC_HINT",
    "classify_hint",
]

#: The seven families from IDEA-006 § Recognition-state hints, in table order.
HINT_FAMILIES = (
    "angle",
    "lighting",
    "sharpness",
    "framing",
    "surface",
    "distance",
    "marking",
)

GENERIC_FAMILY = "generic"
GENERIC_HINT = "image unclear — recompose and retry"

# Keyword → family. Ordered so that more specific cues win; matched as
# whole-word / substring patterns against the lower-cased hint.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("angle", re.compile(r"rotate|tilt|angle|orient|turn|side view|from the (left|right|top)|°|degree")),
    ("lighting", re.compile(r"too dark|too bright|glare|shadow|lighting|underexposed|overexposed|reflection of light")),
    ("sharpness", re.compile(r"blur|out of focus|focus|sharp|defocus")),
    ("framing", re.compile(r"off.?cent|cut off|cropped|out of frame|two parts|multiple parts|centre|center|reframe the shot")),
    ("surface", re.compile(r"reflective surface|matte mat|background|glossy surface|shiny mat")),
    ("distance", re.compile(r"too close|too far|move (closer|back|away)|zoom|distance")),
    ("marking", re.compile(r"marking|worn|unreadable|illegible|text on the (chip|part|body)|label worn")),
)


def classify_hint(text: str) -> str:
    """Return the family key for ``text``, or :data:`GENERIC_FAMILY`.

    The match is best-effort and order-sensitive: the first family whose
    keyword pattern fires wins. Empty / whitespace input collapses to the
    generic family.
    """
    if not text or not text.strip():
        return GENERIC_FAMILY
    low = text.strip().lower()
    for family, pattern in _PATTERNS:
        if pattern.search(low):
            return family
    return GENERIC_FAMILY
