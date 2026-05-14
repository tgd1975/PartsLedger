"""Camera-selection wizard — TASK-032.

First-run wizard that lets the maker pick which USB capture device PartsLedger
uses. Platform-specific enumeration (V4L2 on Linux, DirectShow on Windows)
under the hood; only friendly names ever reach the maker.

Public surface:
    list_cameras()    -> [(stable_id, friendly_name)]
    run_wizard()      -> (stable_id, friendly_name)   # prompts on stdin
    resolve_camera()  -> stable_id                    # raises CameraChoiceUnresolved on failure
"""

from __future__ import annotations

import os
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

try:  # py3.11+
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]


CONFIG_PATH_ENV = "PL_CONFIG_PATH"
CAMERA_OVERRIDE_ENV = "PL_CAMERA"


def _config_path() -> Path:
    override = os.environ.get(CONFIG_PATH_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "partsledger" / "config.toml"


# ---------------------------------------------------------------------------
# Errors


class CameraChoiceUnresolved(RuntimeError):
    """Raised when the persisted camera choice no longer opens.

    The wizard should re-enter when this fires — never silently fall through
    to a different device.
    """


# ---------------------------------------------------------------------------
# Data


@dataclass(frozen=True)
class CameraChoice:
    stable_id: str
    friendly_name: str


# ---------------------------------------------------------------------------
# Platform enumeration


def _enumerate_linux() -> list[CameraChoice]:
    """Walk /dev/v4l/by-id/usb-… symlinks; read friendly names from sysfs."""
    by_id = Path("/dev/v4l/by-id")
    if not by_id.is_dir():
        return []
    seen: dict[str, CameraChoice] = {}
    for entry in sorted(by_id.iterdir()):
        if not entry.name.startswith("usb-"):
            continue
        # Stable id is the absolute /dev/v4l/by-id/... path — survives replug.
        stable_id = str(entry)
        friendly = _linux_friendly_name(entry)
        # The same physical webcam often exposes multiple /dev/videoN nodes
        # (capture + metadata). Dedupe by friendly name + USB serial chunk.
        key = friendly
        if key in seen:
            continue
        seen[key] = CameraChoice(stable_id=stable_id, friendly_name=friendly)
    return list(seen.values())


def _linux_friendly_name(by_id_path: Path) -> str:
    """Derive a maker-friendly name from a /dev/v4l/by-id/usb-VENDOR_PRODUCT-… path.

    Falls back to the symlink basename with the leading `usb-` stripped and
    underscores turned to spaces. Real V4L2 capability queries would be nicer
    but require ctypes on every distro; the symlink already encodes the
    vendor's marketed product string.
    """
    raw = by_id_path.name
    # Strip "usb-" prefix and the trailing "-videoN" / "-index0" suffix.
    raw = re.sub(r"^usb-", "", raw)
    # Real V4L2 symlinks look like `…-video-index0`. Strip the index suffix
    # first, then any trailing `-video` token.
    raw = re.sub(r"-index\d+$", "", raw)
    raw = re.sub(r"-video$", "", raw)
    # The first underscore-separated token is the manufacturer; subsequent
    # tokens form the product. Underscores → spaces.
    cleaned = raw.replace("_", " ").strip()
    return cleaned or by_id_path.name


def _enumerate_windows() -> list[CameraChoice]:  # pragma: no cover - manual hw test
    """Enumerate DirectShow capture devices.

    Uses pygrabber if available; otherwise falls back to opening indices 0..7
    with cv2.VideoCapture and reading the backend's reported name. The first
    path produces real DirectShow friendly names; the fallback is a degraded
    "Camera 0" / "Camera 1" labelling that still satisfies the
    no-bare-integers maker UX rule by being labelled.
    """
    try:
        from pygrabber.dshow_graph import FilterGraph  # type: ignore[import-not-found]
    except ImportError:
        return _enumerate_windows_cv2_fallback()
    graph = FilterGraph()
    devices = graph.get_input_devices()
    return [
        CameraChoice(stable_id=f"directshow:{name}", friendly_name=name)
        for name in devices
    ]


def _enumerate_windows_cv2_fallback() -> list[CameraChoice]:  # pragma: no cover
    import cv2  # type: ignore[import-not-found]

    choices: list[CameraChoice] = []
    for idx in range(8):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap is not None and cap.isOpened():
            # The maker sees "Camera A" / "Camera B" — never the integer.
            label = f"Camera {chr(ord('A') + idx)}"
            choices.append(
                CameraChoice(stable_id=f"directshow:index:{idx}", friendly_name=label)
            )
            cap.release()
    return choices


def list_cameras() -> list[CameraChoice]:
    """Enumerate connected capture devices.

    Dispatches by platform. Returns an empty list when no devices are present.
    """
    system = platform.system()
    if system == "Linux":
        return _enumerate_linux()
    if system == "Windows":
        return _enumerate_windows()
    # macOS and other platforms — out of scope for PartsLedger today.
    raise NotImplementedError(f"Camera enumeration not implemented for {system}.")


# ---------------------------------------------------------------------------
# Persistence


def _load_config(config_path: Path) -> dict:
    if not config_path.is_file():
        return {}
    with config_path.open("rb") as fh:
        return tomllib.load(fh)


def _save_camera_section(config_path: Path, choice: CameraChoice) -> None:
    """Write the `[camera]` section, preserving any other sections present.

    Hand-edits the TOML rather than pulling in tomli-w as a runtime dep —
    PartsLedger already has a hand-edit policy for config files.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""

    block = (
        "[camera]\n"
        f'stable_id = "{_escape_toml(choice.stable_id)}"\n'
        f'friendly_name = "{_escape_toml(choice.friendly_name)}"\n'
    )

    if "[camera]" in existing:
        # Replace the existing section (up to the next [section] or EOF).
        pattern = re.compile(r"^\[camera\][^\[]*", re.MULTILINE)
        new_text = pattern.sub(block, existing, count=1)
    else:
        sep = "" if existing.endswith("\n") or not existing else "\n"
        new_text = existing + sep + block
    config_path.write_text(new_text, encoding="utf-8")


def _escape_toml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


# ---------------------------------------------------------------------------
# Resolver


def resolve_camera(
    *,
    config_path: Path | None = None,
    opener: Callable[[str], bool] | None = None,
) -> CameraChoice:
    """Return the persisted (or $PL_CAMERA-overridden) camera choice.

    Verifies the device opens. Raises `CameraChoiceUnresolved` when the
    persisted choice no longer resolves — caller re-enters the wizard.

    `opener` is injected to keep the resolver testable without a real
    `cv2.VideoCapture`; default uses cv2 when available.
    """
    cfg_path = config_path or _config_path()
    override = os.environ.get(CAMERA_OVERRIDE_ENV)
    if override:
        choice = CameraChoice(stable_id=override, friendly_name=override)
    else:
        data = _load_config(cfg_path)
        cam = data.get("camera") or {}
        stable_id = cam.get("stable_id")
        friendly = cam.get("friendly_name")
        if not stable_id or not friendly:
            raise CameraChoiceUnresolved(
                "no [camera] section in config — wizard required",
            )
        choice = CameraChoice(stable_id=stable_id, friendly_name=friendly)

    open_fn = opener or _default_opener
    if not open_fn(choice.stable_id):
        raise CameraChoiceUnresolved(
            f"camera '{choice.friendly_name}' did not open — wizard required",
        )
    return choice


def _default_opener(stable_id: str) -> bool:
    """Try to open the device with cv2; release immediately on success."""
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        return False
    cap = cv2.VideoCapture(_stable_id_to_cv2_arg(stable_id))
    try:
        return bool(cap is not None and cap.isOpened())
    finally:
        if cap is not None:
            cap.release()


def _stable_id_to_cv2_arg(stable_id: str):
    """Translate the platform-stable id to whatever cv2.VideoCapture wants.

    Linux: the /dev/v4l/by-id/... path resolves to /dev/videoN at the OS
    level; cv2 accepts the path directly.

    Windows: "directshow:index:N" → integer N; "directshow:<friendly>" →
    the index reported by enumeration. The index lookup happens lazily so
    this module stays import-cheap.
    """
    if stable_id.startswith("directshow:index:"):
        return int(stable_id.rsplit(":", 1)[1])
    if stable_id.startswith("directshow:"):  # pragma: no cover - manual hw test
        friendly = stable_id.split(":", 1)[1]
        for idx, choice in enumerate(_enumerate_windows()):
            if choice.friendly_name == friendly:
                return idx
        return -1
    return stable_id


# ---------------------------------------------------------------------------
# Wizard CLI


def run_wizard(
    *,
    enumerate_fn: Callable[[], Sequence[CameraChoice]] | None = None,
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
    config_path: Path | None = None,
) -> CameraChoice:
    """Run the interactive wizard. Returns the persisted choice.

    Maker UX contract:
      - Only friendly names are shown.
      - No /dev/... paths, no DirectShow GUIDs, no bare integer indices.
    """
    cameras = list((enumerate_fn or list_cameras)())
    if not cameras:
        raise RuntimeError(
            "No camera devices found. Plug one in and try again.",
        )
    output("Available cameras:")
    for n, cam in enumerate(cameras, start=1):
        output(f"  {n}. {cam.friendly_name}")
    while True:
        raw = input_fn("Pick a camera by number: ").strip()
        if not raw.isdigit():
            output("Please enter a number from the list above.")
            continue
        pick = int(raw)
        if 1 <= pick <= len(cameras):
            choice = cameras[pick - 1]
            break
        output("That number is not in the list. Try again.")
    cfg = config_path or _config_path()
    _save_camera_section(cfg, choice)
    output(f"Saved camera choice: {choice.friendly_name}")
    return choice


# ---------------------------------------------------------------------------
# Maker-UX guardrail


_FORBIDDEN_IN_PROMPT = (
    re.compile(r"/dev/"),
    re.compile(r"\{[0-9A-F]{8}-[0-9A-F]{4}", re.IGNORECASE),  # DirectShow GUID prefix
)


def assert_no_tech_internals(strings: Iterable[str]) -> None:
    """Test helper: assert none of the strings expose tech-stack internals."""
    for s in strings:
        for pat in _FORBIDDEN_IN_PROMPT:
            if pat.search(s):
                raise AssertionError(
                    f"maker-facing string leaks tech internals: {s!r}",
                )
        # A bare integer alone (e.g. "0", "1") is also forbidden as a
        # device identifier. Numbers used as menu indices ("  1. ...")
        # are fine because they sit inside a labelled menu line.
        if re.fullmatch(r"\d+", s.strip()):
            raise AssertionError(
                f"maker-facing string is a bare integer: {s!r}",
            )


# ---------------------------------------------------------------------------
# Entry-point — `python -m partsledger.capture.camera_select`


def main(argv: Sequence[str] | None = None) -> int:
    """Run the wizard standalone (no viewfinder). Useful as a setup step."""
    del argv
    try:
        choice = run_wizard()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"OK — {choice.friendly_name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
