"""Tests for partsledger.capture.viewfinder — TASK-033."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.capture import viewfinder as vf  # noqa: E402


np = pytest.importorskip("numpy")


# ---------------------------------------------------------------------------
# Overlay primitive logic — independent of cv2


def test_compute_focus_bands_split_correctly():
    """Laplacian variance → green/amber/red, threshold-driven."""
    cv2_stub = _FakeCV2(laplacian_variance=200.0)
    frame = _fake_frame()
    out = vf.compute_focus(frame, _cv2=cv2_stub)
    assert out.band == "green"

    cv2_stub.laplacian_variance = 50.0
    assert vf.compute_focus(frame, _cv2=cv2_stub).band == "amber"

    cv2_stub.laplacian_variance = 10.0
    assert vf.compute_focus(frame, _cv2=cv2_stub).band == "red"


def test_compute_lighting_green_band_when_mid_brightness():
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    reading = vf.compute_lighting(frame)
    assert reading.band == "green"


def test_compute_lighting_amber_when_too_dark():
    frame = np.full((100, 100, 3), 30, dtype=np.uint8)
    reading = vf.compute_lighting(frame)
    assert reading.band in {"amber", "red"}
    assert reading.mean_luminance < vf.LIGHTING_GREEN_MIN


def test_compute_lighting_red_on_severe_clipping():
    """A frame that's 100% blown highlights — should hit the red band."""
    frame = np.full((100, 100, 3), 255, dtype=np.uint8)
    reading = vf.compute_lighting(frame)
    assert reading.band == "red"
    assert reading.clipped_fraction >= vf.LIGHTING_CLIP_FRACTION_RED


# ---------------------------------------------------------------------------
# Overlay isolation — a crashing overlay must not kill the session


def test_overlay_state_tracks_disabled():
    state = vf.OverlayState()
    state.disable("focus")
    assert state.is_disabled("focus")
    state.disable("focus")  # idempotent
    assert state.disabled == {"focus"}


def test_apply_overlays_isolates_a_crashing_decorator(monkeypatch):
    """If compute_focus raises, the focus overlay is disabled and the rest still render."""
    state = vf.OverlayState()
    frame = _fake_frame()
    cv2_stub = _FakeCV2(laplacian_variance=200.0)

    def boom(*_args, **_kw):
        raise RuntimeError("focus computer exploded")

    monkeypatch.setattr(vf, "compute_focus", boom)
    monkeypatch.setattr(
        vf, "compute_lighting", lambda f: vf.LightingReading(mean_luminance=128, clipped_fraction=0.0, band="green")
    )
    vf.apply_overlays(frame, state, vf.FramingRect(), _cv2=cv2_stub)
    assert state.is_disabled("focus")
    # framing, lighting, trigger_hint still applied — none of them were disabled.
    assert "framing" not in state.disabled
    assert "lighting" not in state.disabled
    assert "trigger_hint" not in state.disabled


# ---------------------------------------------------------------------------
# Context manager lifecycle — cleanup guaranteed


def test_viewfinder_enter_releases_on_exception():
    """If namedWindow fails, the capture is released and re-raised as DisplayBackendUnavailable."""
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_cv2 = _FakeCV2()

    def boom_window(_name):
        raise RuntimeError("no display")

    with pytest.raises(vf.DisplayBackendUnavailable):
        with vf.Viewfinder(
            "/dev/fake",
            capture_factory=lambda _arg: fake_capture,
            window_factory=boom_window,
            cv2_module=fake_cv2,
        ):
            pytest.fail("should not enter the body")
    fake_capture.release.assert_called_once()


def test_viewfinder_cleanup_releases_on_normal_exit():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/fake",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        assert v.stable_id == "/dev/fake"
    fake_capture.release.assert_called_once()
    fake_cv2.destroy_all_called.assert_called_once()


def test_viewfinder_cleanup_releases_on_body_exception():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_cv2 = _FakeCV2()
    with pytest.raises(ValueError):
        with vf.Viewfinder(
            "/dev/fake",
            capture_factory=lambda _arg: fake_capture,
            window_factory=lambda _name: None,
            cv2_module=fake_cv2,
        ):
            raise ValueError("body explodes")
    fake_capture.release.assert_called_once()
    fake_cv2.destroy_all_called.assert_called_once()


def test_viewfinder_raises_when_capture_doesnt_open():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = False
    with pytest.raises(vf.CameraLost):
        with vf.Viewfinder(
            "/dev/fake",
            capture_factory=lambda _arg: fake_capture,
            window_factory=lambda _name: None,
            cv2_module=_FakeCV2(),
        ):
            pytest.fail("should not enter the body")


# ---------------------------------------------------------------------------
# pump_once — frame grab loop and quit signals


def test_pump_once_returns_camera_lost_after_five_failures():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (False, None)
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/fake",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        for _ in range(4):
            assert v.pump_once(poll_key=False) is None
        assert v.pump_once(poll_key=False) == "camera-lost"


def test_pump_once_swallows_single_frame_failures():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_frame = _fake_frame()
    # 3 failures interleaved with successes — should never hit 5 consecutive.
    fake_capture.read.side_effect = [
        (False, None),
        (True, fake_frame),
        (False, None),
        (True, fake_frame),
        (False, None),
        (True, fake_frame),
    ]
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/fake",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        for _ in range(6):
            assert v.pump_once(poll_key=False) is None


def test_pump_once_reports_key_quit():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (True, _fake_frame())
    fake_cv2 = _FakeCV2()
    fake_cv2.next_key = ord("q")
    with vf.Viewfinder(
        "/dev/fake",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        assert v.pump_once(poll_key=True) == "key-quit"


def test_pump_once_reports_wm_close():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (True, _fake_frame())
    fake_cv2 = _FakeCV2()
    fake_cv2.window_visible = False
    with vf.Viewfinder(
        "/dev/fake",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        assert v.pump_once(poll_key=True) == "wm-close"


def test_flash_capture_draws_shutter_overlay_for_n_frames():
    """After flash_capture(), the next N pumps paint the shutter overlay."""
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (True, _fake_frame())
    fake_cv2 = _FakeCV2()
    flash_calls = mock.MagicMock()

    with vf.Viewfinder(
        "/dev/fake",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        with mock.patch.object(vf, "draw_shutter_flash", flash_calls):
            v.pump_once(poll_key=False)
            assert flash_calls.call_count == 0
            v.flash_capture(frames=3)
            v.pump_once(poll_key=False)
            v.pump_once(poll_key=False)
            v.pump_once(poll_key=False)
            assert flash_calls.call_count == 3
            v.pump_once(poll_key=False)
            # 4th pump: counter exhausted, no further flash.
            assert flash_calls.call_count == 3


def test_pump_once_reports_signal_interrupt():
    fake_capture = mock.MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (True, _fake_frame())
    fake_cv2 = _FakeCV2()
    with vf.Viewfinder(
        "/dev/fake",
        capture_factory=lambda _arg: fake_capture,
        window_factory=lambda _name: None,
        cv2_module=fake_cv2,
    ) as v:
        v._interrupted = True
        assert v.pump_once(poll_key=False) == "signal"


# ---------------------------------------------------------------------------
# Helpers


def _fake_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)


class _FakeCV2:
    """Minimal cv2 stand-in — only the symbols the viewfinder touches."""

    COLOR_BGR2GRAY = 6
    CV_64F = 6
    FONT_HERSHEY_SIMPLEX = 0
    WND_PROP_VISIBLE = 4

    def __init__(self, *, laplacian_variance: float = 100.0):
        self.laplacian_variance = laplacian_variance
        self.window_visible = True
        self.next_key = -1
        self.destroy_all_called = mock.MagicMock()

    def cvtColor(self, frame, _code):
        return frame[..., 0] if frame.ndim == 3 else frame

    def Laplacian(self, _gray, _ddepth):
        class _L:
            def __init__(self, v):
                self._v = v

            def var(self):
                return self._v

        return _L(self.laplacian_variance)

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
        self.destroy_all_called()

    def VideoCapture(self, _arg):  # pragma: no cover - injection bypasses this
        raise AssertionError("tests should inject capture_factory")
