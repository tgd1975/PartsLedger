"""Tests for partsledger.capture.recognition_state — TASK-036.

The cv2 module and the clock are injected, so the four-state machine, the
per-state renderers, the hint tokeniser, and the flash timing run with no
camera and no real cv2.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.capture import recognition_state as rs  # noqa: E402
from partsledger.capture.recognition_state import (  # noqa: E402
    RecognitionOverlay,
    RecognitionState,
    tokenise_hint,
)

np = pytest.importorskip("numpy")


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class FakeCV2:
    FONT_HERSHEY_SIMPLEX = 0

    def __init__(self):
        self.texts = []
        self.resize_calls = 0

    def putText(self, frame, text, org, font, scale, color, thickness):  # noqa: N802
        self.texts.append(text)

    def resize(self, img, size):
        self.resize_calls += 1
        return np.zeros((size[1], size[0], 3), dtype=np.uint8)


def _frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)


def _overlay(clock=None, cv2=None, **kw):
    return RecognitionOverlay(clock=clock or Clock(), cv2_module=cv2 or FakeCV2(), **kw)


# ---------------------------------------------------------------------------
# transitions + idempotency


def test_starts_idle():
    assert _overlay().state == RecognitionState.IDLE


def test_transition_api_sets_states():
    o = _overlay()
    o.begin_analyzing(_frame())
    assert o.state == RecognitionState.ANALYZING
    o.show_retry_or_abort("too dark")
    assert o.state == RecognitionState.RETRY_OR_ABORT
    o.flash_confirmation("Saved as LM358N")
    assert o.state == RecognitionState.CONFIRMATION_FLASH
    o.return_to_idle()
    assert o.state == RecognitionState.IDLE


def test_set_state_idempotent():
    o = _overlay()
    payload = rs._IdlePayload(last_result="x")
    o.set_state(RecognitionState.IDLE, payload)
    first = o.payload
    # An equal-but-distinct payload must not replace the held instance.
    o.set_state(RecognitionState.IDLE, rs._IdlePayload(last_result="x"))
    assert o.payload is first


# ---------------------------------------------------------------------------
# per-state renderers


def test_analyzing_renders_status_and_thumbnail():
    cv2 = FakeCV2()
    o = _overlay(cv2=cv2)
    o.begin_analyzing(_frame())
    o.render(_frame(), live_frame=_frame())
    assert any("Identifying" in t for t in cv2.texts)
    assert cv2.resize_calls == 1  # live thumbnail composited


def test_analyzing_thumbnail_keeps_updating():
    cv2 = FakeCV2()
    o = _overlay(cv2=cv2)
    o.begin_analyzing(_frame())
    o.render(_frame(), live_frame=_frame())
    o.render(_frame(), live_frame=_frame())
    assert cv2.resize_calls == 2  # fresh thumbnail each frame while main is frozen


def test_retry_renders_hint_and_prompt():
    cv2 = FakeCV2()
    o = _overlay(cv2=cv2)
    o.show_retry_or_abort("glare on the marking", confidence_band="medium cache")
    o.render(_frame())
    joined = " | ".join(cv2.texts)
    assert "glare on the marking" in joined
    assert "R retry" in joined and "X abort" in joined
    assert "medium cache" in joined


def test_confirmation_flash_renders_via_vlm_and_undo():
    cv2 = FakeCV2()
    o = _overlay(cv2=cv2)
    o.flash_confirmation("Saved as LM358N - qty 5 -> 6", via_vlm=True)
    o.render(_frame())
    joined = " | ".join(cv2.texts)
    assert "Saved as LM358N" in joined
    assert "via VLM" in joined
    assert "U to undo" in joined


def test_idle_renders_last_result_breadcrumb():
    cv2 = FakeCV2()
    o = _overlay(cv2=cv2)
    o.return_to_idle(last_result="LM358N")
    o.render(_frame())
    assert any("LM358N" in t for t in cv2.texts)


# ---------------------------------------------------------------------------
# hint tokeniser


@pytest.mark.parametrize(
    "hint,family",
    [
        ("rotate 90", "angle"),
        ("too dark", "lighting"),
        ("image too blurry", "sharpness"),
        ("part is off-centre", "framing"),
        ("reflective surface - try a matte mat", "surface"),
        ("too far away", "distance"),
        ("marking worn", "marking"),
    ],
)
def test_tokeniser_seven_families(hint, family):
    fam, display = tokenise_hint(hint)
    assert fam == family
    assert display == hint


def test_tokeniser_unknown_collapses_to_generic():
    fam, display = tokenise_hint("flibberty gibbet")
    assert fam == "generic"
    assert display == rs.GENERIC_HINT


# ---------------------------------------------------------------------------
# flash timing


def test_flash_auto_times_out_to_idle():
    clock = Clock()
    o = _overlay(clock=clock, flash_duration=1.0)
    o.flash_confirmation("Saved")
    clock.t = 0.5
    o.tick()
    assert o.state == RecognitionState.CONFIRMATION_FLASH  # still flashing
    clock.t = 1.5
    o.tick()
    assert o.state == RecognitionState.IDLE
    assert o.payload.last_result == "Saved"


def test_undo_window_outlives_flash():
    clock = Clock()
    o = _overlay(clock=clock, flash_duration=1.0, undo_window=5.0)
    o.flash_confirmation("Saved")
    clock.t = 2.0  # flash faded, but undo window (5 s) still open
    o.tick()
    assert o.state == RecognitionState.IDLE
    assert o.is_undo_window_open() is True
    clock.t = 6.0
    assert o.is_undo_window_open() is False
