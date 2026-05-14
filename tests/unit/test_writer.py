"""Unit tests for ``partsledger.inventory.writer``.

Covers every documented disposition (``inserted``, ``bumped``,
``metadata_updated``, ``no_op``), the atomic-rename guarantee, the
pre-flush lint integration, the four error contracts, and the
idempotency property.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.inventory.lint import InventoryLintError  # noqa: E402
from partsledger.inventory.writer import (  # noqa: E402
    MalformedPreStateError,
    SectionUnresolvableError,
    SourceShapeError,
    WriteResult,
    _upsert_row_at,
    upsert_row,
)

CLEAN_TEMPLATE = """\
# Inventory

## ICs

| Part   | Qty | Description | Datasheet            | Octopart            | Source | Notes |
| ------ | --- | ----------- | -------------------- | ------------------- | ------ | ----- |
| LM358N | 1   | Op-amp      | [LM358](https://x)   | [search](https://y) | manual |       |

## Sensors

| Part | Qty | Description | Datasheet | Octopart | Source | Notes |
| ---- | --- | ----------- | --------- | -------- | ------ | ----- |
"""


@pytest.fixture()
def inv_path(tmp_path: Path) -> Path:
    p = tmp_path / "INVENTORY.md"
    p.write_text(CLEAN_TEMPLATE)
    return p


def _call(part_id: str, qty_delta: int, *, path: Path, **kwargs) -> WriteResult:
    return _upsert_row_at(
        part_id,
        qty_delta,
        source=kwargs.pop("source", "manual"),
        section=kwargs.pop("section", None),
        cells=kwargs.pop("cells", None),
        path=path,
    )


class TestInsert:
    def test_new_part_into_named_section(self, inv_path: Path):
        result = _call("NE555N", 3, path=inv_path, section="ICs", cells={"Description": "Timer"})
        assert result == WriteResult(disposition="inserted", qty=3, section="ICs")
        text = inv_path.read_text()
        assert "| NE555N" in text
        assert "Timer" in text

    def test_new_part_with_none_section_uses_first_h2(self, inv_path: Path):
        result = _call("XX1", 1, path=inv_path, section=None)
        assert result.disposition == "inserted"
        assert result.section == "ICs"

    def test_alphabetical_insert(self, inv_path: Path):
        _call("AAA999", 1, path=inv_path, section="ICs")
        _call("MMM222", 1, path=inv_path, section="ICs")
        _call("ZZZ111", 1, path=inv_path, section="ICs")
        text = inv_path.read_text()
        lines = [line for line in text.splitlines() if line.startswith("| AAA") or line.startswith("| LM") or line.startswith("| MM") or line.startswith("| ZZ")]
        positions = [text.find(p) for p in ("AAA999", "LM358N", "MMM222", "ZZZ111")]
        assert positions == sorted(positions), f"rows out of order: {lines}"

    def test_insert_into_empty_section_drops_placeholder(self, inv_path: Path):
        result = _call("BME280", 1, path=inv_path, section="Sensors", cells={"Description": "T/H/P"})
        assert result.disposition == "inserted"
        assert result.section == "Sensors"
        text = inv_path.read_text()
        sensors_section = text.split("## Sensors", 1)[1]
        # The placeholder row had no data; it should not remain.
        assert "|      |     |             |" not in sensors_section


class TestBump:
    def test_existing_part_bumped(self, inv_path: Path):
        result = _call("LM358N", 2, path=inv_path)
        assert result == WriteResult(disposition="bumped", qty=3, section="ICs")
        assert "| LM358N | 3" in inv_path.read_text()

    def test_bump_idempotency_accumulates_qty(self, inv_path: Path):
        a = _call("LM358N", 1, path=inv_path)
        b = _call("LM358N", 1, path=inv_path)
        assert a.qty == 2
        assert b.qty == 3
        assert b.disposition == "bumped"


class TestMetadataUpdate:
    def test_only_cell_change_is_metadata_updated(self, inv_path: Path):
        result = _call("LM358N", 0, path=inv_path, cells={"Notes": "moved to drawer B"})
        assert result.disposition == "metadata_updated"
        assert result.qty == 1
        assert "moved to drawer B" in inv_path.read_text()


class TestNoOp:
    def test_no_qty_no_cell_diff_is_no_op(self, inv_path: Path):
        before = inv_path.read_text()
        result = _call("LM358N", 0, path=inv_path)
        assert result.disposition == "no_op"
        assert result.qty == 1
        # File contents should not change on a no_op call.
        assert inv_path.read_text() == before


class TestNegativeFinalQty:
    def test_negative_final_qty_does_not_raise(self, inv_path: Path):
        """The writer's job is to apply the delta; the caller is responsible."""
        result = _call("LM358N", -5, path=inv_path)
        assert result.disposition == "bumped"
        assert result.qty == -4


class TestExtraCells:
    def test_extra_keys_silently_ignored(self, inv_path: Path):
        result = _call(
            "LM358N",
            0,
            path=inv_path,
            cells={"Notes": "x", "NotAColumn": "y", "AnotherFake": "z"},
        )
        assert result.disposition == "metadata_updated"
        assert "NotAColumn" not in inv_path.read_text()


class TestSourceShape:
    def test_empty_source_raises(self, inv_path: Path):
        with pytest.raises(SourceShapeError):
            _call("Z1", 1, path=inv_path, source="", section="ICs")

    def test_whitespace_source_raises(self, inv_path: Path):
        with pytest.raises(SourceShapeError):
            _call("Z1", 1, path=inv_path, source="man ual", section="ICs")

    def test_mixed_case_source_raises(self, inv_path: Path):
        with pytest.raises(SourceShapeError):
            _call("Z1", 1, path=inv_path, source="Manual", section="ICs")

    def test_camera_source_accepted(self, inv_path: Path):
        result = _call(
            "Z1",
            1,
            path=inv_path,
            source="camera",
            section="ICs",
            cells={"Notes": "likely LM-series"},
        )
        assert result.disposition == "inserted"


class TestSectionUnresolvable:
    def test_unknown_named_section_raises(self, inv_path: Path):
        with pytest.raises(SectionUnresolvableError):
            _call("Z1", 1, path=inv_path, section="DoesNotExist")

    def test_empty_file_no_headings_raises(self, tmp_path: Path):
        p = tmp_path / "INVENTORY.md"
        p.write_text("# Inventory\n\nNo sections yet.\n")
        with pytest.raises(SectionUnresolvableError):
            _call("Z1", 1, path=p)


class TestMalformedPreState:
    def test_missing_file_raises(self, tmp_path: Path):
        p = tmp_path / "INVENTORY.md"
        with pytest.raises(MalformedPreStateError):
            _call("Z1", 1, path=p, section="ICs")


class TestPreFlushLint:
    def test_lint_failure_blocks_write(self, inv_path: Path):
        """When the post-state would fail the lint, the writer raises and
        does not write."""
        before = inv_path.read_text()
        with mock.patch(
            "partsledger.inventory.writer.lint_text",
            return_value=[mock.MagicMock(__str__=lambda s: "synthetic")],
        ):
            with pytest.raises(InventoryLintError):
                _call("ZZ1", 1, path=inv_path, section="ICs")
        # File must not have been written.
        assert inv_path.read_text() == before


class TestAtomicWrite:
    def test_replace_failure_leaves_pre_state(self, inv_path: Path):
        before = inv_path.read_text()
        with mock.patch("partsledger.inventory.writer.os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                _call("ZZ1", 1, path=inv_path, section="ICs")
        # File contents unchanged because os.replace was the failing step.
        assert inv_path.read_text() == before


class TestEnvVarResolver:
    def test_pl_inventory_path_env_used(self, inv_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PL_INVENTORY_PATH", str(inv_path))
        result = upsert_row("ZZ1", 1, source="manual", section="ICs")
        assert result.disposition == "inserted"
        assert "ZZ1" in inv_path.read_text()
