"""Tests for partsledger.resistor_reader.decode — TASK-052."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

pytest.importorskip("numpy")
cv2 = pytest.importorskip("cv2")
pytest.importorskip("skimage")
pytest.importorskip("scipy")

from partsledger.resistor_reader.decode import decode_resistor, format_value  # noqa: E402
from partsledger.resistor_reader.localise import locate_resistors  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "resistor-reader"


def _decode_top(name):
    img = cv2.imread(str(FIXTURES / f"{name}.png"))
    truth = json.loads((FIXTURES / f"{name}.json").read_text())
    cands = [c for c in locate_resistors(img) if c.confidence > 0.6]
    assert cands, f"no candidate for {name}"
    return decode_resistor(img, cands[0]), truth


# ---------------------------------------------------------------------------
# value decoding matches the ground-truth sidecar


@pytest.mark.parametrize("name", ["single-1k", "single-4k7", "single-220"])
def test_value_matches_ground_truth(name):
    decoded, truth = _decode_top(name)
    assert decoded.value == truth["value"]
    assert decoded.tolerance == truth["tolerance"]


def test_four_band_decode():
    decoded, _ = _decode_top("single-1k")
    assert len(decoded.bands) == 4
    assert decoded.orientation_resolved is True


def test_five_band_decode():
    decoded, _ = _decode_top("single-220")
    assert len(decoded.bands) == 5
    assert decoded.value == "220R"


def test_orientation_ambiguous_reduces_confidence():
    decoded, _ = _decode_top("ambiguous")
    assert decoded.orientation_resolved is False
    # The chosen value is still the higher/forward reading; confidence is
    # reduced relative to an unambiguous decode.
    clean, _ = _decode_top("single-1k")
    assert decoded.confidence < clean.confidence


# ---------------------------------------------------------------------------
# RKM value formatting


@pytest.mark.parametrize(
    "ohms,expected",
    [
        (100, "100R"),
        (220, "220R"),
        (1_000, "1k"),
        (4_700, "4k7"),
        (47_000, "47k"),
        (470_000, "470k"),
        (1_000_000, "1M"),
        (2_200_000, "2M2"),
    ],
)
def test_format_value(ohms, expected):
    assert format_value(ohms) == expected
