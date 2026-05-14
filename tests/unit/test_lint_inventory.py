"""Unit tests for ``partsledger.inventory.lint``.

One positive (violation rejected) + negative (clean accepted) test per
invariant, plus a smoke test confirming the checked-in
``inventory/INVENTORY.md`` passes clean.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.inventory.lint import (  # noqa: E402
    InventoryLintError,
    lint_path,
    lint_text,
)


# --------------------------------------------------------------------------
# Fixtures — minimal valid + variants
# --------------------------------------------------------------------------

CLEAN_TABLE = """\
# Inventory

## ICs

| Part                    | Qty | Description     | Datasheet            | Octopart            | Source | Notes |
| ----------------------- | --- | --------------- | -------------------- | ------------------- | ------ | ----- |
| [7660S](parts/7660s.md) | 2   | Charge pump     | [DS](https://x.com)  | [search](https://y) | manual |       |
| LM358N                  | 1   | Op-amp          | [LM358](https://x)   | [search](https://y) | manual |       |
| NE555N                  | 3   | Timer           | [NE555](https://x)   | [search](https://y) | manual |       |
"""


# --------------------------------------------------------------------------
# Source-column shape
# --------------------------------------------------------------------------


class TestSourceShape:
    def test_clean_table_accepts_lowercase_token(self):
        diagnostics = lint_text(CLEAN_TABLE)
        assert [d for d in diagnostics if d.rule == "source-shape"] == []

    def test_empty_source_is_rejected(self):
        text = CLEAN_TABLE.replace("| manual |       |\n| LM358N", "|        |       |\n| LM358N", 1)
        diagnostics = lint_text(text)
        assert any(d.rule == "source-shape" for d in diagnostics)

    def test_mixed_case_is_rejected(self):
        text = CLEAN_TABLE.replace("| manual |       |\n| LM358N", "| Manual |       |\n| LM358N", 1)
        diagnostics = lint_text(text)
        assert any(d.rule == "source-shape" for d in diagnostics)

    def test_whitespace_only_is_rejected(self):
        bad = CLEAN_TABLE.replace(
            "| 1   | Op-amp          | [LM358](https://x)   | [search](https://y) | manual |       |",
            "| 1   | Op-amp          | [LM358](https://x)   | [search](https://y) |        |       |",
        )
        diagnostics = lint_text(bad)
        assert any(d.rule == "source-shape" for d in diagnostics)

    def test_unknown_lowercase_token_is_accepted(self):
        """No allow-list — `imported` is fine."""
        text = CLEAN_TABLE.replace("manual", "imported", 1)
        diagnostics = lint_text(text)
        assert [d for d in diagnostics if d.rule == "source-shape"] == []


# --------------------------------------------------------------------------
# Alphabetical row order
# --------------------------------------------------------------------------


class TestAlphabeticalOrder:
    def test_in_order_accepted(self):
        diagnostics = lint_text(CLEAN_TABLE)
        assert [d for d in diagnostics if d.rule == "alphabetical-order"] == []

    def test_out_of_order_rejected(self):
        bad = """\
# Inventory

## ICs

| Part   | Qty | Description | Datasheet            | Octopart            | Source | Notes |
| ------ | --- | ----------- | -------------------- | ------------------- | ------ | ----- |
| NE555N | 3   | Timer       | [NE555](https://x)   | [search](https://y) | manual |       |
| LM358N | 1   | Op-amp      | [LM358](https://x)   | [search](https://y) | manual |       |
"""
        diagnostics = lint_text(bad)
        assert any(d.rule == "alphabetical-order" for d in diagnostics)

    def test_linked_part_sorts_by_visible_text(self):
        """`[7660S](parts/7660s.md)` sorts as `7660S`, ahead of `LM358N`."""
        diagnostics = lint_text(CLEAN_TABLE)
        assert [d for d in diagnostics if d.rule == "alphabetical-order"] == []


# --------------------------------------------------------------------------
# Hedge language in Notes (camera path only)
# --------------------------------------------------------------------------


class TestHedgeLanguage:
    def test_camera_with_hedge_accepted(self):
        text = """\
## ICs

| Part   | Qty | Description | Datasheet     | Octopart    | Source | Notes               |
| ------ | --- | ----------- | ------------- | ----------- | ------ | ------------------- |
| LM358N | 1   | Op-amp      | [LM358](x://) | [search](y) | camera | likely LM358 family |
"""
        diagnostics = lint_text(text)
        assert [d for d in diagnostics if d.rule == "hedge-language"] == []

    def test_camera_without_hedge_rejected(self):
        text = """\
## ICs

| Part   | Qty | Description | Datasheet     | Octopart    | Source | Notes        |
| ------ | --- | ----------- | ------------- | ----------- | ------ | ------------ |
| LM358N | 1   | Op-amp      | [LM358](x://) | [search](y) | camera | LM358 family |
"""
        diagnostics = lint_text(text)
        assert any(d.rule == "hedge-language" for d in diagnostics)

    def test_manual_without_hedge_accepted(self):
        """Manual rows are not constrained — free-form Notes are fine."""
        text = """\
## ICs

| Part   | Qty | Description | Datasheet     | Octopart    | Source | Notes              |
| ------ | --- | ----------- | ------------- | ----------- | ------ | ------------------ |
| LM358N | 1   | Op-amp      | [LM358](x://) | [search](y) | manual | brought from drawer |
"""
        diagnostics = lint_text(text)
        assert [d for d in diagnostics if d.rule == "hedge-language"] == []

    def test_camera_with_empty_notes_accepted(self):
        text = """\
## ICs

| Part   | Qty | Description | Datasheet     | Octopart    | Source | Notes |
| ------ | --- | ----------- | ------------- | ----------- | ------ | ----- |
| LM358N | 1   | Op-amp      | [LM358](x://) | [search](y) | camera |       |
"""
        diagnostics = lint_text(text)
        assert [d for d in diagnostics if d.rule == "hedge-language"] == []


# --------------------------------------------------------------------------
# Parts-link correctness
# --------------------------------------------------------------------------


class TestPartsLink:
    def test_existing_link_accepted(self, tmp_path: Path):
        (tmp_path / "parts").mkdir()
        (tmp_path / "parts" / "lm358.md").write_text("# LM358")
        inv = tmp_path / "INVENTORY.md"
        inv.write_text("""\
## ICs

| Part                  | Qty | Description | Datasheet     | Octopart    | Source | Notes |
| --------------------- | --- | ----------- | ------------- | ----------- | ------ | ----- |
| [LM358](parts/lm358.md) | 1 | Op-amp      | [LM358](x://) | [search](y) | manual |       |
""")
        diagnostics = lint_path(inv)
        assert [d for d in diagnostics if d.rule == "parts-link"] == []

    def test_missing_link_target_rejected(self, tmp_path: Path):
        (tmp_path / "parts").mkdir()
        inv = tmp_path / "INVENTORY.md"
        inv.write_text("""\
## ICs

| Part                    | Qty | Description | Datasheet     | Octopart    | Source | Notes |
| ----------------------- | --- | ----------- | ------------- | ----------- | ------ | ----- |
| [MISSING](parts/missing.md) | 1 | Stub    | [DS](x://)    | [search](y) | manual |       |
""")
        diagnostics = lint_path(inv)
        assert any(d.rule == "parts-link" for d in diagnostics)


# --------------------------------------------------------------------------
# InventoryLintError integration (used by writer's pre-flush check)
# --------------------------------------------------------------------------


class TestInventoryLintError:
    def test_error_carries_diagnostics(self):
        bad = CLEAN_TABLE.replace("manual", "Manual", 1)
        diagnostics = lint_text(bad)
        with pytest.raises(InventoryLintError) as info:
            raise InventoryLintError(diagnostics)
        assert info.value.diagnostics == diagnostics
        assert "Manual" in str(info.value)


# --------------------------------------------------------------------------
# Smoke test — checked-in INVENTORY.md
# --------------------------------------------------------------------------


class TestCheckedInInventory:
    def test_repo_inventory_is_clean(self):
        inv = REPO_ROOT / "inventory" / "INVENTORY.md"
        diagnostics = lint_path(inv)
        assert diagnostics == [], "\n".join(str(d) for d in diagnostics)
