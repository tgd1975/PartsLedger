"""Tests for partsledger.resistor_reader.uniformity — TASK-053.

The unit cases use directly-constructed DecodedResistor lists (no image);
one end-to-end case walks the mixed-strip fixture through localise → decode →
uniformity.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

pytest.importorskip("scipy")  # extra gate (package import)
pytest.importorskip("skimage")

from partsledger.resistor_reader.decode import DecodedResistor  # noqa: E402
from partsledger.resistor_reader.uniformity import check_uniformity  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "resistor-reader"


def _r(value, conf=0.85):
    return DecodedResistor(value=value, tolerance="5%", confidence=conf)


# ---------------------------------------------------------------------------
# unit cases (no image)


def test_all_same_is_uniform():
    rep = check_uniformity([_r("1k"), _r("1k"), _r("1k")])
    assert rep.uniform is True
    assert rep.modal_value == "1k"
    assert rep.deviations == []


def test_one_outlier():
    rep = check_uniformity(
        [_r("1k"), _r("1k"), _r("4k7"), _r("1k")],
        positions=[(0, 0), (1, 1), (2, 2), (3, 3)],
    )
    assert rep.uniform is False
    assert rep.modal_value == "1k"
    assert len(rep.deviations) == 1
    assert rep.deviations[0].value == "4k7"
    assert rep.deviations[0].position == (2, 2)


def test_multi_mode_both_outliers_listed():
    rep = check_uniformity([_r("1k"), _r("1k"), _r("1k"), _r("4k7"), _r("4k7")])
    assert rep.modal_value == "1k"
    assert [d.value for d in rep.deviations] == ["4k7", "4k7"]


def test_low_confidence_outlier_still_listed():
    rep = check_uniformity([_r("1k"), _r("1k"), _r("220R", conf=0.05)])
    assert rep.uniform is False
    assert rep.deviations[0].value == "220R"
    assert rep.deviations[0].confidence == 0.05  # not discarded


def test_empty_is_uniform():
    rep = check_uniformity([])
    assert rep.uniform is True
    assert rep.deviations == []


# ---------------------------------------------------------------------------
# end-to-end


def test_mixed_strip_end_to_end():
    cv2 = pytest.importorskip("cv2")
    from partsledger.resistor_reader.decode import decode_resistor
    from partsledger.resistor_reader.localise import locate_resistors

    img = cv2.imread(str(FIXTURES / "mixed-strip.png"))
    truth = json.loads((FIXTURES / "mixed-strip.json").read_text())
    cands = [c for c in locate_resistors(img) if c.confidence > 0.6]
    decoded = [decode_resistor(img, c) for c in cands]
    rep = check_uniformity(decoded, [c.center for c in cands])
    assert rep.uniform is False
    assert rep.modal_value == truth["modal_value"]
    assert len(rep.deviations) == 1
    assert rep.deviations[0].value == truth["deviation_value"]
