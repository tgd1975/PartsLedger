"""Tests for the capture trigger + single-still emit — TASK-034."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.capture import viewfinder as vf  # noqa: E402


np = pytest.importorskip("numpy")


# ---------------------------------------------------------------------------
# Trigger dispatch — pump_once returns "trigger" on <Space>


def test_pump_once_returns_trigger_on_space():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (True, _frame())
    fake_cv2 = _FakeCV2()
    fake_cv2.next_key = vf.SPACE_KEY
    with vf.Viewfinder(
        "/dev/fake",
        friendly_name="Test Cam",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        assert v.pump_once(poll_key=True) == "trigger"


# ---------------------------------------------------------------------------
# Capture packet contract


def test_capture_packet_shape_and_metadata():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    frame = _frame()
    fake_capture.read.return_value = (True, frame)
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/v4l/by-id/usb-Test_Cam-video-index0",
        friendly_name="Test Cam",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        v.pump_once(poll_key=False)
        packet = v.capture()

    assert packet.image.shape == (480, 640, 3)
    assert packet.image.dtype == np.uint8
    md = packet.metadata
    assert md["camera"]["name"] == "Test Cam"
    assert md["camera"]["stable_id"] == "/dev/v4l/by-id/usb-Test_Cam-video-index0"
    assert md["resolution"] == (640, 480)
    assert md["trigger"] == "keyboard"
    # ISO 8601 in UTC, filesystem-safe form (no colons).
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d+Z", md["timestamp"]
    )


def test_capture_image_is_not_a_stale_buffer():
    """Each capture must return the *most recent* frame, not a reused reference."""
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    frame_a = _frame(fill=10)
    frame_b = _frame(fill=200)
    fake_capture.read.side_effect = [(True, frame_a), (True, frame_b)]
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/fake",
        friendly_name="Cam",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        v.pump_once(poll_key=False)
        first = v.capture()
        v.pump_once(poll_key=False)
        second = v.capture()
    assert first.image.mean() != second.image.mean()
    h1 = hash(first.image.tobytes())
    h2 = hash(second.image.tobytes())
    assert h1 != h2
    assert h1 != 0 and h2 != 0


def test_capture_packet_is_a_copy_not_a_view():
    """Mutating the returned image must not change the next capture."""
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    frame = _frame(fill=50)
    fake_capture.read.return_value = (True, frame)
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/fake",
        friendly_name="Cam",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        v.pump_once(poll_key=False)
        packet = v.capture()
        packet.image.fill(255)
        v.pump_once(poll_key=False)
        again = v.capture()
    assert again.image.mean() != 255


def test_capture_before_pump_raises():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (True, _frame())
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/fake",
        friendly_name="Cam",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        with pytest.raises(RuntimeError):
            v.capture()


# ---------------------------------------------------------------------------
# Camera-lost exit path


def test_isolated_failures_dont_trigger_camera_lost():
    """4 failures interleaved with successes must not fire camera-lost."""
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.side_effect = [(False, None)] * 4 + [(True, _frame())] + [(False, None)] * 4
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/fake",
        friendly_name="Cam",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        for _ in range(9):
            assert v.pump_once(poll_key=False) != "camera-lost"


# ---------------------------------------------------------------------------
# Helpers


def _frame(fill: int = 0):
    arr = np.full((480, 640, 3), fill, dtype=np.uint8)
    return arr


class _FakeCV2:
    COLOR_BGR2GRAY = 6
    CV_64F = 6
    FONT_HERSHEY_SIMPLEX = 0
    WND_PROP_VISIBLE = 4

    def __init__(self):
        self.next_key = -1
        self.window_visible = True

    def cvtColor(self, frame, _code):
        return frame[..., 0] if frame.ndim == 3 else frame

    def Laplacian(self, _gray, _ddepth):
        class _L:
            def var(self_):
                return 100.0

        return _L()

    def rectangle(self, *_a, **_kw):
        return None

    def putText(self, *_a, **_kw):
        return None

    def imshow(self, *_a, **_kw):
        return None

    def waitKey(self, _delay):
        return self.next_key

    def getWindowProperty(self, _name, _prop):
        return 1.0 if self.window_visible else 0.0

    def namedWindow(self, _name):
        return None

    def destroyAllWindows(self):
        return None
