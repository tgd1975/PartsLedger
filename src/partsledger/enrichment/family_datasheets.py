"""Static MPN-prefix → datasheet-URL fallback — TASK-047 (IDEA-008 Stage 3).

When Nexar returns nothing, this table supplies a known-good,
manufacturer-direct datasheet URL for the part families already present in
``inventory/parts/``. It codifies the ``WebSearch`` guess that IDEA-005's
``/inventory-add`` skill makes today.

Pure data — a module-level dict, no file I/O, no scraping, grep-able.
Extension is by hand-edit of :data:`_FAMILY_TABLE` in the same change that
adds a new part family to inventory. If even this misses, the caller leaves
the Datasheet cell empty (IDEA-008 *Fallback path*) — empty is honest, a
wrong URL rots silently.
"""

from __future__ import annotations

__all__ = ["lookup_family"]

# MPN prefix → manufacturer-direct datasheet URL. Keys are upper-case; the
# longest matching prefix wins so e.g. "LM386" never shadows "LM358". URLs
# must point at ti.com / microchip.com / st.com / … — never an aggregator.
_FAMILY_TABLE: dict[str, str] = {
    "LM358": "https://www.ti.com/lit/ds/symlink/lm358.pdf",
    "LM386": "https://www.ti.com/lit/ds/symlink/lm386.pdf",
    "TL08": "https://www.ti.com/lit/ds/symlink/tl084.pdf",
    "NE555": "https://www.ti.com/lit/ds/symlink/ne555.pdf",
    "LM555": "https://www.ti.com/lit/ds/symlink/lm555.pdf",
    "L7805": "https://www.st.com/resource/en/datasheet/l78.pdf",
    "L78": "https://www.st.com/resource/en/datasheet/l78.pdf",
    # PIC16F62x family (PIC16F627A/628A/648A) — Microchip DS40044.
    "PIC16F": "https://ww1.microchip.com/downloads/en/DeviceDoc/40044G.pdf",
    "PIC12F": "https://ww1.microchip.com/downloads/en/DeviceDoc/41190G.pdf",
}

# Pre-sort prefixes longest-first so the first startswith hit is the most
# specific family.
_PREFIXES_BY_SPECIFICITY = sorted(_FAMILY_TABLE, key=len, reverse=True)


def lookup_family(mpn: str) -> str | None:
    """Return the fallback datasheet URL for ``mpn``'s family, or ``None``.

    Prefix match is case-insensitive; the longest matching prefix wins.
    Empty / unknown input returns ``None`` without raising.
    """
    if not mpn or not mpn.strip():
        return None
    key = mpn.strip().upper()
    for prefix in _PREFIXES_BY_SPECIFICITY:
        if key.startswith(prefix):
            return _FAMILY_TABLE[prefix]
    return None
