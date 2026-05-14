"""Tests for the ``partsledger[resistor-reader]`` extra.

Covers:

- Import without the extras-only deps raises ``ImportError`` with
  the install hint.
- Import with the extras-only deps succeeds (skipped when the deps
  aren't installed in the dev env).
"""

from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _fresh_import_resistor_reader():
    """Force a fresh module import each time the test runs."""

    sys.modules.pop("partsledger.resistor_reader", None)
    return importlib.import_module("partsledger.resistor_reader")


def test_resistor_reader_missing_extra_raises_helpful_error(monkeypatch):
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name in {"skimage", "scipy"} or name.startswith(("skimage.", "scipy.")):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with pytest.raises(ImportError) as info:
        _fresh_import_resistor_reader()
    msg = str(info.value)
    assert "partsledger.resistor_reader" in msg
    assert "pip install" in msg
    assert "partsledger[resistor-reader]" in msg


def test_resistor_reader_imports_with_extra():
    """Skipped unless the extras-only deps are actually installed."""

    pytest.importorskip("skimage")
    pytest.importorskip("scipy")
    module = _fresh_import_resistor_reader()
    assert module is not None
