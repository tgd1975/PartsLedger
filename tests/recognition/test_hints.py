"""Tests for partsledger.recognition.hints — hint-family tokeniser."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import pytest  # noqa: E402

from partsledger.recognition import hints  # noqa: E402


@pytest.mark.parametrize(
    "text,family",
    [
        ("rotate 90°", "angle"),
        ("tilt up so the marking is visible", "angle"),
        ("too dark", "lighting"),
        ("glare on the marking", "lighting"),
        ("image too blurry", "sharpness"),
        ("out of focus", "sharpness"),
        ("part is off-centre", "framing"),
        ("two parts in shot — show one", "framing"),
        ("reflective surface — try a matte mat", "surface"),
        ("too close", "distance"),
        ("too far away", "distance"),
        ("marking worn — try a different side", "marking"),
    ],
)
def test_known_families(text, family):
    assert hints.classify_hint(text) == family


def test_unknown_collapses_to_generic():
    assert hints.classify_hint("purple monkey dishwasher") == hints.GENERIC_FAMILY


def test_empty_is_generic():
    assert hints.classify_hint("") == hints.GENERIC_FAMILY
    assert hints.classify_hint("   ") == hints.GENERIC_FAMILY


def test_seven_families_exact():
    assert len(hints.HINT_FAMILIES) == 7
