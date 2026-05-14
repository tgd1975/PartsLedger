"""Live viewfinder + capture overlays — TASK-033.

`Viewfinder` is a context manager that owns the camera-device + cv2.imshow
window lifecycle. Per-frame overlays (framing rectangle, focus traffic light,
lighting indicator, trigger hint) are drawn on top of the live feed. Overlay
crashes disable the failing overlay for the rest of the session — they do
not kill the viewfinder.

Per IDEA-006 § Window lifecycle, three quit triggers all route through the
same try…finally cleanup:
  - `q` / Esc via cv2.waitKey
  - WM-close via cv2.getWindowProperty(WND_PROP_VISIBLE)
  - SIGINT / SIGTERM via signal handlers

Per IDEA-006 § Pipeline failure modes, ~5 consecutive frame-grab failures is
treated as "camera disappeared" — TASK-034 wires that exit path.
"""

from __future__ import annotations

import datetime as _dt
import logging
import signal
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors


class DisplayBackendUnavailable(RuntimeError):
    """cv2.imshow cannot create a window (no display / broken $DISPLAY)."""


class CameraLost(RuntimeError):
    """Repeated frame-grab failures — camera has disappeared."""


# ---------------------------------------------------------------------------
# Overlay primitives


@dataclass
class FramingRect:
    """Fixed working-distance rectangle the maker lines parts up against."""

    x: int = 160
    y: int = 120
    width: int = 320
    height: int = 240


@dataclass
class FocusReading:
    variance: float
    band: str  # "green" | "amber" | "red"


@dataclass
class LightingReading:
    mean_luminance: float
    clipped_fraction: float
    band: str  # "green" | "amber" | "red"


# Thresholds tuned for the 2K USB webcam at the canonical working distance.
# Calibration in practice is a later concern (IDEA-006 § Open questions).
FOCUS_GREEN_VARIANCE = 100.0
FOCUS_AMBER_VARIANCE = 30.0

LIGHTING_GREEN_MIN = 70.0
LIGHTING_GREEN_MAX = 200.0
LIGHTING_AMBER_MIN = 40.0
LIGHTING_AMBER_MAX = 230.0
LIGHTING_CLIP_FRACTION_AMBER = 0.02
LIGHTING_CLIP_FRACTION_RED = 0.10


def compute_focus(frame, *, _cv2=None) -> FocusReading:
    """Laplacian variance → green/amber/red band."""
    cv2 = _cv2 or _import_cv2()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if var >= FOCUS_GREEN_VARIANCE:
        band = "green"
    elif var >= FOCUS_AMBER_VARIANCE:
        band = "amber"
    else:
        band = "red"
    return FocusReading(variance=var, band=band)


def compute_lighting(frame) -> LightingReading:
    """Mean luminance + max-channel clip count → green/amber/red band."""
    import numpy as np  # local import keeps module import cheap

    luminance = frame.mean(axis=2) if frame.ndim == 3 else frame
    mean_lum = float(luminance.mean())
    # Per-pixel clip rate across the brightest channel.
    if frame.ndim == 3:
        brightest = frame.max(axis=2)
    else:
        brightest = frame
    clipped_fraction = float(np.mean(brightest >= 250))

    out_of_green = (
        mean_lum < LIGHTING_GREEN_MIN
        or mean_lum > LIGHTING_GREEN_MAX
        or clipped_fraction >= LIGHTING_CLIP_FRACTION_AMBER
    )
    out_of_amber = (
        mean_lum < LIGHTING_AMBER_MIN
        or mean_lum > LIGHTING_AMBER_MAX
        or clipped_fraction >= LIGHTING_CLIP_FRACTION_RED
    )
    if out_of_amber:
        band = "red"
    elif out_of_green:
        band = "amber"
    else:
        band = "green"
    return LightingReading(
        mean_luminance=mean_lum,
        clipped_fraction=clipped_fraction,
        band=band,
    )


def _import_cv2():
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "cv2 is required for the viewfinder. Install opencv-python.",
        ) from exc
    return cv2


# ---------------------------------------------------------------------------
# Overlay decorators


@dataclass
class OverlayState:
    """Tracks which overlays are disabled because they crashed earlier."""

    disabled: set[str] = field(default_factory=set)

    def is_disabled(self, name: str) -> bool:
        return name in self.disabled

    def disable(self, name: str) -> None:
        if name not in self.disabled:
            logger.warning("disabling overlay %s after error", name)
            self.disabled.add(name)


def draw_framing_rect(frame, rect: FramingRect, *, _cv2=None):
    cv2 = _cv2 or _import_cv2()
    cv2.rectangle(
        frame,
        (rect.x, rect.y),
        (rect.x + rect.width, rect.y + rect.height),
        (0, 255, 0),
        2,
    )
    return frame


def draw_focus_indicator(frame, reading: FocusReading, *, _cv2=None):
    cv2 = _cv2 or _import_cv2()
    color = _band_color(reading.band, _cv2=cv2)
    text = f"Focus {reading.variance:6.1f}"
    cv2.putText(
        frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
    )
    return frame


def draw_lighting_indicator(frame, reading: LightingReading, *, _cv2=None):
    cv2 = _cv2 or _import_cv2()
    color = _band_color(reading.band, _cv2=cv2)
    text = f"Light {reading.mean_luminance:5.1f} clip={reading.clipped_fraction:.2%}"
    cv2.putText(
        frame, text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
    )
    return frame


def draw_trigger_hint(frame, hint: str = "Press <Space> to capture", *, _cv2=None):
    cv2 = _cv2 or _import_cv2()
    h = frame.shape[0]
    cv2.putText(
        frame, hint, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
    )
    return frame


def draw_shutter_flash(frame, *, _cv2=None):
    """Paint a thick white border + 'Captured' label as a shutter-flash receipt."""
    cv2 = _cv2 or _import_cv2()
    h, w = frame.shape[:2]
    # Thick white border around the entire frame — the eye picks it up
    # even in peripheral vision.
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (255, 255, 255), 12)
    # Centered "Captured" label with a black outline for contrast against
    # bright backgrounds.
    text = "Captured"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.4
    thickness = 3
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    org = ((w - tw) // 2, (h + th) // 2)
    cv2.putText(frame, text, org, font, scale, (0, 0, 0), thickness + 3)
    cv2.putText(frame, text, org, font, scale, (255, 255, 255), thickness)
    return frame


def draw_overlay_off_breadcrumb(frame, disabled: Iterable[str], *, _cv2=None):
    cv2 = _cv2 or _import_cv2()
    items = sorted(disabled)
    if not items:
        return frame
    msg = f"overlay off: {', '.join(items)}"
    h = frame.shape[0]
    cv2.putText(
        frame, msg, (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1
    )
    return frame


def _band_color(band: str, *, _cv2):
    if band == "green":
        return (0, 255, 0)
    if band == "amber":
        return (0, 165, 255)
    return (0, 0, 255)


def apply_overlays(frame, state: OverlayState, rect: FramingRect, *, _cv2=None):
    """Apply every overlay; isolate failures per overlay.

    A crashing overlay is disabled for the rest of the session; the underlying
    frame still renders.
    """
    cv2 = _cv2 or _import_cv2()
    if not state.is_disabled("framing"):
        try:
            draw_framing_rect(frame, rect, _cv2=cv2)
        except Exception:  # noqa: BLE001 — isolation is the point
            state.disable("framing")
    if not state.is_disabled("focus"):
        try:
            reading = compute_focus(frame, _cv2=cv2)
            draw_focus_indicator(frame, reading, _cv2=cv2)
        except Exception:  # noqa: BLE001
            state.disable("focus")
    if not state.is_disabled("lighting"):
        try:
            reading = compute_lighting(frame)
            draw_lighting_indicator(frame, reading, _cv2=cv2)
        except Exception:  # noqa: BLE001
            state.disable("lighting")
    if not state.is_disabled("trigger_hint"):
        try:
            draw_trigger_hint(frame, _cv2=cv2)
        except Exception:  # noqa: BLE001
            state.disable("trigger_hint")
    draw_overlay_off_breadcrumb(frame, state.disabled, _cv2=cv2)
    return frame


# ---------------------------------------------------------------------------
# Viewfinder context manager


WINDOW_NAME = "PartsLedger Capture"
QUIT_KEYS = {ord("q"), 27}  # 'q' or <Esc>
SPACE_KEY = 32


@dataclass(frozen=True)
class CapturePacket:
    """The Output contract from IDEA-006 § Output contract."""

    image: Any  # np.ndarray (H, W, 3), BGR uint8 — declared loose to avoid hard numpy import
    metadata: dict


class Viewfinder(AbstractContextManager):
    """Context manager that owns one camera-window session.

    Parameters
    ----------
    stable_id:
        The camera identifier from `camera_select.resolve_camera()`.
    rect:
        Framing rectangle overlay. Default works for the canonical 640x480
        viewfinder; bigger frames just see the rectangle at the same
        absolute coordinates.
    capture_factory, window_factory:
        Injection points for tests — by default they call into cv2.
    """

    def __init__(
        self,
        stable_id: str,
        *,
        friendly_name: str = "",
        rect: FramingRect | None = None,
        capture_factory: Callable[[Any], Any] | None = None,
        window_factory: Callable[[str], None] | None = None,
        cv2_module: Any = None,
    ) -> None:
        self.stable_id = stable_id
        self.friendly_name = friendly_name or stable_id
        self.rect = rect or FramingRect()
        self._cv2 = cv2_module
        self._capture_factory = capture_factory
        self._window_factory = window_factory
        self._capture: Any = None
        self._window_open = False
        self._overlay_state = OverlayState()
        self._previous_sigint = None
        self._previous_sigterm = None
        self._interrupted = False
        self._last_frame = None
        self._consecutive_failures = 0
        self._failure_limit = 5
        # Shutter-flash receipt: when >0, the next pump frames paint a
        # white border + "Captured" overlay before normal overlays draw.
        # Phase-1 standalone receipt — TASK-036's richer recognition-result
        # flash will replace this once the pipeline exists.
        self._shutter_flash_frames = 0

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "Viewfinder":
        cv2 = self._cv2 or _import_cv2()
        self._cv2 = cv2
        self._capture = (self._capture_factory or cv2.VideoCapture)(
            _camera_arg(self.stable_id)
        )
        if not self._capture or not self._capture.isOpened():
            raise CameraLost(f"camera '{self.friendly_name}' did not open")
        try:
            (self._window_factory or cv2.namedWindow)(WINDOW_NAME)
        except Exception as exc:  # pragma: no cover - display-backend test only
            self._capture.release()
            raise DisplayBackendUnavailable(
                "cv2.imshow cannot create a window (no display / broken $DISPLAY)"
            ) from exc
        self._window_open = True
        self._install_signal_handlers()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._cleanup()

    # -- public surface ----------------------------------------------------

    @property
    def overlay_state(self) -> OverlayState:
        return self._overlay_state

    def pump_once(self, *, poll_key: bool = True) -> str | None:
        """Grab one frame, apply overlays, show it. Returns an event or None.

        Events: "key-quit", "wm-close", "signal", "camera-lost", "trigger".
        """
        cv2 = self._cv2
        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_limit:
                return "camera-lost"
            return None
        self._consecutive_failures = 0
        self._last_frame = frame
        apply_overlays(frame, self._overlay_state, self.rect, _cv2=cv2)
        if self._shutter_flash_frames > 0:
            draw_shutter_flash(frame, _cv2=cv2)
            self._shutter_flash_frames -= 1
        cv2.imshow(WINDOW_NAME, frame)
        if self._interrupted:
            return "signal"
        if poll_key:
            key = cv2.waitKey(1) & 0xFF
            if key in QUIT_KEYS:
                return "key-quit"
            if key == SPACE_KEY:
                return "trigger"
            if not _window_visible(cv2, WINDOW_NAME):
                return "wm-close"
        return None

    def latest_frame(self):
        """Most recent frame seen by `pump_once`. None until the first pump."""
        return self._last_frame

    def flash_capture(self, *, frames: int = 5) -> None:
        """Schedule a brief shutter-flash receipt on the next `frames` pumps.

        Pure visual confirmation that a capture registered. Independent of
        the recognition pipeline (TASK-036 will replace this with the
        verdict-bearing flash once EPIC-006 lands).
        """
        self._shutter_flash_frames = max(self._shutter_flash_frames, frames)

    def capture(self) -> CapturePacket:
        """Freeze the latest frame and emit the Output-contract packet.

        Raises RuntimeError if no frame has been pumped yet (caller must
        invoke pump_once at least once first).
        """
        frame = self._last_frame
        if frame is None:
            raise RuntimeError(
                "capture() called before any frame was read — pump_once first"
            )
        # The caller may keep using the viewfinder for subsequent captures;
        # hand out a copy so downstream writes (e.g. PNG encoding) cannot
        # mutate the live ring-buffer used by pump_once.
        try:
            image = frame.copy()
        except AttributeError:
            image = frame
        h, w = frame.shape[:2] if hasattr(frame, "shape") else (0, 0)
        metadata = {
            "timestamp": _now_iso8601(),
            "camera": {
                "name": self.friendly_name,
                "stable_id": self.stable_id,
            },
            "resolution": (w, h),
            "trigger": "keyboard",
        }
        return CapturePacket(image=image, metadata=metadata)

    # -- internals ---------------------------------------------------------

    def _cleanup(self) -> None:
        cv2 = self._cv2
        self._restore_signal_handlers()
        if self._capture is not None:
            try:
                self._capture.release()
            except Exception:  # noqa: BLE001
                logger.exception("VideoCapture.release() failed")
        if cv2 is not None and self._window_open:
            try:
                cv2.destroyAllWindows()
            except Exception:  # noqa: BLE001
                logger.exception("cv2.destroyAllWindows() failed")
        self._window_open = False

    def _install_signal_handlers(self) -> None:
        def on_signal(signum, _frame):
            self._interrupted = True
        try:
            self._previous_sigint = signal.signal(signal.SIGINT, on_signal)
            self._previous_sigterm = signal.signal(signal.SIGTERM, on_signal)
        except (ValueError, OSError):
            # Signal handlers must run on the main thread; tests on worker
            # threads silently skip this — the cleanup path still works.
            self._previous_sigint = None
            self._previous_sigterm = None

    def _restore_signal_handlers(self) -> None:
        if self._previous_sigint is not None:
            try:
                signal.signal(signal.SIGINT, self._previous_sigint)
            except (ValueError, OSError):
                pass
        if self._previous_sigterm is not None:
            try:
                signal.signal(signal.SIGTERM, self._previous_sigterm)
            except (ValueError, OSError):
                pass


def _window_visible(cv2, name: str) -> bool:
    try:
        return cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) >= 1
    except Exception:  # noqa: BLE001
        # The property check sometimes throws if the window was already torn
        # down by the WM — treat that as "not visible".
        return False


def _camera_arg(stable_id: str):
    """Translate the platform-stable id to the cv2.VideoCapture argument.

    Mirrors the equivalent logic in `camera_select._stable_id_to_cv2_arg` so
    the viewfinder is callable without a config file lookup.
    """
    if stable_id.startswith("directshow:index:"):
        return int(stable_id.rsplit(":", 1)[1])
    return stable_id


def _now_iso8601() -> str:
    """ISO 8601 timestamp suitable for filenames (no colons)."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.%fZ")
