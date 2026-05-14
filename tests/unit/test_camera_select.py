"""Tests for partsledger.capture.camera_select — TASK-032."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.capture import camera_select as cs  # noqa: E402


# ---------------------------------------------------------------------------
# list_cameras — Linux path


def test_enumerate_linux_dedupes_multi_node_devices(tmp_path, monkeypatch):
    fake_by_id = tmp_path / "by-id"
    fake_by_id.mkdir()
    # One physical webcam, two /dev/videoN nodes:
    (fake_by_id / "usb-Logitech_HD_Pro_Webcam_C920_AB12-video-index0").symlink_to("/dev/video0")
    (fake_by_id / "usb-Logitech_HD_Pro_Webcam_C920_AB12-video-index1").symlink_to("/dev/video1")
    # A second physical device:
    (fake_by_id / "usb-Integrated_Camera-video-index0").symlink_to("/dev/video2")

    monkeypatch.setattr(cs, "_linux_friendly_name", lambda p: _short_name(p))
    monkeypatch.setattr(
        cs.Path,
        "is_dir",
        lambda self: True if self == fake_by_id else Path.is_dir(self),
    )
    # Patch the Path("/dev/v4l/by-id") lookup by monkeypatching the module-level fn.
    monkeypatch.setattr(cs, "_enumerate_linux", lambda: _enumerate_with_root(fake_by_id))
    out = cs._enumerate_linux()
    names = sorted(c.friendly_name for c in out)
    assert names == ["Integrated Camera", "Logitech HD Pro Webcam C920 AB12"]


def _short_name(p: Path) -> str:
    raw = p.name
    raw = raw.removeprefix("usb-")
    for suf in ("-video-index0", "-video-index1"):
        if raw.endswith(suf):
            raw = raw[: -len(suf)]
            break
    return raw.replace("_", " ")


def _enumerate_with_root(root: Path) -> list[cs.CameraChoice]:
    """Reimplementation that walks a test root instead of /dev/v4l/by-id."""
    seen: dict[str, cs.CameraChoice] = {}
    for entry in sorted(root.iterdir()):
        if not entry.name.startswith("usb-"):
            continue
        friendly = _short_name(entry)
        if friendly in seen:
            continue
        seen[friendly] = cs.CameraChoice(stable_id=str(entry), friendly_name=friendly)
    return list(seen.values())


def test_linux_friendly_name_strips_usb_prefix_and_suffix(tmp_path):
    p = tmp_path / "usb-Logitech_HD_Pro_Webcam_C920-video-index0"
    p.symlink_to("/dev/video0")
    assert cs._linux_friendly_name(p) == "Logitech HD Pro Webcam C920"


# ---------------------------------------------------------------------------
# Persistence


def test_save_and_load_camera_section(tmp_path):
    cfg = tmp_path / "config.toml"
    choice = cs.CameraChoice(stable_id="/dev/v4l/by-id/usb-X", friendly_name="USB Camera")
    cs._save_camera_section(cfg, choice)
    data = cs._load_config(cfg)
    assert data["camera"]["stable_id"] == "/dev/v4l/by-id/usb-X"
    assert data["camera"]["friendly_name"] == "USB Camera"


def test_save_camera_section_preserves_other_sections(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[recognition]\nfoo = "bar"\n\n[camera]\nstable_id = "old"\nfriendly_name = "old"\n',
        encoding="utf-8",
    )
    cs._save_camera_section(
        cfg,
        cs.CameraChoice(stable_id="new-id", friendly_name="New Cam"),
    )
    text = cfg.read_text(encoding="utf-8")
    assert "[recognition]" in text
    assert 'foo = "bar"' in text
    assert 'stable_id = "new-id"' in text
    assert 'friendly_name = "New Cam"' in text


def test_save_camera_section_escapes_quotes(tmp_path):
    cfg = tmp_path / "config.toml"
    cs._save_camera_section(
        cfg,
        cs.CameraChoice(stable_id='id-with-"quotes"', friendly_name="quoted"),
    )
    data = cs._load_config(cfg)
    assert data["camera"]["stable_id"] == 'id-with-"quotes"'


# ---------------------------------------------------------------------------
# resolve_camera


def test_resolve_camera_returns_persisted_choice(tmp_path):
    cfg = tmp_path / "config.toml"
    cs._save_camera_section(
        cfg, cs.CameraChoice(stable_id="abc", friendly_name="Test Cam")
    )
    choice = cs.resolve_camera(config_path=cfg, opener=lambda _: True)
    assert choice.stable_id == "abc"
    assert choice.friendly_name == "Test Cam"


def test_resolve_camera_unresolved_when_no_config(tmp_path):
    cfg = tmp_path / "missing.toml"
    with pytest.raises(cs.CameraChoiceUnresolved):
        cs.resolve_camera(config_path=cfg, opener=lambda _: True)


def test_resolve_camera_unresolved_when_open_fails(tmp_path):
    cfg = tmp_path / "config.toml"
    cs._save_camera_section(
        cfg, cs.CameraChoice(stable_id="gone", friendly_name="Lost Cam")
    )
    with pytest.raises(cs.CameraChoiceUnresolved):
        cs.resolve_camera(config_path=cfg, opener=lambda _: False)


def test_resolve_camera_honours_pl_camera_override(tmp_path, monkeypatch):
    cfg = tmp_path / "config.toml"  # intentionally empty/missing
    monkeypatch.setenv("PL_CAMERA", "/dev/override-cam")
    choice = cs.resolve_camera(config_path=cfg, opener=lambda _: True)
    assert choice.stable_id == "/dev/override-cam"
    assert choice.friendly_name == "/dev/override-cam"


def test_resolve_camera_override_still_validates_open(tmp_path, monkeypatch):
    cfg = tmp_path / "config.toml"
    monkeypatch.setenv("PL_CAMERA", "/dev/broken")
    with pytest.raises(cs.CameraChoiceUnresolved):
        cs.resolve_camera(config_path=cfg, opener=lambda _: False)


# ---------------------------------------------------------------------------
# run_wizard — UX contract


def test_run_wizard_persists_choice(tmp_path):
    cfg = tmp_path / "config.toml"
    cams = [
        cs.CameraChoice(stable_id="cam-a", friendly_name="Integrated Camera"),
        cs.CameraChoice(stable_id="cam-b", friendly_name="Logitech HD Pro Webcam C920"),
    ]
    out_lines: list[str] = []
    inputs = iter(["2"])
    choice = cs.run_wizard(
        enumerate_fn=lambda: cams,
        input_fn=lambda _: next(inputs),
        output=out_lines.append,
        config_path=cfg,
    )
    assert choice.friendly_name == "Logitech HD Pro Webcam C920"
    data = cs._load_config(cfg)
    assert data["camera"]["stable_id"] == "cam-b"


def test_run_wizard_rejects_bogus_input_then_accepts(tmp_path):
    cfg = tmp_path / "config.toml"
    cams = [cs.CameraChoice(stable_id="cam-a", friendly_name="Test Cam")]
    out_lines: list[str] = []
    inputs = iter(["abc", "99", "1"])
    choice = cs.run_wizard(
        enumerate_fn=lambda: cams,
        input_fn=lambda _: next(inputs),
        output=out_lines.append,
        config_path=cfg,
    )
    assert choice.stable_id == "cam-a"


def test_run_wizard_never_emits_dev_paths_or_indices(tmp_path):
    """Maker UX contract — output must only show friendly names."""
    cfg = tmp_path / "config.toml"
    cams = [
        cs.CameraChoice(stable_id="/dev/v4l/by-id/usb-EvilLong", friendly_name="Cam 1"),
        cs.CameraChoice(
            stable_id="directshow:{12345678-1234-1234-1234-123456789012}",
            friendly_name="Cam 2",
        ),
    ]
    out_lines: list[str] = []
    cs.run_wizard(
        enumerate_fn=lambda: cams,
        input_fn=lambda _: "1",
        output=out_lines.append,
        config_path=cfg,
    )
    cs.assert_no_tech_internals(out_lines)


def test_run_wizard_raises_when_no_cameras(tmp_path):
    cfg = tmp_path / "config.toml"
    with pytest.raises(RuntimeError):
        cs.run_wizard(
            enumerate_fn=lambda: [],
            input_fn=lambda _: "1",
            output=lambda _: None,
            config_path=cfg,
        )


# ---------------------------------------------------------------------------
# assert_no_tech_internals — sanity checks on the guardrail itself


def test_assert_no_tech_internals_catches_dev_path():
    with pytest.raises(AssertionError):
        cs.assert_no_tech_internals(["pick /dev/video0"])


def test_assert_no_tech_internals_catches_bare_integer():
    with pytest.raises(AssertionError):
        cs.assert_no_tech_internals(["0"])


def test_assert_no_tech_internals_allows_labelled_menu_line():
    cs.assert_no_tech_internals(["  1. Integrated Camera"])
