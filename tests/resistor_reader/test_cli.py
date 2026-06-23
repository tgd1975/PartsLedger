"""Tests for the partsledger-resistor-reader CLI — TASK-054.

Invokes the entry point as a subprocess (`python -m
partsledger.resistor_reader <image>`) and asserts on stdout.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("cv2")
pytest.importorskip("skimage")
pytest.importorskip("scipy")

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "resistor-reader"
NO_PROFILE_NOTE = "no calibration profile"


def _run(args, env=None):
    full_env = dict(os.environ)
    full_env.setdefault("PYTHONPATH", str(REPO_ROOT / "src"))
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "partsledger.resistor_reader", *args],
        capture_output=True, text=True, env=full_env,
    )


def test_single_resistor_text_output():
    res = _run([str(FIXTURES / "single-1k.png")])
    assert res.returncode == 0, res.stderr
    assert "1k" in res.stdout


def test_json_multi_resistor():
    res = _run(["--json", str(FIXTURES / "mixed-strip.png")])
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["uniformity"]["uniform"] is False
    assert payload["uniformity"]["modal_value"] == "1k"
    assert len(payload["resistors"]) == 5


def test_no_profile_note_present():
    # No PL_INVENTORY_PATH, no --calibrate → the note appears.
    env = {k: os.environ[k] for k in os.environ if k != "PL_INVENTORY_PATH"}
    env["HOME"] = "/nonexistent-home-for-test"
    res = _run([str(FIXTURES / "single-1k.png")], env=env)
    assert NO_PROFILE_NOTE in res.stdout


def test_profile_present_suppresses_note_via_calibrate():
    res = _run([
        "--calibrate", str(FIXTURES / "calibration" / "color_profile.toml"),
        str(FIXTURES / "single-1k.png"),
    ])
    assert res.returncode == 0, res.stderr
    assert NO_PROFILE_NOTE not in res.stdout


def test_profile_present_via_inventory_path(tmp_path):
    calib = tmp_path / ".calibration"
    calib.mkdir()
    shutil.copy(FIXTURES / "calibration" / "color_profile.toml", calib / "color_profile.toml")
    res = _run([str(FIXTURES / "single-1k.png")], env={"PL_INVENTORY_PATH": str(tmp_path)})
    assert res.returncode == 0, res.stderr
    assert NO_PROFILE_NOTE not in res.stdout


def test_help_hides_cv_internals():
    res = _run(["--help"])
    assert res.returncode == 0
    low = res.stdout.lower()
    for leak in ("hsv", "contour", "kernel", "morph"):
        assert leak not in low
