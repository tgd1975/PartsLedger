"""Unit tests for update_idea_overview.py — no filesystem side effects on repo."""

import io
import os
import pathlib
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import update_idea_overview as uio


def _write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


class TestParseIdeaFile(unittest.TestCase):

    def test_parses_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "idea-042-sample.md"
            _write(p, """
                ---
                id: IDEA-042
                title: Sample idea
                description: A short description.
                ---

                # Body
            """)
            result = uio.parse_idea_file(str(p))
            self.assertEqual(result["id"], "IDEA-042")
            self.assertEqual(result["title"], "Sample idea")
            self.assertEqual(result["description"], "A short description.")
            self.assertEqual(result["_file"], "idea-042-sample.md")

    def test_returns_none_without_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "no-frontmatter.md"
            _write(p, "# Just a body\n")
            self.assertIsNone(uio.parse_idea_file(str(p)))


class TestRenderOverview(unittest.TestCase):

    def test_empty_folders(self):
        out = uio.render_overview([], [])
        self.assertIn("**Open: 0** | **Archived: 0**", out)
        self.assertIn("_No open ideas._", out)
        self.assertNotIn("## Archived Ideas", out)

    def test_single_open_idea_renders_row(self):
        idea = {"id": "IDEA-001", "title": "First", "description": "Does things.",
                "category": "firmware", "_file": "idea-001-first.md"}
        out = uio.render_overview([idea], [])
        self.assertIn(
            "| [IDEA-001](open/idea-001-first.md) | ⚡ firmware | First | Does things. |",
            out,
        )

    def test_missing_description_renders_empty_cell(self):
        idea = {"id": "IDEA-002", "title": "No desc",
                "category": "tooling", "_file": "idea-002.md"}
        out = uio.render_overview([idea], [])
        self.assertIn(
            "| [IDEA-002](open/idea-002.md) | 🛠️ tooling | No desc |  |", out
        )

    def test_missing_category_renders_em_dash(self):
        idea = {"id": "IDEA-010", "title": "Uncategorised",
                "description": "x", "_file": "idea-010.md"}
        out = uio.render_overview([idea], [])
        self.assertIn("| [IDEA-010](open/idea-010.md) | — | Uncategorised | x |", out)

    def test_unknown_category_renders_without_icon(self):
        idea = {"id": "IDEA-011", "title": "Mystery",
                "category": "weather-balloon", "description": "x",
                "_file": "idea-011.md"}
        out = uio.render_overview([idea], [])
        self.assertIn(
            "| [IDEA-011](open/idea-011.md) | weather-balloon | Mystery | x |", out
        )

    def test_pipe_in_description_is_escaped(self):
        idea = {"id": "IDEA-003", "title": "Piped", "category": "firmware",
                "description": "Has | pipe", "_file": "idea-003.md"}
        out = uio.render_overview([idea], [])
        self.assertIn("Has \\| pipe", out)

    def test_archived_section_only_when_non_empty(self):
        archived = {"id": "IDEA-099", "title": "Done", "category": "hardware",
                    "_file": "idea-099.md"}
        out = uio.render_overview([], [archived])
        self.assertIn("## Archived Ideas", out)
        self.assertIn(
            "| [IDEA-099](archived/idea-099.md) | 🔧 hardware | Done |", out
        )

    def test_archived_missing_category_renders_em_dash(self):
        archived = {"id": "IDEA-098", "title": "Old", "_file": "idea-098.md"}
        out = uio.render_overview([], [archived])
        self.assertIn("| [IDEA-098](archived/idea-098.md) | — | Old |", out)

    def test_format_category_known_categories(self):
        # \u00a0 = NBSP, the required separator between icon and category name.
        self.assertEqual(uio.format_category("hardware"), "🔧 hardware")
        self.assertEqual(uio.format_category("firmware"), "⚡ firmware")
        self.assertEqual(uio.format_category("apps"), "📱 apps")
        self.assertEqual(uio.format_category("tooling"), "🛠️ tooling")
        self.assertEqual(uio.format_category("docs"), "📖 docs")
        self.assertEqual(uio.format_category("outreach"), "📣 outreach")

    def test_format_category_uses_non_breaking_space(self):
        # The separator between icon and name must be U+00A0 so the pair
        # never wraps to separate lines in narrow renderers.
        out = uio.format_category("hardware")
        self.assertIn(" ", out)
        self.assertNotIn("🔧 hardware", out)  # plain-space form would defeat the purpose

    def test_format_category_empty_renders_em_dash(self):
        self.assertEqual(uio.format_category(""), "—")
        self.assertEqual(uio.format_category("   "), "—")

    def test_open_table_has_category_column_header(self):
        idea = {"id": "IDEA-001", "title": "x", "_file": "idea-001.md"}
        out = uio.render_overview([idea], [])
        self.assertIn("| ID | Category | Title | Description |", out)

    def test_archived_table_has_category_column_header(self):
        archived = {"id": "IDEA-099", "title": "x", "_file": "idea-099.md"}
        out = uio.render_overview([], [archived])
        self.assertIn("| ID | Category | Title |", out)

    def test_overview_intro_links_to_readme(self):
        out = uio.render_overview([], [])
        self.assertIn("[README.md](README.md)", out)


class TestSubFileDetection(unittest.TestCase):

    def test_main_file_is_not_sub_file(self):
        self.assertFalse(uio.is_sub_file("idea-027-circuit-skill.md"))
        self.assertFalse(uio.is_sub_file("idea-001-mobile-app.md"))
        self.assertFalse(uio.is_sub_file("idea-043-coordinated-rollout.md"))

    def test_sub_file_with_dot_separator(self):
        self.assertTrue(uio.is_sub_file("idea-027.erc-engine.md"))
        self.assertTrue(uio.is_sub_file("idea-027.components.md"))
        self.assertTrue(uio.is_sub_file("idea-043.release-burnup-chart.md"))

    def test_load_ideas_skips_sub_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp) / "open"
            # Main file: should be loaded.
            _write(tmp_p / "idea-027-circuit-skill.md",
                   "---\nid: IDEA-027\ntitle: Circuit\n---\n")
            # Sub-file: even with frontmatter, must be skipped.
            _write(tmp_p / "idea-027.erc-engine.md",
                   "---\nid: IDEA-027-ERC\ntitle: ERC\n---\n")
            ideas = uio.load_ideas(str(tmp_p))
            self.assertEqual(len(ideas), 1)
            self.assertEqual(ideas[0]["id"], "IDEA-027")


class TestMainIdempotent(unittest.TestCase):

    def test_dry_run_prints_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            _write(tmp_p / "open" / "idea-001.md",
                   "---\nid: IDEA-001\ntitle: A\n---\n")
            overview = tmp_p / "OVERVIEW.md"

            buf = io.StringIO()
            with patch.object(uio, "OPEN_DIR", str(tmp_p / "open")), \
                 patch.object(uio, "ARCHIVED_DIR", str(tmp_p / "archived")), \
                 patch.object(uio, "OVERVIEW", str(overview)), \
                 redirect_stdout(buf):
                rc = uio.main(["--dry-run"])
            self.assertEqual(rc, 0)
            self.assertFalse(overview.exists())
            self.assertIn("IDEA-001", buf.getvalue())

    def test_write_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            _write(tmp_p / "open" / "idea-001.md",
                   "---\nid: IDEA-001\ntitle: A\n---\n")
            overview = tmp_p / "OVERVIEW.md"

            with patch.object(uio, "OPEN_DIR", str(tmp_p / "open")), \
                 patch.object(uio, "ARCHIVED_DIR", str(tmp_p / "archived")), \
                 patch.object(uio, "OVERVIEW", str(overview)), \
                 redirect_stdout(io.StringIO()):
                uio.main([])
                first = overview.read_text()
                uio.main([])
                second = overview.read_text()
            self.assertEqual(first, second)


class TestGeneratedOverviewIsLintClean(unittest.TestCase):
    """Idea OVERVIEW.md must pass markdownlint even when titles or
    descriptions contain `<word>` placeholders or pipe characters.
    """

    def setUp(self):
        import shutil
        self.markdownlint = shutil.which("markdownlint-cli2")
        if not self.markdownlint:
            self.skipTest("markdownlint-cli2 not installed")

    def test_hostile_title_and_description_lint_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            _write(tmp_p / "open" / "idea-001.md",
                   "---\nid: IDEA-001\n"
                   "title: Try archive/<version>/ pattern for ideas\n"
                   "description: Notes from a | b | c discussion\n"
                   "category: tooling\n---\n")
            overview = tmp_p / "OVERVIEW.md"

            with patch.object(uio, "OPEN_DIR", str(tmp_p / "open")), \
                 patch.object(uio, "ARCHIVED_DIR", str(tmp_p / "archived")), \
                 patch.object(uio, "OVERVIEW", str(overview)), \
                 redirect_stdout(io.StringIO()):
                uio.main([])

            import subprocess
            result = subprocess.run(
                [self.markdownlint, str(overview)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
