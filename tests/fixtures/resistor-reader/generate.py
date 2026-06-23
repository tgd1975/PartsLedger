"""Generate synthetic resistor fixtures for the EPIC-008 V1 test suite.

These are *synthetic* — clean drawn resistors on a controlled background — so
the localise + decode algorithms can be validated deterministically without a
camera. Real-photo robustness is the TASK-051/052 `human-in-loop: Support`
step. Re-run with:

    python tests/fixtures/resistor-reader/generate.py
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent

BG = (40, 40, 40)  # BGR dark bench background
BODY_RGB = (220, 200, 160)

# EIA palette in RGB (mirrors decode._PALETTE_RGB for the digit/mult/tol set).
PALETTE_RGB = {
    "black": (0, 0, 0), "brown": (102, 51, 0), "red": (200, 0, 0),
    "orange": (255, 128, 0), "yellow": (230, 220, 0), "green": (0, 140, 60),
    "blue": (0, 60, 220), "violet": (140, 0, 200), "grey": (128, 128, 128),
    "white": (245, 245, 245), "gold": (212, 175, 55), "silver": (190, 190, 190),
}


def _bgr(rgb):
    r, g, b = rgb
    return (b, g, r)


def draw_resistor(img, top_left, size, bands, *, even=False):
    """Draw one horizontal resistor; return (bbox, band_list).

    ``even=True`` spaces every band equally (no tolerance-gap cue) — used to
    build a genuinely orientation-ambiguous fixture.
    """
    bx, by = top_left
    bw, bh = size
    cv2.rectangle(img, (bx, by), (bx + bw, by + bh), _bgr(BODY_RGB), -1)

    band_w = max(10, bw // 18)

    if even:
        # All bands equally spaced across the middle — no tolerance gap.
        x = bx + int(bw * 0.15)
        gap = band_w
        for color in bands:
            cv2.rectangle(img, (x, by), (x + band_w, by + bh), _bgr(PALETTE_RGB[color]), -1)
            x += band_w + gap
        return (bx, by, bw, bh), bands

    # Value bands clustered on the left; tolerance band offset to the right,
    # leaving the wide gap that signals reading direction.
    value_bands = bands[:-1]
    tol_band = bands[-1]
    x = bx + int(bw * 0.12)
    gap = band_w
    for color in value_bands:
        cv2.rectangle(img, (x, by), (x + band_w, by + bh), _bgr(PALETTE_RGB[color]), -1)
        x += band_w + gap
    tol_x = bx + int(bw * 0.80)
    cv2.rectangle(img, (tol_x, by), (tol_x + band_w, by + bh), _bgr(PALETTE_RGB[tol_band]), -1)

    return (bx, by, bw, bh), bands


def make_ambiguous(name, bands):
    img = np.full((160, 480, 3), BG, dtype=np.uint8)
    bbox, _ = draw_resistor(img, (70, 55), (340, 50), bands, even=True)
    cv2.imwrite(str(HERE / f"{name}.png"), img)
    (HERE / f"{name}.json").write_text(
        json.dumps({"value": "1k", "tolerance": "1%", "ambiguous": True}, indent=2),
        encoding="utf-8",
    )


def make_single(name, bands, value, tolerance, *, busy=False):
    img = np.full((160, 480, 3), BG, dtype=np.uint8)
    if busy:
        # Clutter in the margins only — never overlapping the body band
        # (rows 55..105), so the resistor stays the dominant beige blob.
        rng = np.random.default_rng(7)
        for _ in range(10):
            top = bool(rng.integers(0, 2))
            y0 = int(rng.integers(0, 40)) if top else int(rng.integers(120, 150))
            x0 = int(rng.integers(0, 440))
            col = tuple(int(c) for c in rng.integers(60, 200, size=3))
            cv2.rectangle(img, (x0, y0), (x0 + 30, y0 + 10), col, -1)
    bbox, _ = draw_resistor(img, (70, 55), (340, 50), bands, even=False)
    cv2.imwrite(str(HERE / f"{name}.png"), img)
    (HERE / f"{name}.json").write_text(
        json.dumps({"value": value, "tolerance": tolerance,
                    "bbox": list(bbox), "count": 1}, indent=2),
        encoding="utf-8",
    )


def make_partial(name, bands):
    """Resistor running off the left edge of the frame."""
    img = np.full((160, 480, 3), BG, dtype=np.uint8)
    bbox, _ = draw_resistor(img, (-120, 55), (340, 50), bands)
    cv2.imwrite(str(HERE / f"{name}.png"), img)
    (HERE / f"{name}.json").write_text(
        json.dumps({"value": "1k", "tolerance": "5%", "partial": True}, indent=2),
        encoding="utf-8",
    )


def make_strip(name, rows, expected):
    img = np.full((90 * len(rows) + 30, 480, 3), BG, dtype=np.uint8)
    boxes = []
    y = 20
    for bands in rows:
        bbox, _ = draw_resistor(img, (70, y), (340, 50), bands)
        boxes.append(list(bbox))
        y += 90
    cv2.imwrite(str(HERE / f"{name}.png"), img)
    (HERE / f"{name}.json").write_text(
        json.dumps({"count": len(rows), "bboxes": boxes, **expected}, indent=2),
        encoding="utf-8",
    )


# 4-band codes: [d1, d2, multiplier, tolerance]
ONE_K = ["brown", "black", "red", "gold"]          # 1k 5%
FOUR_K7 = ["yellow", "violet", "red", "gold"]       # 4k7 5%
# 5-band: [d1, d2, d3, multiplier, tolerance]
TWO_TWENTY = ["red", "red", "black", "black", "brown"]  # 220R 1%
# ambiguous 4-band (no gold/silver): brown-black-red-brown decodes both ways
AMBIG = ["brown", "black", "red", "brown"]


def main():
    make_single("single-1k", ONE_K, "1k", "5%")
    make_single("single-4k7", FOUR_K7, "4k7", "5%")
    make_single("single-220", TWO_TWENTY, "220R", "1%")
    make_single("busy-background", ONE_K, "1k", "5%", busy=True)
    make_ambiguous("ambiguous", AMBIG)
    make_partial("partial", ONE_K)
    make_strip("three-1k", [ONE_K, ONE_K, ONE_K], {"uniform": True, "modal_value": "1k"})
    make_strip(
        "mixed-strip",
        [ONE_K, ONE_K, FOUR_K7, ONE_K, ONE_K],
        {"uniform": False, "modal_value": "1k", "deviation_value": "4k7"},
    )
    # Calibration profile fixture (identity matrix) for the CLI no-note path.
    calib = HERE / "calibration"
    calib.mkdir(exist_ok=True)
    (calib / "color_profile.toml").write_text(
        "[correction]\nmatrix = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]\n",
        encoding="utf-8",
    )
    print("fixtures written to", HERE)


if __name__ == "__main__":
    main()
