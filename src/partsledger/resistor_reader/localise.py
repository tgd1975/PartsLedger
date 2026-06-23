"""Resistor localisation — TASK-051 (IDEA-011 Rough approach #1).

Given a still photo of one or more through-hole axial resistors, locate each
resistor body and return a ranked list of candidate bounding boxes. V1 is
classical CV only — HSV thresholding on the typical beige / blue body
colours, morphological closing to bridge the band gaps, contour finding, and
minimum-area-rectangle fitting. No PyTorch (that is V2 / TASK-055).

The OpenCV detail (HSV ranges, kernel sizes, contour-area thresholds) stays
inside this module — it never surfaces in the CLI or in maker-facing
messages. ``cv2`` is imported lazily so the package stays import-cheap on a
host without the ``[resistor-reader]`` extra.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["Candidate", "locate_resistors"]


@dataclass(frozen=True)
class Candidate:
    """One localised resistor body.

    ``bbox`` is the axis-aligned ``(x, y, w, h)`` enclosing rectangle;
    ``angle`` is the body-axis tilt in degrees (from the rotated-rect fit);
    ``confidence`` is a 0..1 score from the body-colour coverage and shape.
    """

    bbox: tuple[int, int, int, int]
    angle: float
    confidence: float

    @property
    def center(self) -> tuple[int, int]:
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)

    @property
    def horizontal(self) -> bool:
        return self.bbox[2] >= self.bbox[3]


# HSV colour gates for the two common axial-resistor body families. Beige /
# tan carbon-film bodies and blue metal-film bodies. Internal detail.
_BODY_GATES = (
    # (lower HSV, upper HSV) — beige / tan
    ((10, 30, 110), (35, 210, 255)),
    # blue metal-film
    ((95, 60, 60), (130, 255, 255)),
)

# A resistor body is a long thin blob: reject near-square / tiny / edge blobs.
_MIN_AREA_FRACTION = 0.002  # of the frame
_MIN_ASPECT = 2.0  # long:short side


def _import_cv2() -> Any:
    import cv2  # type: ignore[import-not-found]

    return cv2


def _body_mask(hsv: Any, cv2: Any) -> Any:
    import numpy as np

    mask = None
    for lo, hi in _BODY_GATES:
        m = cv2.inRange(hsv, np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8))
        mask = m if mask is None else cv2.bitwise_or(mask, m)
    # Bridge the band stripes (non-body colour) so one body is one blob.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask


def locate_resistors(image: Any, *, cv2_module: Any = None) -> list[Candidate]:
    """Return resistor-body candidates, ranked by confidence descending.

    ``image`` is a BGR ``np.ndarray``. Ambiguous frames yield a ranked list
    rather than a single guess; partially-out-of-frame bodies score low.
    """
    cv2 = cv2_module or _import_cv2()

    h, w = image.shape[:2]
    frame_area = float(h * w)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = _body_mask(hsv, cv2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[Candidate] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < _MIN_AREA_FRACTION * frame_area:
            continue
        rect = cv2.minAreaRect(contour)  # ((cx, cy), (rw, rh), angle)
        (cx, cy), (rw, rh), angle = rect
        long_side, short_side = max(rw, rh), min(rw, rh)
        if short_side <= 0:
            continue
        aspect = long_side / short_side
        if aspect < _MIN_ASPECT:
            continue

        x, y, bw, bh = cv2.boundingRect(contour)
        # Confidence: rectangularity (contour fills its rect) × an
        # edge-clipping penalty for bodies touching the frame border.
        rectangularity = float(area / (long_side * short_side))
        touches_edge = x <= 1 or y <= 1 or (x + bw) >= w - 1 or (y + bh) >= h - 1
        edge_penalty = 0.45 if touches_edge else 1.0
        confidence = max(0.0, min(1.0, rectangularity * edge_penalty))

        # Normalise the reported angle to the body-axis tilt.
        body_angle = angle if rw >= rh else angle + 90.0
        candidates.append(
            Candidate(bbox=(int(x), int(y), int(bw), int(bh)), angle=float(body_angle), confidence=confidence)
        )

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates
