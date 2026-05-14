"""Tests for the /capture slash-skill wrapper — TASK-038."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# SKILL.md + .vibe/config.toml + .claude/settings.json registration


def test_skill_md_exists():
    path = REPO_ROOT / ".claude" / "skills" / "capture" / "SKILL.md"
    assert path.is_file()
    contents = path.read_text(encoding="utf-8")
    assert "name: capture" in contents
    assert "python -m partsledger.capture" in contents


def test_skill_registered_in_vibe_config():
    path = REPO_ROOT / ".vibe" / "config.toml"
    text = path.read_text(encoding="utf-8")
    assert '"capture"' in text, "capture not in enabled_skills"


def test_skill_allowed_in_claude_settings():
    path = REPO_ROOT / ".claude" / "settings.json"
    text = path.read_text(encoding="utf-8")
    assert "python -m partsledger.capture" in text


# ---------------------------------------------------------------------------
# Wrapper script — picks $PL_PYTHON, forwards args


def test_wrapper_script_exists_and_is_executable():
    sh = REPO_ROOT / "scripts" / "skills" / "capture-cli.sh"
    cmd = REPO_ROOT / "scripts" / "skills" / "capture-cli.cmd"
    assert sh.is_file()
    assert cmd.is_file()
    if sys.platform != "win32":
        assert os.access(sh, os.X_OK), "capture-cli.sh must be executable"


@pytest.mark.skipif(sys.platform == "win32", reason="bash wrapper test")
def test_wrapper_forwards_args_and_inherits_env(tmp_path):
    """Drive the wrapper with PL_PYTHON pointing at a fake interpreter.

    The fake interpreter is a one-shot shell script that records its argv
    and exits with a known code; we assert the wrapper forwarded the
    user's flags and used the env var.
    """
    fake_python = tmp_path / "fake-python"
    log_file = tmp_path / "argv.txt"
    fake_python.write_text(
        f"#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$@\" > {log_file}\n"
        f"exit 42\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["PL_PYTHON"] = str(fake_python)

    wrapper = REPO_ROOT / "scripts" / "skills" / "capture-cli.sh"
    proc = subprocess.run(
        [str(wrapper), "--no-preview", "--dump-captures-to", "/tmp/x"],
        env=env,
        capture_output=True,
    )
    assert proc.returncode == 42
    argv = log_file.read_text(encoding="utf-8").splitlines()
    assert argv == [
        "-m",
        "partsledger.capture",
        "--no-preview",
        "--dump-captures-to",
        "/tmp/x",
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="bash wrapper test")
def test_wrapper_propagates_exit_code(tmp_path):
    """Wrapper's exit code must equal the CLI's exit code."""
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/usr/bin/env bash\nexit 130\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env["PL_PYTHON"] = str(fake_python)
    wrapper = REPO_ROOT / "scripts" / "skills" / "capture-cli.sh"
    proc = subprocess.run([str(wrapper)], env=env, capture_output=True)
    assert proc.returncode == 130


@pytest.mark.skipif(sys.platform == "win32", reason="bash wrapper test")
def test_wrapper_auto_detects_repo_venv_when_pl_python_unset(tmp_path):
    """When $PL_PYTHON is unset, the wrapper prefers <repo>/.venv/bin/python.

    The Claude Code Bash tool spawns non-interactive shells that don't load
    direnv, so $PL_PYTHON from .envrc is invisible. Auto-detecting the
    sibling venv covers that case.
    """
    # Build a fake repo layout: .venv/bin/python + scripts/skills/capture-cli.sh.
    fake_repo = tmp_path / "fake-repo"
    venv_bin = fake_repo / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    log_file = tmp_path / "venv-python-called.txt"
    fake_venv_python = venv_bin / "python"
    fake_venv_python.write_text(
        f"#!/usr/bin/env bash\necho venv-python > {log_file}\nexit 0\n",
        encoding="utf-8",
    )
    fake_venv_python.chmod(0o755)

    fake_skills_dir = fake_repo / "scripts" / "skills"
    fake_skills_dir.mkdir(parents=True)
    real_wrapper = REPO_ROOT / "scripts" / "skills" / "capture-cli.sh"
    fake_wrapper = fake_skills_dir / "capture-cli.sh"
    fake_wrapper.write_bytes(real_wrapper.read_bytes())
    fake_wrapper.chmod(0o755)

    env = {k: v for k, v in os.environ.items() if k != "PL_PYTHON"}
    proc = subprocess.run(
        [str(fake_wrapper)], env=env, capture_output=True
    )
    assert proc.returncode == 0
    assert log_file.read_text(encoding="utf-8").strip() == "venv-python"


@pytest.mark.skipif(sys.platform == "win32", reason="bash wrapper test")
def test_wrapper_pl_python_takes_precedence_over_venv(tmp_path):
    """An explicit $PL_PYTHON wins over the auto-detected venv."""
    fake_repo = tmp_path / "fake-repo"
    venv_bin = fake_repo / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    venv_log = tmp_path / "venv-python.txt"
    fake_venv_python = venv_bin / "python"
    fake_venv_python.write_text(
        f"#!/usr/bin/env bash\necho venv > {venv_log}\nexit 0\n",
        encoding="utf-8",
    )
    fake_venv_python.chmod(0o755)

    explicit_log = tmp_path / "explicit-python.txt"
    explicit = tmp_path / "explicit-python"
    explicit.write_text(
        f"#!/usr/bin/env bash\necho explicit > {explicit_log}\nexit 0\n",
        encoding="utf-8",
    )
    explicit.chmod(0o755)

    fake_skills_dir = fake_repo / "scripts" / "skills"
    fake_skills_dir.mkdir(parents=True)
    real_wrapper = REPO_ROOT / "scripts" / "skills" / "capture-cli.sh"
    fake_wrapper = fake_skills_dir / "capture-cli.sh"
    fake_wrapper.write_bytes(real_wrapper.read_bytes())
    fake_wrapper.chmod(0o755)

    env = os.environ.copy()
    env["PL_PYTHON"] = str(explicit)
    proc = subprocess.run([str(fake_wrapper)], env=env, capture_output=True)
    assert proc.returncode == 0
    assert explicit_log.read_text(encoding="utf-8").strip() == "explicit"
    assert not venv_log.exists()
