"""Unit tests for task_system_config.py."""

import io
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import task_system_config as tsc


class TestDefaults(unittest.TestCase):

    def test_missing_file_returns_defaults(self):
        with redirect_stderr(io.StringIO()):
            cfg = tsc.load("/nonexistent/path/task-system.yaml")
        self.assertTrue(tsc.get(cfg, "tasks", "active", "enabled"))
        self.assertTrue(tsc.get(cfg, "tasks", "epics", "enabled"))
        self.assertEqual(
            tsc.get(cfg, "ideas", "base_folder"),
            "docs/developers/ideas",
        )

    def test_get_returns_default_when_missing(self):
        self.assertEqual(tsc.get({}, "missing", default="fallback"), "fallback")

    def test_deep_merge_overrides_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "config.yaml"
            path.write_text(
                "tasks:\n  active:\n    enabled: false\n",
                encoding="utf-8",
            )
            with redirect_stderr(io.StringIO()):
                cfg = tsc.load(path)
            # Override applied:
            self.assertFalse(tsc.get(cfg, "tasks", "active", "enabled"))
            # Siblings preserved from defaults:
            self.assertTrue(tsc.get(cfg, "tasks", "epics", "enabled"))
            self.assertTrue(tsc.get(cfg, "ideas", "enabled"))

    def test_env_var_overrides_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "custom.yaml"
            path.write_text("tasks:\n  epics:\n    enabled: false\n",
                            encoding="utf-8")
            old = os.environ.get(tsc.ENV_VAR)
            os.environ[tsc.ENV_VAR] = str(path)
            try:
                with redirect_stderr(io.StringIO()):
                    cfg = tsc.load()
                self.assertFalse(tsc.get(cfg, "tasks", "epics", "enabled"))
            finally:
                if old is None:
                    del os.environ[tsc.ENV_VAR]
                else:
                    os.environ[tsc.ENV_VAR] = old


if __name__ == "__main__":
    unittest.main()
