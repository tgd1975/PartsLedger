"""CLI wrapper — `python -m partsledger.capture` — TASK-035.

Thin argparse layer over the library. Per IDEA-006 Stage 6: arguments,
signal handling, exit codes — no business logic.

Exit codes:
  0   clean exit
  1   camera not resolvable
  2   display backend unusable
  130 interrupted (SIGINT)
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Sequence

from .camera_select import (
    CameraChoiceUnresolved,
    resolve_camera,
    run_wizard,
)
from .viewfinder import (
    CameraLost,
    DisplayBackendUnavailable,
    Viewfinder,
)

EXIT_OK = 0
EXIT_CAMERA = 1
EXIT_DISPLAY = 2
EXIT_INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="partsledger.capture",
        description="USB camera capture viewfinder.",
    )
    p.add_argument(
        "--no-preview",
        action="store_true",
        help="Run without opening the cv2 window (scripted regression mode).",
    )
    p.add_argument(
        "--pick-camera",
        action="store_true",
        help="Force the camera-selection wizard to re-enter, even when a "
        "persisted choice still resolves.",
    )
    p.add_argument(
        "--dump-captures-to",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write each captured frame as a PNG into PATH (filename = the "
        "metadata timestamp). Default: off. Files are not cleaned up at "
        "session end — the whole point is post-session inspection.",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Resolve the camera. --pick-camera always forces the wizard.
    try:
        if args.pick_camera:
            choice = run_wizard()
        else:
            choice = resolve_camera()
    except CameraChoiceUnresolved:
        try:
            choice = run_wizard()
        except RuntimeError as exc:
            print(f"camera: {exc}", file=sys.stderr)
            return EXIT_CAMERA
    except RuntimeError as exc:
        print(f"camera: {exc}", file=sys.stderr)
        return EXIT_CAMERA

    if args.dump_captures_to is not None:
        args.dump_captures_to.mkdir(parents=True, exist_ok=True)

    # Install a clean SIGINT handler so Ctrl-C exits 130 with a clear message.
    def _on_sigint(_signum, _frame):
        # Propagate to the Viewfinder via its installed handler — but make sure
        # an early Ctrl-C (before the viewfinder owns the handler) still exits.
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, _on_sigint)

    try:
        return _run_session(choice, args)
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


def _run_session(choice, args) -> int:
    if args.no_preview:
        # Headless mode — no window, no per-frame pump. The flag exists so
        # downstream regression tests can drive the pipeline against
        # pre-recorded frames; the actual frame source is the caller's
        # problem (see test fixtures).
        return EXIT_OK

    try:
        viewfinder_cm = Viewfinder(
            choice.stable_id,
            friendly_name=choice.friendly_name,
        )
    except DisplayBackendUnavailable as exc:
        print(f"display: {exc}", file=sys.stderr)
        return EXIT_DISPLAY

    try:
        with viewfinder_cm as v:
            while True:
                event = v.pump_once(poll_key=True)
                if event in {"key-quit", "wm-close"}:
                    return EXIT_OK
                if event == "signal":
                    return EXIT_INTERRUPTED
                if event == "camera-lost":
                    print(
                        f"camera lost — {choice.friendly_name}",
                        file=sys.stderr,
                    )
                    return EXIT_CAMERA
                if event == "trigger":
                    packet = v.capture()
                    v.flash_capture()
                    if args.dump_captures_to is not None:
                        _dump_packet(args.dump_captures_to, packet)
    except DisplayBackendUnavailable as exc:
        print(f"display: {exc}", file=sys.stderr)
        return EXIT_DISPLAY
    except CameraLost as exc:
        print(f"camera: {exc}", file=sys.stderr)
        return EXIT_CAMERA


def _dump_packet(target_dir: Path, packet) -> None:
    """Write the captured frame as a PNG using the timestamp as filename."""
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        return
    ts = packet.metadata["timestamp"]
    path = target_dir / f"{ts}.png"
    cv2.imwrite(str(path), packet.image)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
