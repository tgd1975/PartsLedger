"""Unit tests for ``partsledger.inventory.family``.

Covers IDEA-005 § Stage 2 worked examples (the family-boundary
ground truth from IDEA-004) plus the helper functions used by
``/inventory-add`` and ``/inventory-page``.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.inventory.family import (  # noqa: E402
    family_sibling,
    find_sibling_pages,
    find_siblings,
)


# --------------------------------------------------------------------------
# family_sibling — IDEA-004 worked examples (the ground truth)
# --------------------------------------------------------------------------


class TestFamilySibling:
    def test_lm358p_and_lm358n_are_siblings(self):
        """LM358P / LM358N — common prefix LM358 (5), suffixes P / N."""
        assert family_sibling("LM358P", "LM358N") is True

    def test_lm358n_and_lm386n_are_not_siblings(self):
        """Common prefix LM3 (3 chars) fails the length gate."""
        assert family_sibling("LM358N", "LM386N") is False

    def test_lm358_and_lm2904_are_not_siblings(self):
        """Common prefix LM (2 chars) fails the length gate."""
        assert family_sibling("LM358", "LM2904") is False

    def test_lm358_and_lm3580_are_not_siblings(self):
        """Suffix-only divergence fails — remainder '0' is part of a new stem."""
        assert family_sibling("LM358", "LM3580") is False

    def test_lm358_and_lm358n_are_siblings(self):
        """Empty remainder against single-letter suffix is allowed."""
        assert family_sibling("LM358", "LM358N") is True

    def test_exact_match_is_not_a_sibling(self):
        assert family_sibling("LM358N", "LM358N") is False

    def test_case_insensitive(self):
        assert family_sibling("lm358n", "LM358P") is True

    def test_empty_input_is_not_a_sibling(self):
        assert family_sibling("", "LM358N") is False
        assert family_sibling("LM358N", "") is False

    def test_two_letter_two_digit_suffix_allowed(self):
        """Suffix can be letter + digit + letter (e.g. P5N)."""
        assert family_sibling("PIC16F628AP", "PIC16F628AT") is True

    def test_longer_alphanumeric_remainder_rejected(self):
        """Remainders that are themselves alphanumeric stems are not suffixes."""
        assert family_sibling("PIC16F628", "PIC16F876A") is False


# --------------------------------------------------------------------------
# find_siblings — order-preserving filter
# --------------------------------------------------------------------------


class TestFindSiblings:
    def test_returns_only_siblings(self):
        existing = ["LM358N", "NE555N", "TL082CP", "LM386N"]
        assert find_siblings("LM358P", existing) == ["LM358N"]

    def test_empty_list_returns_empty(self):
        assert find_siblings("LM358P", []) == []

    def test_order_is_preserved(self):
        existing = ["LM358Z", "LM358N", "LM358T"]
        assert find_siblings("LM358P", existing) == ["LM358Z", "LM358N", "LM358T"]


# --------------------------------------------------------------------------
# find_sibling_pages — filesystem-level lookup for /inventory-page
# --------------------------------------------------------------------------


class TestFindSiblingPages:
    def test_finds_existing_sibling_page(self, tmp_path: Path):
        parts = tmp_path / "parts"
        parts.mkdir()
        (parts / "lm358n.md").write_text("# LM358N")
        (parts / "ne555.md").write_text("# NE555")
        matches = find_sibling_pages("LM358P", parts)
        assert [p.name for p in matches] == ["lm358n.md"]

    def test_returns_empty_when_no_siblings(self, tmp_path: Path):
        parts = tmp_path / "parts"
        parts.mkdir()
        (parts / "ne555.md").write_text("# NE555")
        assert find_sibling_pages("LM358P", parts) == []

    def test_missing_parts_dir_returns_empty(self, tmp_path: Path):
        assert find_sibling_pages("LM358P", tmp_path / "does-not-exist") == []


# --------------------------------------------------------------------------
# Batched-add ordering case
# --------------------------------------------------------------------------


class TestBatchedAddOrdering:
    """Batched `/inventory-add LM358P 2, LM358N 3` against an empty
    inventory: first pair commits silently, second pair fires the
    suggestion against the just-committed first pair. The scan runs
    against post-commit state after each pair.

    This test simulates the scan loop the skill runs — the heuristic
    is the load-bearing primitive here; the skill is the orchestrator.
    """

    def test_first_pair_no_existing_siblings(self):
        assert find_siblings("LM358P", []) == []

    def test_second_pair_finds_first(self):
        # After first pair committed: existing = ["LM358P"]
        assert find_siblings("LM358N", ["LM358P"]) == ["LM358P"]
