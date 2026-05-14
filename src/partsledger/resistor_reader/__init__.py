"""Resistor color-band reader — EPIC-008.

This subpackage is shipped as the ``partsledger[resistor-reader]``
PEP 517 extra. Importing it without the extra installed raises a
clear :class:`ImportError` instead of the default
:class:`ModuleNotFoundError` traceback.

The implementation lands in EPIC-008 (TASK-051..056). This file
exists today only to wire the extras-dependency check and produce
the install-hint error before any reader code is added.
"""

from __future__ import annotations

_INSTALL_HINT = (
    "partsledger.resistor_reader requires the [resistor-reader] extra: "
    "pip install 'partsledger[resistor-reader]'"
)


def _check_extras() -> None:
    """Raise :class:`ImportError` if the extras-only deps are missing."""

    missing: list[str] = []
    try:
        import skimage  # noqa: F401
    except ImportError:
        missing.append("scikit-image")
    try:
        import scipy  # noqa: F401
    except ImportError:
        missing.append("scipy")
    if missing:
        raise ImportError(
            f"{_INSTALL_HINT} (missing: {', '.join(missing)})"
        )


_check_extras()
