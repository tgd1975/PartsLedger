"""Tests for partsledger.recognition.undo — TASK-044."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.recognition.pipeline import WriteEntry  # noqa: E402
from partsledger.recognition.undo import (  # noqa: E402
    NothingToUndo,
    Reverted,
    UndoFailed,
    UndoJournal,
)


class FakeCache:
    def __init__(self):
        self.deleted = []

    def delete_row(self, row_id):
        self.deleted.append(row_id)
        return True


class FakeWriter:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def __call__(self, part_id, qty_delta, *, source):
        self.calls.append((part_id, qty_delta, source))
        if self.fail:
            raise RuntimeError("simulated MD failure")
        return None


def _entry(part_id="lm358n", row_id=1287, source="cache", qty_before=3):
    return WriteEntry(
        part_id=part_id,
        qty_before=qty_before,
        qty_after=qty_before + 1,
        cache_row_id=row_id,
        source=source,
        label=part_id.upper(),
    )


def _journal(tmp_path, cache, writer, depth=1):
    return UndoJournal(
        cache=cache,
        writer_upsert=writer,
        path=tmp_path / "undo.toml",
        depth=depth,
    )


# ---------------------------------------------------------------------------
# round-trip undo after cache hit


def test_undo_after_cache_hit_decrements_and_deletes(tmp_path):
    cache, writer = FakeCache(), FakeWriter()
    j = _journal(tmp_path, cache, writer)
    j.record(_entry(source="cache", row_id=1287))
    out = j.undo_last()
    assert isinstance(out, Reverted)
    assert out.part_id == "lm358n"
    assert writer.calls == [("lm358n", -1, "cache")]
    assert cache.deleted == [1287]


def test_undo_after_vlm_hit_same_path(tmp_path):
    cache, writer = FakeCache(), FakeWriter()
    j = _journal(tmp_path, cache, writer)
    j.record(_entry(source="vlm", row_id=99))
    out = j.undo_last()
    assert isinstance(out, Reverted)
    assert writer.calls == [("lm358n", -1, "vlm")]
    assert cache.deleted == [99]


# ---------------------------------------------------------------------------
# depth-1: second undo no-ops


def test_depth_one_second_undo_is_nothing(tmp_path):
    cache, writer = FakeCache(), FakeWriter()
    j = _journal(tmp_path, cache, writer)
    j.record(_entry())
    assert isinstance(j.undo_last(), Reverted)
    assert isinstance(j.undo_last(), NothingToUndo)


def test_recording_two_entries_keeps_only_last_at_depth_one(tmp_path):
    cache, writer = FakeCache(), FakeWriter()
    j = _journal(tmp_path, cache, writer)
    j.record(_entry(part_id="first", row_id=1))
    j.record(_entry(part_id="second", row_id=2))
    out = j.undo_last()
    assert isinstance(out, Reverted)
    assert out.part_id == "second"
    assert isinstance(j.undo_last(), NothingToUndo)


# ---------------------------------------------------------------------------
# persistence across process restart


def test_persistence_across_reopen(tmp_path):
    cache, writer = FakeCache(), FakeWriter()
    j1 = _journal(tmp_path, cache, writer)
    j1.record(_entry(part_id="persisted", row_id=42))
    # Simulated process B — fresh journal object, same file.
    j2 = _journal(tmp_path, cache, writer)
    out = j2.undo_last()
    assert isinstance(out, Reverted)
    assert out.part_id == "persisted"
    assert cache.deleted == [42]


# ---------------------------------------------------------------------------
# empty journal


def test_empty_journal_is_nothing_to_undo(tmp_path):
    j = _journal(tmp_path, FakeCache(), FakeWriter())
    assert isinstance(j.undo_last(), NothingToUndo)


# ---------------------------------------------------------------------------
# writer failure leaves a recoverable state


def test_writer_failure_leaves_cache_and_journal_intact(tmp_path):
    cache, writer = FakeCache(), FakeWriter(fail=True)
    j = _journal(tmp_path, cache, writer)
    j.record(_entry(row_id=7))
    out = j.undo_last()
    assert isinstance(out, UndoFailed)
    assert cache.deleted == []  # cache row untouched
    # Journal entry still there — a retry with a working writer reverts it.
    writer.fail = False
    out2 = j.undo_last()
    assert isinstance(out2, Reverted)
    assert cache.deleted == [7]
