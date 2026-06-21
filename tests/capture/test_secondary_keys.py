"""Tests for the R / X / U secondary-key dispatch — TASK-037."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.capture.recognition_state import (  # noqa: E402
    RecognitionOverlay,
    RecognitionState,
)
from partsledger.recognition.undo import NothingToUndo, Reverted, UndoFailed  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class FakeCV2:
    FONT_HERSHEY_SIMPLEX = 0

    def putText(self, *a, **k):  # noqa: N802
        pass

    def resize(self, img, size):
        return img


def _overlay(clock=None):
    return RecognitionOverlay(clock=clock or Clock(), cv2_module=FakeCV2())


R, X, U = ord("r"), ord("x"), ord("u")


# ---------------------------------------------------------------------------
# R / X in Retry-or-abort


def test_r_retries_and_returns_to_idle():
    o = _overlay()
    o.show_retry_or_abort("too dark")
    fired = []
    res = o.handle_key(R, retry=lambda: fired.append("retry"))
    assert res.action == "retry"
    assert fired == ["retry"]
    assert o.state == RecognitionState.IDLE


def test_x_aborts_to_inventory_add():
    o = _overlay()
    o.show_retry_or_abort("too dark")
    fired = []
    res = o.handle_key(X, abort=lambda: fired.append("abort"))
    assert res.action == "abort"
    assert fired == ["abort"]
    assert o.state == RecognitionState.IDLE


# ---------------------------------------------------------------------------
# U during / after the confirmation flash


def test_u_undoes_during_flash_reverted():
    o = _overlay()
    o.flash_confirmation("Saved as LM358N")
    res = o.handle_key(U, undo=lambda: Reverted(part_id="lm358n"))
    assert res.action == "undo"
    assert res.detail == "reverted"


def test_u_undo_failed_surfaces():
    o = _overlay()
    o.flash_confirmation("Saved")
    res = o.handle_key(U, undo=lambda: UndoFailed(reason="md locked"))
    assert res.detail == "undo failed"


def test_u_nothing_to_undo():
    o = _overlay()
    o.flash_confirmation("Saved")
    res = o.handle_key(U, undo=lambda: NothingToUndo())
    assert res.detail == "nothing to undo"


def test_u_within_window_fires_after_flash_fades():
    clock = Clock()
    o = _overlay(clock=clock)
    o.flash_confirmation("Saved")
    clock.t = 4.0  # past the ~1 s flash, inside the ~5 s undo window
    res = o.handle_key(U, undo=lambda: Reverted(part_id="x"))
    assert res.action == "undo"


def test_u_after_window_is_ignored():
    clock = Clock()
    o = _overlay(clock=clock)
    o.flash_confirmation("Saved")
    clock.t = 6.0  # past the 5 s window
    fired = []
    res = o.handle_key(U, undo=lambda: fired.append("undo") or Reverted("x"))
    assert res.action == "ignored"
    assert fired == []


def test_second_u_is_noop():
    o = _overlay()
    o.flash_confirmation("Saved")
    o.handle_key(U, undo=lambda: Reverted("x"))
    # The window was consumed; a second U does nothing.
    res = o.handle_key(U, undo=lambda: Reverted("x"))
    assert res.action == "ignored"


# ---------------------------------------------------------------------------
# wrong-state / reserved keys ignored silently


def test_r_x_in_idle_ignored():
    o = _overlay()
    assert o.handle_key(R).action == "ignored"
    assert o.handle_key(X).action == "ignored"


def test_u_in_idle_without_flash_ignored():
    o = _overlay()
    assert o.handle_key(U, undo=lambda: Reverted("x")).action == "ignored"


def test_digits_ignored_everywhere():
    o = _overlay()
    o.show_retry_or_abort("too dark")
    for d in range(ord("0"), ord("9") + 1):
        assert o.handle_key(d).action == "ignored"
    assert o.state == RecognitionState.RETRY_OR_ABORT  # unchanged


def test_unknown_key_ignored():
    o = _overlay()
    o.show_retry_or_abort("too dark")
    assert o.handle_key(ord("z")).action == "ignored"
