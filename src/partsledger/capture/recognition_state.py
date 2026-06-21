"""Recognition-status overlay state machine + secondary keys — TASK-036/037.

IDEA-006 Stage 4 (the four-state overlay machine) and Stage 5 (the contextual
``R`` / ``X`` / ``U`` key dispatch). The viewfinder doubles as the
recognition-status surface: every state of the recognition flow renders on
the same window the maker is already looking at.

This module owns the *renderer + dispatch* side of the contract; EPIC-006's
pipeline (TASK-043) owns the verdict payload and calls the transition API
(:meth:`begin_analyzing` / :meth:`show_retry_or_abort` /
:meth:`flash_confirmation` / :meth:`return_to_idle`). The viewfinder never
inspects a verdict — it renders what it is told.

Everything is injected (``cv2`` module, ``clock``) so the state transitions,
the seven-family hint tokeniser (shared with
:func:`partsledger.recognition.hints.classify_hint`), the flash / undo
timing, and the key dispatch are unit-testable with no camera and no real
cv2. The final rendering-quality + timing check is the task's
``human-in-loop: Support`` manual hardware step.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from ..recognition.hints import GENERIC_HINT, classify_hint

__all__ = [
    "RecognitionState",
    "KeyResult",
    "RecognitionOverlay",
    "tokenise_hint",
]


class RecognitionState(Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    RETRY_OR_ABORT = "retry_or_abort"
    CONFIRMATION_FLASH = "confirmation_flash"


def tokenise_hint(hint: str) -> tuple[str, str]:
    """Return ``(family, display_hint)`` for a VLM re-frame hint.

    Thin wrapper over :func:`partsledger.recognition.hints.classify_hint`:
    a recognised hint keeps its text; an unrecognised one collapses to the
    generic *"image unclear — recompose and retry"* string.
    """
    family = classify_hint(hint)
    display = hint.strip() if family != "generic" else GENERIC_HINT
    return family, display


@dataclass(frozen=True)
class KeyResult:
    """Outcome of a secondary-key press (TASK-037)."""

    action: str  # "retry" | "abort" | "undo" | "ignored"
    detail: str = ""  # e.g. "reverted" / "undo failed" for undo


@dataclass
class _FlashPayload:
    text: str
    via_vlm: bool = False
    started_at: float = 0.0


@dataclass
class _AnalyzingPayload:
    frozen_frame: Any = None


@dataclass
class _RetryPayload:
    family: str = "generic"
    display_hint: str = GENERIC_HINT
    confidence_band: str = ""
    frozen_frame: Any = None


@dataclass
class _IdlePayload:
    last_result: str = ""


class RecognitionOverlay:
    """Four-state recognition overlay + state-gated secondary keys.

    Parameters
    ----------
    flash_duration:
        Seconds the *Confirmation flash* text stays before auto-timeout
        back to *Idle* (~1 s).
    undo_window:
        Seconds after a flash starts during which ``U`` still reverts the
        write (~5 s); the corner *U-to-undo* hint persists this long.
    clock, cv2_module:
        Injected for deterministic tests.
    """

    def __init__(
        self,
        *,
        flash_duration: float = 1.0,
        undo_window: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
        cv2_module: Any = None,
    ) -> None:
        self._flash_duration = flash_duration
        self._undo_window = undo_window
        self._clock = clock
        self._cv2 = cv2_module
        self._state = RecognitionState.IDLE
        self._payload: Any = _IdlePayload()
        # Tracks the most recent flash so the U-window can outlive the flash
        # text (the maker has ~5 s to undo even after the flash fades to idle).
        self._flash_started_at: float | None = None

    # -- state ------------------------------------------------------------

    @property
    def state(self) -> RecognitionState:
        return self._state

    @property
    def payload(self) -> Any:
        return self._payload

    def set_state(self, state: RecognitionState, payload: Any) -> None:
        """Generic transition. Idempotent: re-entering a state with an equal
        payload is a no-op (no renderer thrash)."""
        if state == self._state and payload == self._payload:
            return
        self._state = state
        self._payload = payload

    # -- transition API (called by the TASK-043 pipeline) -----------------

    def begin_analyzing(self, captured_frame: Any) -> None:
        self.set_state(RecognitionState.ANALYZING, _AnalyzingPayload(frozen_frame=captured_frame))

    def show_retry_or_abort(
        self, hint: str, *, confidence_band: str = "", captured_frame: Any = None
    ) -> None:
        family, display = tokenise_hint(hint)
        self.set_state(
            RecognitionState.RETRY_OR_ABORT,
            _RetryPayload(
                family=family,
                display_hint=display,
                confidence_band=confidence_band,
                frozen_frame=captured_frame,
            ),
        )

    def flash_confirmation(self, text: str, *, via_vlm: bool = False) -> None:
        now = self._clock()
        self._flash_started_at = now
        self.set_state(
            RecognitionState.CONFIRMATION_FLASH,
            _FlashPayload(text=text, via_vlm=via_vlm, started_at=now),
        )

    def return_to_idle(self, *, last_result: str = "") -> None:
        self.set_state(RecognitionState.IDLE, _IdlePayload(last_result=last_result))

    # -- timing -----------------------------------------------------------

    def is_flash_expired(self) -> bool:
        """True once the flash has outlived ``flash_duration``."""
        if self._state != RecognitionState.CONFIRMATION_FLASH:
            return False
        return (self._clock() - self._payload.started_at) > self._flash_duration

    def tick(self) -> None:
        """Auto-timeout the confirmation flash back to idle when expired.

        The viewfinder calls this each frame. The U-window outlives the
        flash (tracked separately), so undo still works for ~5 s after.
        """
        if self.is_flash_expired():
            last = self._payload.text
            self.return_to_idle(last_result=last)

    def is_undo_window_open(self) -> bool:
        if self._flash_started_at is None:
            return False
        return (self._clock() - self._flash_started_at) <= self._undo_window

    # -- secondary key dispatch (TASK-037) --------------------------------

    def handle_key(
        self,
        key: int,
        *,
        retry: Callable[[], Any] | None = None,
        abort: Callable[[], Any] | None = None,
        undo: Callable[[], Any] | None = None,
    ) -> KeyResult:
        """Dispatch a contextual key. Wrong-state / unknown keys are silently
        ignored (no error overlay, no beep). Numeric digits are reserved for a
        future top-N picker and ignored everywhere."""
        ch = chr(key).lower() if 0 <= key < 0x110000 else ""

        if ch == "r" and self._state == RecognitionState.RETRY_OR_ABORT:
            if retry is not None:
                retry()
            self.return_to_idle()
            return KeyResult(action="retry")

        if ch == "x" and self._state == RecognitionState.RETRY_OR_ABORT:
            if abort is not None:
                abort()
            self.return_to_idle()
            return KeyResult(action="abort")

        if ch == "u" and self.is_undo_window_open():
            detail = "undo failed"
            if undo is not None:
                outcome = undo()
                detail = _describe_undo(outcome)
            # Surface the result on the viewfinder.
            self.flash_confirmation(detail)
            # An undo consumes the window so a second U is a no-op.
            self._flash_started_at = None
            return KeyResult(action="undo", detail=detail)

        return KeyResult(action="ignored")

    # -- rendering --------------------------------------------------------

    def render(self, frame: Any, *, live_frame: Any = None) -> Any:
        """Composite the current state's overlay onto ``frame`` in place."""
        cv2 = self._cv2 or _import_cv2()
        if self._state == RecognitionState.ANALYZING:
            return self._render_analyzing(frame, live_frame, cv2)
        if self._state == RecognitionState.RETRY_OR_ABORT:
            return self._render_retry(frame, cv2)
        if self._state == RecognitionState.CONFIRMATION_FLASH:
            return self._render_flash(frame, cv2)
        return self._render_idle(frame, cv2)

    def _render_idle(self, frame: Any, cv2: Any) -> Any:
        last = getattr(self._payload, "last_result", "")
        if last:
            _text(cv2, frame, f"last: {last}", (10, 20), 0.5, (200, 200, 200))
        return frame

    def _render_analyzing(self, frame: Any, live_frame: Any, cv2: Any) -> Any:
        _text(cv2, frame, "Identifying...", (10, 30), 0.7, (0, 255, 255))
        if live_frame is not None:
            _composite_thumbnail(cv2, frame, live_frame)
        return frame

    def _render_retry(self, frame: Any, cv2: Any) -> Any:
        p = self._payload
        _text(cv2, frame, p.display_hint, (10, 30), 0.6, (0, 165, 255))
        if p.confidence_band:
            _text(cv2, frame, p.confidence_band, (10, 55), 0.5, (200, 200, 200))
        h = frame.shape[0]
        _text(cv2, frame, "R retry  -  X abort", (10, h - 15), 0.6, (255, 255, 255))
        return frame

    def _render_flash(self, frame: Any, cv2: Any) -> Any:
        p = self._payload
        label = p.text + ("  (via VLM)" if p.via_vlm else "")
        _text(cv2, frame, label, (10, 30), 0.7, (0, 255, 0))
        if self.is_undo_window_open():
            h = frame.shape[0]
            _text(cv2, frame, "U to undo", (10, h - 15), 0.55, (255, 255, 255))
        return frame


# ---------------------------------------------------------------------------
# rendering helpers


def _import_cv2() -> Any:  # pragma: no cover - exercised only on real hardware
    import cv2  # type: ignore[import-not-found]

    return cv2


def _text(cv2: Any, frame: Any, text: str, org: tuple[int, int], scale: float, color) -> None:
    cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)


def _composite_thumbnail(cv2: Any, frame: Any, live_frame: Any, *, fraction: float = 0.25) -> None:
    """Paste a small live-feed thumbnail into the top-right corner.

    The main frame stays frozen during *Analyzing*; the thumbnail keeps
    updating from the live feed so the maker can still reframe the next part.
    """
    h, w = frame.shape[:2]
    tw, th = int(w * fraction), int(h * fraction)
    thumb = cv2.resize(live_frame, (tw, th))
    frame[0:th, w - tw : w] = thumb


def _describe_undo(outcome: Any) -> str:
    """Map a TASK-044 UndoOutcome to viewfinder text."""
    name = type(outcome).__name__
    if name == "Reverted":
        return "reverted"
    if name == "NothingToUndo":
        return "nothing to undo"
    return "undo failed"
