"""Resistor band reading + EIA decode — TASK-052 (IDEA-011 Rough approach #2).

Given a localised resistor body (a :class:`~partsledger.resistor_reader.localise.Candidate`),
find the band positions along the body axis, sample each band's dominant
colour, classify against the EIA palette, and decode to a nominal resistance
+ tolerance. Handles 4-band and 5-band codes.

Orientation (which end is band 1?) is resolved by decoding both directions
and keeping the one that yields a valid E-series value; if both are valid the
higher-precision series wins and confidence is reduced. Output values use the
PartsLedger RKM convention (``4k7``, ``100R``, ``1M``) so the decoder output
pastes straight into ``/inventory-add``.

The EIA palette and E-series tables are module-internal. The decoder accepts
an optional colour-correction matrix (the IDEA-013 calibration profile);
without one it falls back to white-balance-naive classification and reports a
lower baseline confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "BandReading",
    "DecodedResistor",
    "decode_resistor",
    "format_value",
    "classify_color",
    "EIA_DIGITS",
]

# EIA colour → digit. RGB reference values (the synthetic fixtures draw these
# exactly; real photos lean on the calibration profile to get close).
_PALETTE_RGB: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "brown": (102, 51, 0),
    "red": (200, 0, 0),
    "orange": (255, 128, 0),
    "yellow": (230, 220, 0),
    "green": (0, 140, 60),
    "blue": (0, 60, 220),
    "violet": (140, 0, 200),
    "grey": (128, 128, 128),
    "white": (245, 245, 245),
    "gold": (212, 175, 55),
    "silver": (190, 190, 190),
}

EIA_DIGITS: dict[str, int] = {
    "black": 0, "brown": 1, "red": 2, "orange": 3, "yellow": 4,
    "green": 5, "blue": 6, "violet": 7, "grey": 8, "white": 9,
}

_MULTIPLIER: dict[str, float] = {
    "black": 1, "brown": 10, "red": 100, "orange": 1_000, "yellow": 10_000,
    "green": 100_000, "blue": 1_000_000, "violet": 10_000_000,
    "gold": 0.1, "silver": 0.01,
}

_TOLERANCE: dict[str, str] = {
    "brown": "1%", "red": "2%", "green": "0.5%", "blue": "0.25%",
    "violet": "0.1%", "grey": "0.05%", "gold": "5%", "silver": "10%",
}

# E-series significant-figure sets (normalised to a 2- or 3-digit integer).
_E12 = {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82}
_E24 = _E12 | {11, 13, 16, 20, 24, 30, 36, 43, 51, 62, 75, 91}


@dataclass(frozen=True)
class BandReading:
    color: str
    confidence: float


@dataclass(frozen=True)
class DecodedResistor:
    value: str  # RKM-formatted, e.g. "4k7"
    tolerance: str  # e.g. "5%"
    bands: list[BandReading] = field(default_factory=list)
    confidence: float = 0.0
    orientation_resolved: bool = True
    ohms: float = 0.0


# ---------------------------------------------------------------------------
# colour classification


def classify_color(rgb: tuple[float, float, float], *, correction: Any = None) -> tuple[str, float]:
    """Nearest EIA palette colour for an RGB sample, plus a 0..1 confidence.

    ``correction`` is an optional 3×3 colour-correction matrix (the IDEA-013
    profile); when absent, naive nearest-neighbour is used.
    """
    import numpy as np

    vec = np.asarray(rgb, dtype=np.float64)
    if correction is not None:
        vec = np.asarray(correction, dtype=np.float64) @ vec
    best_name, best_dist = "black", float("inf")
    for name, ref in _PALETTE_RGB.items():
        dist = float(np.linalg.norm(vec - np.asarray(ref, dtype=np.float64)))
        if dist < best_dist:
            best_name, best_dist = name, dist
    # Map distance (0..~441 max in RGB) to a soft confidence.
    confidence = max(0.0, 1.0 - best_dist / 180.0)
    return best_name, confidence


# ---------------------------------------------------------------------------
# value formatting (RKM code)


def format_value(ohms: float) -> str:
    """Format a resistance in ohms as PartsLedger RKM code (``4k7``/``100R``/``1M``)."""
    if ohms >= 1_000_000:
        unit, scaled = "M", ohms / 1_000_000
    elif ohms >= 1_000:
        unit, scaled = "k", ohms / 1_000
    else:
        unit, scaled = "R", float(ohms)
    if scaled == int(scaled):
        digits = str(int(scaled))
    else:
        digits = ("%g" % scaled)
    if "." in digits:
        whole, frac = digits.split(".")
        return f"{whole}{unit}{frac}"
    return f"{digits}{unit}"


def _significant_figures(ohms: float) -> int | None:
    """Normalise a value to its 2/3-digit significant-figure integer for an
    E-series membership check, or ``None`` if it can't be normalised."""
    if ohms <= 0:
        return None
    v = ohms
    while v >= 100:
        v /= 10
    while v < 10:
        v *= 10
    return int(round(v))


def _e_series(ohms: float) -> str | None:
    sig = _significant_figures(ohms)
    if sig is None:
        return None
    if sig in _E12:
        return "E12"
    if sig in _E24:
        return "E24"
    return None


_SERIES_RANK = {"E12": 1, "E24": 2, "E96": 3}


# ---------------------------------------------------------------------------
# decode one direction


def _decode_bands(colors: list[str]) -> tuple[float, str] | None:
    """Decode an ordered band-colour list to ``(ohms, tolerance)`` or None.

    Supports 4-band (d d × tol) and 5-band (d d d × tol).
    """
    n = len(colors)
    if n == 4:
        d1, d2, mult, tol = colors
        digits = [d1, d2]
        mult_color, tol_color = mult, tol
        significant = None
    elif n == 5:
        d1, d2, d3, mult, tol = colors
        digits = [d1, d2, d3]
        mult_color, tol_color = mult, tol
        significant = None
    else:
        return None

    if any(c not in EIA_DIGITS for c in digits):
        return None
    if mult_color not in _MULTIPLIER:
        return None
    if tol_color not in _TOLERANCE:
        return None

    sig = 0
    for c in digits:
        sig = sig * 10 + EIA_DIGITS[c]
    del significant
    ohms = sig * _MULTIPLIER[mult_color]
    return ohms, _TOLERANCE[tol_color]


def _direction_score(decoded: tuple[float, str] | None) -> tuple[bool, str | None]:
    """(valid, e_series) for a decoded direction."""
    if decoded is None:
        return False, None
    ohms, _tol = decoded
    series = _e_series(ohms)
    return True, series


# ---------------------------------------------------------------------------
# band finding along the body axis


def _find_band_colors(
    image: Any, candidate: Any, cv2: Any, *, correction: Any = None
) -> list[tuple[str, float]]:
    import numpy as np

    x, y, w, h = candidate.bbox
    crop = image[y : y + h, x : x + w]
    if crop.size == 0:
        return []
    # Work along the long axis; transpose so columns run left→right on it.
    if h > w:
        crop = np.transpose(crop, (1, 0, 2))
    ch, cw = crop.shape[:2]
    # Sample the central band of rows (avoid the rounded body edges).
    y0, y1 = int(ch * 0.3), int(ch * 0.7)
    strip = crop[y0:y1, :, :].astype(np.float64)  # (rows, cols, 3) BGR
    col_mean_bgr = strip.mean(axis=0)  # (cols, 3)
    col_mean_rgb = col_mean_bgr[:, ::-1]

    # Body colour = median of the outer margin columns (no bands there).
    margin = max(2, int(cw * 0.06))
    body = np.median(np.vstack([col_mean_rgb[:margin], col_mean_rgb[-margin:]]), axis=0)

    dist = np.linalg.norm(col_mean_rgb - body, axis=1)
    band_cols = dist > 55.0  # column belongs to a band, not the body

    # Group contiguous band columns into segments.
    segments: list[tuple[int, int]] = []
    start = None
    for i, flag in enumerate(band_cols):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start >= max(2, int(cw * 0.01)):
                segments.append((start, i))
            start = None
    if start is not None and cw - start >= max(2, int(cw * 0.01)):
        segments.append((start, cw))

    readings: list[tuple[str, float, int]] = []
    for s, e in segments:
        mid = (s + e) // 2
        sample = col_mean_rgb[max(s, mid - 1) : min(e, mid + 2)].mean(axis=0)
        name, conf = classify_color(tuple(sample), correction=correction)
        readings.append((name, conf, mid))
    return readings


def _spacing_orientation(centers: list[int]) -> str:
    """Infer reading direction from band spacing.

    The tolerance band sits after a wider gap than the value-band cluster, so
    an over-large *last* gap means forward (tolerance at the right end), an
    over-large *first* gap means reversed. Returns ``"forward"`` /
    ``"reverse"`` / ``"none"`` (spacing inconclusive — evenly spaced).
    """
    if len(centers) < 4:
        return "none"
    gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    inner = sorted(gaps)[: max(1, len(gaps) - 1)]  # drop the single widest gap
    baseline = sum(inner) / len(inner)
    if baseline <= 0:
        return "none"
    first, last = gaps[0], gaps[-1]
    if last > 1.6 * baseline and last >= first * 1.3:
        return "forward"
    if first > 1.6 * baseline and first >= last * 1.3:
        return "reverse"
    return "none"


# ---------------------------------------------------------------------------
# public entry point


def decode_resistor(
    image: Any,
    candidate: Any,
    *,
    correction: Any = None,
    cv2_module: Any = None,
) -> DecodedResistor:
    """Decode the resistor in ``candidate`` to a :class:`DecodedResistor`.

    ``correction`` is an optional IDEA-013 colour-correction matrix; without
    one the decode is white-balance-naive and the baseline confidence is
    reduced.
    """
    cv2 = cv2_module
    if cv2 is None:
        import cv2 as cv2  # type: ignore

    readings = _find_band_colors(image, candidate, cv2, correction=correction)
    colors = [r[0] for r in readings]
    band_conf = sum(r[1] for r in readings) / len(readings) if readings else 0.0
    bands = [BandReading(color=c, confidence=cf) for c, cf, _ in readings]
    spacing = _spacing_orientation([r[2] for r in readings])

    forward = _decode_bands(colors)
    reverse = _decode_bands(list(reversed(colors)))
    f_valid, f_series = _direction_score(forward)
    r_valid, r_series = _direction_score(reverse)

    orientation_resolved = True
    chosen = forward
    if f_valid and r_valid:
        # Both directions decode. Band spacing is the strongest cue (the
        # tolerance band sits after a wider gap); fall back to the
        # higher-precision E-series, and call it ambiguous only on a true tie.
        if spacing == "forward":
            chosen = forward
        elif spacing == "reverse":
            chosen = reverse
        else:
            f_rank = _SERIES_RANK.get(f_series or "", 0)
            r_rank = _SERIES_RANK.get(r_series or "", 0)
            if r_rank > f_rank:
                chosen = reverse
            elif f_rank > r_rank:
                chosen = forward
            else:
                chosen = forward
                orientation_resolved = False  # ambiguous — reduce confidence
    elif r_valid and not f_valid:
        chosen = reverse
    elif f_valid and not r_valid:
        chosen = forward
    else:
        # Neither direction decodes cleanly.
        return DecodedResistor(
            value="?", tolerance="?", bands=bands, confidence=0.0,
            orientation_resolved=False, ohms=0.0,
        )

    ohms, tolerance = chosen
    confidence = band_conf
    if not orientation_resolved:
        confidence *= 0.5
    if correction is None:
        confidence *= 0.85  # white-balance-naive baseline penalty
    return DecodedResistor(
        value=format_value(ohms),
        tolerance=tolerance,
        bands=bands,
        confidence=round(confidence, 3),
        orientation_resolved=orientation_resolved,
        ohms=ohms,
    )
