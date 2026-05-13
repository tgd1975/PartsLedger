"""Unit tests for release_burnup.py."""

from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import release_burnup as rb


class TestTshirtToHours(unittest.TestCase):
    def test_canonical_six(self):
        self.assertEqual(rb.tshirt_to_hours("XS (<30m)"), 0.25)
        self.assertEqual(rb.tshirt_to_hours("Small (<2h)"), 1.0)
        self.assertEqual(rb.tshirt_to_hours("Medium (2-8h)"), 5.0)
        self.assertEqual(rb.tshirt_to_hours("Large (8-24h)"), 16.0)
        self.assertEqual(rb.tshirt_to_hours("Extra Large (24-40h)"), 32.0)
        self.assertEqual(rb.tshirt_to_hours("XXL (>40h)"), 56.0)

    def test_legacy_labels(self):
        self.assertEqual(rb.tshirt_to_hours("Trivial (<30m)"), 0.25)
        self.assertEqual(rb.tshirt_to_hours("Small (1-2h)"), 1.0)
        self.assertEqual(rb.tshirt_to_hours("Small (1-3h)"), 1.0)
        self.assertEqual(rb.tshirt_to_hours("Small (2-4h)"), 1.0)
        self.assertEqual(rb.tshirt_to_hours("Large (>8h)"), 16.0)

    def test_unknown_or_missing(self):
        self.assertIsNone(rb.tshirt_to_hours(None))
        self.assertIsNone(rb.tshirt_to_hours(""))
        self.assertIsNone(rb.tshirt_to_hours("nonsense"))


class TestParseLogStream(unittest.TestCase):
    def test_single_closure(self):
        raw = (
            "COMMIT 2026-04-26\n"
            "docs/developers/tasks/closed/task-001-foo.md\n"
        )
        out = rb._parse_log_stream(raw)
        self.assertEqual(out, [("docs/developers/tasks/closed/task-001-foo.md",
                                "2026-04-26")])

    def test_multi_closure_per_commit(self):
        raw = (
            "COMMIT 2026-04-26\n"
            "docs/developers/tasks/closed/task-001.md\n"
            "docs/developers/tasks/closed/task-002.md\n"
            "docs/developers/tasks/closed/epic-005.md\n"
        )
        out = rb._parse_log_stream(raw)
        self.assertEqual(len(out), 3)
        self.assertTrue(all(d == "2026-04-26" for _, d in out))

    def test_multiple_commits(self):
        raw = (
            "COMMIT 2026-04-25\n"
            "docs/developers/tasks/closed/task-001.md\n"
            "\n"
            "COMMIT 2026-04-26\n"
            "docs/developers/tasks/closed/task-002.md\n"
        )
        out = rb._parse_log_stream(raw)
        self.assertEqual(out, [
            ("docs/developers/tasks/closed/task-001.md", "2026-04-25"),
            ("docs/developers/tasks/closed/task-002.md", "2026-04-26"),
        ])

    def test_path_before_first_commit_ignored(self):
        # If git ever emits paths without a preceding COMMIT sentinel,
        # they are silently dropped rather than crashing.
        raw = "stray/path.md\nCOMMIT 2026-04-26\nclosed/task-001.md\n"
        out = rb._parse_log_stream(raw)
        self.assertEqual(out, [("closed/task-001.md", "2026-04-26")])


class TestDedupeByBasename(unittest.TestCase):
    def test_keeps_latest(self):
        # Reopen → reclose: same basename appears twice.
        closures = [
            {"path": "closed/task-001.md", "date": "2026-04-20",
             "kind": "task", "effort_h": 1.0, "effort_actual_h": 1.0},
            {"path": "closed/task-001.md", "date": "2026-04-26",
             "kind": "task", "effort_h": 1.0, "effort_actual_h": 5.0},
        ]
        out = rb.dedupe_by_basename_keep_latest(closures)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["date"], "2026-04-26")
        self.assertEqual(out[0]["effort_actual_h"], 5.0)

    def test_keeps_distinct_basenames(self):
        closures = [
            {"path": "closed/task-001.md", "date": "2026-04-26",
             "kind": "task", "effort_h": None, "effort_actual_h": None},
            {"path": "closed/task-002.md", "date": "2026-04-26",
             "kind": "task", "effort_h": None, "effort_actual_h": None},
        ]
        out = rb.dedupe_by_basename_keep_latest(closures)
        self.assertEqual(len(out), 2)


class TestAggregateByDay(unittest.TestCase):
    def test_cumulative_series(self):
        closures = [
            {"path": "closed/task-001.md", "date": "2026-04-25",
             "kind": "task", "effort_h": 1.0, "effort_actual_h": 5.0},
            {"path": "closed/task-002.md", "date": "2026-04-25",
             "kind": "task", "effort_h": 5.0, "effort_actual_h": None},
            {"path": "closed/epic-001.md", "date": "2026-04-26",
             "kind": "epic", "effort_h": None, "effort_actual_h": None},
            {"path": "closed/task-003.md", "date": "2026-04-26",
             "kind": "task", "effort_h": 16.0, "effort_actual_h": 32.0},
        ]
        series = rb.aggregate_by_day(closures)
        self.assertEqual(len(series), 2)

        d0, d1 = series
        self.assertEqual(d0["date"], "2026-04-25")
        self.assertEqual(d0["tasks"], 2)
        self.assertEqual(d0["cum_tasks"], 2)
        self.assertEqual(d0["est_h"], 6.0)
        self.assertEqual(d0["actual_h"], 5.0)
        self.assertEqual(d0["epics"], 0)
        self.assertEqual(d0["cum_epics"], 0)

        self.assertEqual(d1["date"], "2026-04-26")
        self.assertEqual(d1["tasks"], 1)
        self.assertEqual(d1["cum_tasks"], 3)
        self.assertEqual(d1["cum_est"], 22.0)
        self.assertEqual(d1["cum_actual"], 37.0)
        self.assertEqual(d1["epics"], 1)
        self.assertEqual(d1["cum_epics"], 1)

    def test_no_actual_excluded_from_actual_line(self):
        # A task with no effort_actual still counts in the count chart
        # but contributes 0 to the actual-hours line.
        closures = [
            {"path": "closed/task-001.md", "date": "2026-04-26",
             "kind": "task", "effort_h": 1.0, "effort_actual_h": None},
        ]
        series = rb.aggregate_by_day(closures)
        self.assertEqual(series[0]["cum_tasks"], 1)
        self.assertEqual(series[0]["cum_est"], 1.0)
        self.assertEqual(series[0]["cum_actual"], 0.0)


class TestUpdateOverviewSection(unittest.TestCase):
    def _scratch_overview(self, td: pathlib.Path) -> pathlib.Path:
        p = td / "OVERVIEW.md"
        p.write_text(
            "# Tasks Overview\n\n<!-- GENERATED -->\n_stub_\n<!-- END GENERATED -->\n",
            encoding="utf-8",
        )
        return p

    def test_inserts_block_when_absent(self):
        with tempfile.TemporaryDirectory() as t:
            td = pathlib.Path(t)
            ov = self._scratch_overview(td)
            block = "\n## Burn-up since v0.3.0\n\n_test block_\n"
            changed = rb.update_overview_section(ov, block)
            self.assertTrue(changed)
            content = ov.read_text(encoding="utf-8")
            self.assertIn(rb.BURNUP_START, content)
            self.assertIn(rb.BURNUP_END, content)
            self.assertIn("_test block_", content)

    def test_idempotent_on_identical_block(self):
        with tempfile.TemporaryDirectory() as t:
            td = pathlib.Path(t)
            ov = self._scratch_overview(td)
            block = "\n## Burn-up since v0.3.0\n\n_test block_\n"
            self.assertTrue(rb.update_overview_section(ov, block))
            before = ov.read_text(encoding="utf-8")
            # Second call with the same input must be a no-op.
            self.assertFalse(rb.update_overview_section(ov, block))
            after = ov.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_replaces_block_on_change(self):
        with tempfile.TemporaryDirectory() as t:
            td = pathlib.Path(t)
            ov = self._scratch_overview(td)
            self.assertTrue(rb.update_overview_section(ov, "\n_v1_\n"))
            self.assertTrue(rb.update_overview_section(ov, "\n_v2_\n"))
            content = ov.read_text(encoding="utf-8")
            self.assertNotIn("_v1_", content)
            self.assertIn("_v2_", content)


class TestRenderBlockByteStability(unittest.TestCase):
    def test_render_block_no_tag(self):
        # When the scratch repo has no tag, render_block produces a
        # deterministic placeholder instead of crashing.
        with tempfile.TemporaryDirectory() as t:
            td = pathlib.Path(t)
            # Make it look like a non-git directory.
            block_a = rb.render_block(td)
            block_b = rb.render_block(td)
            self.assertEqual(block_a, block_b)
            self.assertIn("No git tag", block_a)


if __name__ == "__main__":
    unittest.main()
