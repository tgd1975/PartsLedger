"""Tests for partsledger.resistor_reader.localise — TASK-051.

Runs against the synthetic fixture set in tests/fixtures/resistor-reader/.
These are drawn, not photographed — real-photo robustness is the
`human-in-loop: Support` step. Skips cleanly when the [resistor-reader]
extra (cv2 / skimage / scipy) is not installed.
"""

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

from partsledger.resistor_reader.localise import locate_resistors  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "resistor-reader"


def _load(name):
    img = cv2.imread(str(FIXTURES / f"{name}.png"))
    assert img is not None, f"fixture {name} missing — run generate.py"
    truth = json.loads((FIXTURES / f"{name}.json").read_text())
    return img, truth


def test_single_resistor_found_with_high_confidence():
    img, truth = _load("single-1k")
    cands = locate_resistors(img)
    assert cands, "no candidate on the single-resistor fixture"
    top = cands[0]
    assert top.confidence > 0.8
    # Centre roughly matches the ground-truth bbox centre.
    tx, ty, tw, th = truth["bbox"]
    cx, cy = top.center
    assert abs(cx - (tx + tw // 2)) < 40
    assert abs(cy - (ty + th // 2)) < 40


def test_three_resistors_one_candidate_each():
    img, truth = _load("three-1k")
    cands = [c for c in locate_resistors(img) if c.confidence > 0.6]
    assert len(cands) == truth["count"] == 3


def test_busy_background_still_finds_resistor():
    img, _ = _load("busy-background")
    cands = locate_resistors(img)
    # Ranked list returned; at least one strong candidate (the resistor).
    assert cands
    assert any(c.confidence > 0.8 for c in cands)
    assert cands == sorted(cands, key=lambda c: c.confidence, reverse=True)


def test_partial_resistor_is_low_confidence():
    img, _ = _load("partial")
    cands = locate_resistors(img)
    # Either rejected, or surfaced only at low confidence (edge penalty).
    strong = [c for c in cands if c.confidence > 0.6]
    assert not strong


def test_candidates_ranked_descending():
    img, _ = _load("mixed-strip")
    cands = locate_resistors(img)
    confs = [c.confidence for c in cands]
    assert confs == sorted(confs, reverse=True)
