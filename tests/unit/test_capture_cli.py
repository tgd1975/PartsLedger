"""Tests for the partsledger.capture CLI wrapper — TASK-035."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.capture import __main__ as cli  # noqa: E402
from partsledger.capture import camera_select as cs  # noqa: E402
from partsledger.capture import viewfinder as vf  # noqa: E402


# ---------------------------------------------------------------------------
# argparse — flag surface


def test_parser_accepts_documented_flags():
    parser = cli.build_parser()
    args = parser.parse_args(
        ["--no-preview", "--pick-camera", "--dump-captures-to", "/tmp/foo"]
    )
    assert args.no_preview is True
    assert args.pick_camera is True
    assert args.dump_captures_to == Path("/tmp/foo")


def test_parser_defaults_are_off():
    args = cli.build_parser().parse_args([])
    assert args.no_preview is False
    assert args.pick_camera is False
    assert args.dump_captures_to is None


# ---------------------------------------------------------------------------
# main() — exit codes


def test_main_returns_0_in_no_preview_mode(monkeypatch):
    monkeypatch.setattr(
        cli, "resolve_camera", lambda: cs.CameraChoice("/dev/x", "Cam")
    )
    assert cli.main(["--no-preview"]) == cli.EXIT_OK


def test_main_returns_1_when_camera_unresolved_and_no_wizard(monkeypatch):
    def fail_resolve():
        raise cs.CameraChoiceUnresolved("no config")

    def fail_wizard(**_):
        raise RuntimeError("no cameras")

    monkeypatch.setattr(cli, "resolve_camera", fail_resolve)
    monkeypatch.setattr(cli, "run_wizard", fail_wizard)
    assert cli.main(["--no-preview"]) == cli.EXIT_CAMERA


def test_main_pick_camera_forces_wizard(monkeypatch):
    called = {"wizard": 0, "resolve": 0}

    def fake_wizard(**_):
        called["wizard"] += 1
        return cs.CameraChoice("/dev/x", "Cam")

    def fake_resolve():
        called["resolve"] += 1
        return cs.CameraChoice("/dev/persisted", "Old")

    monkeypatch.setattr(cli, "run_wizard", fake_wizard)
    monkeypatch.setattr(cli, "resolve_camera", fake_resolve)
    cli.main(["--pick-camera", "--no-preview"])
    assert called["wizard"] == 1
    assert called["resolve"] == 0


def test_main_returns_2_on_display_backend_failure(monkeypatch):
    monkeypatch.setattr(
        cli, "resolve_camera", lambda: cs.CameraChoice("/dev/x", "Cam")
    )

    class _BoomVF:
        def __init__(self, *_a, **_kw):
            raise vf.DisplayBackendUnavailable("no display")

    monkeypatch.setattr(cli, "Viewfinder", _BoomVF)
    assert cli.main([]) == cli.EXIT_DISPLAY


def test_main_returns_1_on_camera_lost_during_session(monkeypatch):
    monkeypatch.setattr(
        cli, "resolve_camera", lambda: cs.CameraChoice("/dev/x", "Cam")
    )

    fake_vf = mock.MagicMock()
    fake_vf.__enter__ = mock.MagicMock(return_value=fake_vf)
    fake_vf.__exit__ = mock.MagicMock(return_value=False)
    fake_vf.pump_once.return_value = "camera-lost"

    monkeypatch.setattr(cli, "Viewfinder", lambda *a, **kw: fake_vf)
    assert cli.main([]) == cli.EXIT_CAMERA


def test_main_returns_0_on_clean_key_quit(monkeypatch):
    monkeypatch.setattr(
        cli, "resolve_camera", lambda: cs.CameraChoice("/dev/x", "Cam")
    )
    fake_vf = mock.MagicMock()
    fake_vf.__enter__ = mock.MagicMock(return_value=fake_vf)
    fake_vf.__exit__ = mock.MagicMock(return_value=False)
    fake_vf.pump_once.return_value = "key-quit"
    monkeypatch.setattr(cli, "Viewfinder", lambda *a, **kw: fake_vf)
    assert cli.main([]) == cli.EXIT_OK


def test_main_returns_130_on_signal_event(monkeypatch):
    monkeypatch.setattr(
        cli, "resolve_camera", lambda: cs.CameraChoice("/dev/x", "Cam")
    )
    fake_vf = mock.MagicMock()
    fake_vf.__enter__ = mock.MagicMock(return_value=fake_vf)
    fake_vf.__exit__ = mock.MagicMock(return_value=False)
    fake_vf.pump_once.return_value = "signal"
    monkeypatch.setattr(cli, "Viewfinder", lambda *a, **kw: fake_vf)
    assert cli.main([]) == cli.EXIT_INTERRUPTED


def test_main_calls_flash_capture_on_trigger(monkeypatch):
    """The CLI must invoke v.flash_capture() each time it captures."""
    monkeypatch.setattr(
        cli, "resolve_camera", lambda: cs.CameraChoice("/dev/x", "Cam")
    )

    np = pytest.importorskip("numpy")

    fake_vf = mock.MagicMock()
    fake_vf.__enter__ = mock.MagicMock(return_value=fake_vf)
    fake_vf.__exit__ = mock.MagicMock(return_value=False)
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    fake_vf.capture.return_value = vf.CapturePacket(
        image=image,
        metadata={
            "timestamp": "2026-05-14T12-00-00.000000Z",
            "camera": {"name": "Cam", "stable_id": "/dev/x"},
            "resolution": (10, 10),
            "trigger": "keyboard",
        },
    )

    events = iter(["trigger", "trigger", "key-quit"])
    fake_vf.pump_once.side_effect = lambda **_: next(events)
    monkeypatch.setattr(cli, "Viewfinder", lambda *a, **kw: fake_vf)
    cli.main([])
    assert fake_vf.flash_capture.call_count == 2


def test_dump_captures_writes_png_with_timestamp_filename(monkeypatch, tmp_path):
    """The --dump-captures-to flag writes PNGs named by the metadata timestamp."""
    monkeypatch.setattr(
        cli, "resolve_camera", lambda: cs.CameraChoice("/dev/x", "Cam")
    )

    np = pytest.importorskip("numpy")

    captured = []

    class _FakeCV2:
        def imwrite(self, path, image):
            captured.append((path, image.shape))
            Path(path).write_bytes(b"PNG-FAKE")
            return True

    # Make _dump_packet route through our fake by injecting it as the cv2 module.
    monkeypatch.setitem(sys.modules, "cv2", _FakeCV2())

    fake_vf = mock.MagicMock()
    fake_vf.__enter__ = mock.MagicMock(return_value=fake_vf)
    fake_vf.__exit__ = mock.MagicMock(return_value=False)
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    packet = vf.CapturePacket(
        image=image,
        metadata={
            "timestamp": "2026-05-14T12-00-00.000000Z",
            "camera": {"name": "Cam", "stable_id": "/dev/x"},
            "resolution": (10, 10),
            "trigger": "keyboard",
        },
    )

    events = iter(["trigger", "key-quit"])
    fake_vf.pump_once.side_effect = lambda **_: next(events)
    fake_vf.capture.return_value = packet

    monkeypatch.setattr(cli, "Viewfinder", lambda *a, **kw: fake_vf)
    rc = cli.main(["--dump-captures-to", str(tmp_path)])
    assert rc == cli.EXIT_OK
    files = list(tmp_path.glob("*.png"))
    assert len(files) == 1
    assert files[0].name == "2026-05-14T12-00-00.000000Z.png"
