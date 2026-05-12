"""Tests for scripts/codeowner_hook.py — exercise registry, matching, hook flow."""

import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import codeowner_hook as ch


def _write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestParseRegistry(unittest.TestCase):

    def test_minimal_valid_registry(self):
        text = (
            "entries:\n"
            "  - pattern: foo.py\n"
            "    skill: co-foo\n"
        )
        data = ch.parse_registry(text)
        self.assertEqual(data["entries"], [{"pattern": "foo.py", "skill": "co-foo"}])

    def test_multiple_entries(self):
        text = (
            "entries:\n"
            "  - pattern: a.py\n"
            "    skill: co-a\n"
            "  - pattern: b/*.json\n"
            "    skill: co-b\n"
        )
        data = ch.parse_registry(text)
        self.assertEqual(len(data["entries"]), 2)
        self.assertEqual(data["entries"][1], {"pattern": "b/*.json", "skill": "co-b"})

    def test_comments_and_blank_lines_ignored(self):
        text = (
            "# top comment\n"
            "\n"
            "entries:\n"
            "  # mid comment\n"
            "  - pattern: a.py   # trailing comment\n"
            "    skill: co-a\n"
            "\n"
        )
        data = ch.parse_registry(text)
        self.assertEqual(data["entries"], [{"pattern": "a.py", "skill": "co-a"}])

    def test_quoted_values_unwrap(self):
        text = (
            "entries:\n"
            '  - pattern: "a b.py"\n'
            "    skill: 'co-spaced'\n"
        )
        data = ch.parse_registry(text)
        self.assertEqual(data["entries"], [{"pattern": "a b.py", "skill": "co-spaced"}])

    def test_empty_text_returns_empty_entries(self):
        self.assertEqual(ch.parse_registry(""), {"entries": []})

    def test_comments_only_returns_empty_entries(self):
        text = "# only comments\n# more\n"
        self.assertEqual(ch.parse_registry(text), {"entries": []})

    def test_missing_required_field_raises(self):
        text = (
            "entries:\n"
            "  - pattern: a.py\n"
        )
        with self.assertRaises(ValueError) as ctx:
            ch.parse_registry(text)
        self.assertIn("skill", str(ctx.exception))

    def test_unexpected_top_level_key_raises(self):
        text = "unknown_key: bar\n"
        with self.assertRaises(ValueError):
            ch.parse_registry(text)

    def test_key_without_entry_marker_raises(self):
        text = (
            "entries:\n"
            "    pattern: a.py\n"
        )
        with self.assertRaises(ValueError):
            ch.parse_registry(text)


class TestMatchEntries(unittest.TestCase):

    def test_exact_match(self):
        entries = [{"pattern": "a/b.py", "skill": "co-x"}]
        self.assertEqual(len(ch.match_entries("a/b.py", entries)), 1)

    def test_glob_match(self):
        entries = [{"pattern": "schema/*.json", "skill": "co-schema"}]
        self.assertEqual(len(ch.match_entries("schema/foo.json", entries)), 1)
        self.assertEqual(len(ch.match_entries("schema/sub/foo.json", entries)), 0)

    def test_no_match(self):
        entries = [{"pattern": "a/b.py", "skill": "co-x"}]
        self.assertEqual(ch.match_entries("a/c.py", entries), [])

    def test_multiple_matches(self):
        entries = [
            {"pattern": "*.py", "skill": "co-any-py"},
            {"pattern": "foo.py", "skill": "co-foo"},
        ]
        matches = ch.match_entries("foo.py", entries)
        self.assertEqual(len(matches), 2)


class TestSkillBody(unittest.TestCase):

    def test_skill_with_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            _write(
                t / ".claude" / "skills" / "co-foo" / "SKILL.md",
                "---\nname: co-foo\n---\n\nBody starts here.\n",
            )
            body = ch.skill_body(t, "co-foo")
            # splitlines drops the trailing newline, so the body string
            # ends at the final non-blank line.
            self.assertEqual(body, "Body starts here.")

    def test_skill_without_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            _write(
                t / ".claude" / "skills" / "co-foo" / "SKILL.md",
                "# Heading\n\nNo frontmatter here.\n",
            )
            body = ch.skill_body(t, "co-foo")
            self.assertIn("# Heading", body)

    def test_missing_skill_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ch.skill_body(pathlib.Path(tmp), "co-foo"))


class TestRun(unittest.TestCase):
    """Integration: drive ch.run() with synthetic payloads and verify."""

    def _setup_repo(self, tmp: pathlib.Path,
                    registry: str | None = None,
                    skill_body: str | None = None) -> None:
        """Build a minimal git-less repo skeleton and (optionally) a
        registry and skill."""
        # repo_root() will fall back to cwd if `git rev-parse` fails.
        # We chdir into tmp in the test and chmod a .git/ stub to make
        # `git rev-parse` happy.
        (tmp / ".git").mkdir(parents=True, exist_ok=True)
        if registry is not None:
            _write(tmp / ".claude" / "codeowners.yaml", registry)
        if skill_body is not None:
            _write(
                tmp / ".claude" / "skills" / "co-test" / "SKILL.md",
                f"---\nname: co-test\n---\n\n{skill_body}\n",
            )

    def _payload(self, file_path: str, tool: str = "Edit") -> str:
        return json.dumps({
            "tool_name": tool,
            "tool_input": {"file_path": file_path},
        })

    def test_unmatched_path_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp).resolve()
            self._setup_repo(
                t,
                registry="entries:\n  - pattern: matches/nothing.py\n    skill: co-x\n",
            )
            target = t / "a.py"
            _write(target, "x = 1\n")
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(ch, "repo_root", return_value=t):
                rc = ch.run(self._payload(str(target)), out=out, err=err)
            self.assertEqual(rc, 0)
            self.assertEqual(out.getvalue(), "")

    def test_matched_path_emits_reminder(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp).resolve()
            self._setup_repo(
                t,
                registry="entries:\n  - pattern: a.py\n    skill: co-test\n",
                skill_body="Invariants:\n- foo is sacred.\n",
            )
            target = t / "a.py"
            _write(target, "x = 1\n")
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(ch, "repo_root", return_value=t):
                rc = ch.run(self._payload(str(target)), out=out, err=err)
            self.assertEqual(rc, 0)
            output = out.getvalue()
            self.assertIn("co-test", output)
            self.assertIn("a.py", output)
            self.assertIn("foo is sacred", output)

    def test_missing_registry_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp).resolve()
            self._setup_repo(t)  # no registry
            target = t / "a.py"
            _write(target, "x = 1\n")
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(ch, "repo_root", return_value=t):
                rc = ch.run(self._payload(str(target)), out=out, err=err)
            self.assertEqual(rc, 0)
            self.assertEqual(out.getvalue(), "")

    def test_malformed_registry_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp).resolve()
            self._setup_repo(
                t,
                registry="entries:\n  - pattern: a.py\n",  # missing skill
            )
            target = t / "a.py"
            _write(target, "x = 1\n")
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(ch, "repo_root", return_value=t):
                rc = ch.run(self._payload(str(target)), out=out, err=err)
            self.assertEqual(rc, 1)
            self.assertIn("malformed registry", err.getvalue())

    def test_missing_referenced_skill_warns_but_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp).resolve()
            self._setup_repo(
                t,
                registry="entries:\n  - pattern: a.py\n    skill: co-missing\n",
            )
            target = t / "a.py"
            _write(target, "x = 1\n")
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(ch, "repo_root", return_value=t):
                rc = ch.run(self._payload(str(target)), out=out, err=err)
            self.assertEqual(rc, 0)
            self.assertIn("co-missing", err.getvalue())
            self.assertEqual(out.getvalue(), "")

    def test_non_edit_tool_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp).resolve()
            self._setup_repo(
                t,
                registry="entries:\n  - pattern: a.py\n    skill: co-test\n",
                skill_body="Body.\n",
            )
            target = t / "a.py"
            _write(target, "x = 1\n")
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(ch, "repo_root", return_value=t):
                rc = ch.run(self._payload(str(target), tool="Bash"),
                            out=out, err=err)
            self.assertEqual(rc, 0)
            self.assertEqual(out.getvalue(), "")

    def test_empty_payload_is_silent(self):
        out = io.StringIO()
        err = io.StringIO()
        rc = ch.run("", out=out, err=err)
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "")

    def test_invalid_json_payload_is_silent(self):
        out = io.StringIO()
        err = io.StringIO()
        rc = ch.run("not-json", out=out, err=err)
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "")

    def test_path_outside_repo_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp).resolve()
            self._setup_repo(
                t,
                registry="entries:\n  - pattern: a.py\n    skill: co-test\n",
                skill_body="Body.\n",
            )
            # Target outside the repo: a path that does not start with t.
            with tempfile.NamedTemporaryFile(suffix=".py") as f:
                out = io.StringIO()
                err = io.StringIO()
                with mock.patch.object(ch, "repo_root", return_value=t):
                    rc = ch.run(self._payload(f.name), out=out, err=err)
                self.assertEqual(rc, 0)
                self.assertEqual(out.getvalue(), "")


class TestRealRegistryRoundtrip(unittest.TestCase):
    """Sanity-check: the checked-in `.claude/codeowners.yaml` parses."""

    def test_checked_in_registry_parses(self):
        repo = pathlib.Path(__file__).resolve().parent.parent.parent
        registry = repo / ".claude" / "codeowners.yaml"
        if not registry.exists():
            self.skipTest("registry not present in this checkout")
        ch.load_registry(registry)  # raises if malformed


if __name__ == "__main__":
    unittest.main()
