"""Resistor-reader CLI — TASK-054.

``partsledger-resistor-reader <image>`` (or ``python -m
partsledger.resistor_reader <image>``) decodes the resistor(s) in a still
image and prints the value(s) in PartsLedger RKM format, plus a uniformity
report for multi-resistor frames. ``--json`` emits a structured form for
piping into ``/inventory-add``.

The colour-calibration profile (IDEA-013) is looked up at
``$PL_INVENTORY_PATH/.calibration/color_profile.toml`` then
``~/.config/partsledger/calibration/color_profile.toml``; a ``--calibrate``
path overrides both. Without one, decoding falls back to white-balance-naive
classification and the output carries a one-line *"no calibration profile"*
note. OpenCV internals and the profile file paths never surface in the
maker-facing output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:  # py3.11+
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]

_CONFIDENCE_FLOOR = 0.6
_NO_PROFILE_NOTE = "no calibration profile — confidence baseline reduced"


def _profile_candidates(override: str | None) -> list[Path]:
    paths: list[Path] = []
    if override:
        paths.append(Path(override).expanduser())
    inv = os.environ.get("PL_INVENTORY_PATH")
    if inv:
        paths.append(Path(inv) / ".calibration" / "color_profile.toml")
    paths.append(Path.home() / ".config" / "partsledger" / "calibration" / "color_profile.toml")
    return paths


def _load_correction(override: str | None) -> Any | None:
    """Return the 3×3 correction matrix from the first profile found, else None."""
    for path in _profile_candidates(override):
        if path.is_file():
            with path.open("rb") as fh:
                data = tomllib.load(fh)
            matrix = (data.get("correction") or {}).get("matrix")
            if matrix:
                return matrix
    return None


def _decode_frame(image: Any, correction: Any | None) -> tuple[list, list]:
    from .decode import decode_resistor
    from .localise import locate_resistors

    candidates = [c for c in locate_resistors(image) if c.confidence >= _CONFIDENCE_FLOOR]
    decoded = [decode_resistor(image, c, correction=correction) for c in candidates]
    return candidates, decoded


def _render_text(decoded, report, note: str | None) -> str:
    lines: list[str] = []
    if not decoded:
        lines.append("no resistor found")
    elif len(decoded) == 1:
        d = decoded[0]
        lines.append(f"{d.value} {d.tolerance}")
    else:
        for d in decoded:
            lines.append(f"{d.value} {d.tolerance}")
        if report is not None:
            if report.uniform:
                lines.append(f"uniform: all {report.modal_value}")
            else:
                lines.append(f"MIXED — modal {report.modal_value}; deviations:")
                for dev in report.deviations:
                    lines.append(f"  {dev.value} at {dev.position}")
    if note:
        lines.append(note)
    return "\n".join(lines)


def _render_json(decoded, report, note: str | None) -> str:
    payload: dict = {
        "resistors": [
            {
                "value": d.value,
                "tolerance": d.tolerance,
                "confidence": d.confidence,
                "orientation_resolved": d.orientation_resolved,
                "bands": [b.color for b in d.bands],
            }
            for d in decoded
        ],
    }
    if report is not None:
        payload["uniformity"] = {
            "modal_value": report.modal_value,
            "uniform": report.uniform,
            "deviations": [
                {"value": dev.value, "position": list(dev.position), "confidence": dev.confidence}
                for dev in report.deviations
            ],
        }
    if note:
        payload["note"] = note
    return json.dumps(payload, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="partsledger-resistor-reader",
        description="Decode resistor colour bands from a still image.",
    )
    parser.add_argument("image", help="path to a still image of one or more resistors")
    parser.add_argument("--json", action="store_true", help="emit structured JSON output")
    parser.add_argument(
        "--calibrate", metavar="PROFILE", default=None,
        help="path to a colour-calibration profile (overrides the default search)",
    )
    args = parser.parse_args(argv)

    import cv2  # local import keeps --help fast and extra-free

    image = cv2.imread(args.image)
    if image is None:
        print(f"error: could not read image '{args.image}'", file=sys.stderr)
        return 1

    correction = _load_correction(args.calibrate)
    note = None if correction is not None else _NO_PROFILE_NOTE

    candidates, decoded = _decode_frame(image, correction)
    report = None
    if len(decoded) > 1:
        from .uniformity import check_uniformity

        report = check_uniformity(decoded, [c.center for c in candidates])

    out = _render_json(decoded, report, note) if args.json else _render_text(decoded, report, note)
    print(out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
