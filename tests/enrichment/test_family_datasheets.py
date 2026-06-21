"""Tests for partsledger.enrichment.family_datasheets — TASK-047."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.enrichment import family_datasheets as fd  # noqa: E402


@pytest.mark.parametrize(
    "mpn,host",
    [
        ("LM358N", "ti.com"),
        ("LM386N-1", "ti.com"),
        ("TL082CP", "ti.com"),
        ("TL084IN", "ti.com"),
        ("NE555P", "ti.com"),
        ("L7805CV", "st.com"),
        ("PIC16F628A", "microchip.com"),
        ("PIC12F675", "microchip.com"),
    ],
)
def test_known_families_resolve_to_manufacturer_host(mpn, host):
    url = fd.lookup_family(mpn)
    assert url is not None
    assert host in url


def test_lm358_specific_url():
    assert fd.lookup_family("LM358N") == "https://www.ti.com/lit/ds/symlink/lm358.pdf"


def test_pic16f_family_url():
    assert fd.lookup_family("PIC16F628A") == (
        "https://ww1.microchip.com/downloads/en/DeviceDoc/40044G.pdf"
    )


def test_unknown_returns_none():
    assert fd.lookup_family("XYZ123") is None


def test_empty_returns_none():
    assert fd.lookup_family("") is None
    assert fd.lookup_family("   ") is None


def test_case_insensitive():
    assert fd.lookup_family("lm358n") == fd.lookup_family("LM358N")


def test_no_file_io_module_level_dict():
    assert isinstance(fd._FAMILY_TABLE, dict)
    assert len(fd._FAMILY_TABLE) >= 6
