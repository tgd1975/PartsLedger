"""Unit tests for ``partsledger._dev.portability_lint``.

Covers the import-graph walk against a synthetic tree (clean +
offending), the docs/ exception for sibling project names, and the
shim exit-code parity.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger._dev.portability_lint import lint  # noqa: E402


# --------------------------------------------------------------------------
# Synthetic tree — clean + offending
# --------------------------------------------------------------------------


def test_clean_tree_returns_no_findings(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        '"""Synthetic clean package."""\n'
    )
    (pkg / "good.py").write_text(
        "from partsledger.inventory import lint\n"
        "x = 1\n"
    )
    assert lint(pkg) == []


def test_scripts_import_is_flagged(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "bad.py").write_text(
        "from scripts.housekeep import main\n"
    )
    findings = lint(pkg)
    assert any("scripts." in f for f in findings)


def test_claude_import_is_flagged(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "bad.py").write_text(
        "from .claude.skills import something\n"
    )
    findings = lint(pkg)
    assert any(".claude/" in f for f in findings)


def test_parent_parent_parent_escape_is_flagged(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "bad.py").write_text(
        "p = Path(__file__).parent.parent.parent / 'scripts'\n"
    )
    findings = lint(pkg)
    assert any("escape-out-of-package" in f for f in findings)


def test_hardcoded_inventory_path_is_flagged(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "bad.py").write_text(
        "p = 'inventory/INVENTORY.md'\n"
    )
    findings = lint(pkg)
    assert any("inventory/..." in f for f in findings)


# --------------------------------------------------------------------------
# Sibling-project name allowed under docs/ but flagged elsewhere
# --------------------------------------------------------------------------


def test_circuitsmith_in_code_is_flagged(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "ref.py").write_text(
        '"""See CircuitSmith for the sibling tool."""\n'
    )
    findings = lint(pkg)
    assert any("CircuitSmith" in f for f in findings)


def test_circuitsmith_in_docs_is_allowed(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    docs = pkg / "docs"
    docs.mkdir(parents=True)
    (docs / "design.md").write_text(
        "PartsLedger pairs with CircuitSmith via the prefer-inventory adapter.\n"
    )
    findings = lint(pkg)
    assert findings == []


# --------------------------------------------------------------------------
# Allow-list mechanism
# --------------------------------------------------------------------------


def test_allowlist_suppresses_matching_finding(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "bad.py").write_text(
        "from scripts.housekeep import main\n"
    )
    (pkg / ".portability-allow.txt").write_text(
        "bad.py:project-side `scripts.` module:legitimate self-test\n"
    )
    assert lint(pkg) == []


# --------------------------------------------------------------------------
# No-op on empty or missing root
# --------------------------------------------------------------------------


def test_missing_root_is_no_op(tmp_path: Path):
    assert lint(tmp_path / "does-not-exist") == []


def test_empty_root_is_no_op(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    assert lint(pkg) == []


# --------------------------------------------------------------------------
# Shim exit-code parity with the in-package entry point
# --------------------------------------------------------------------------


def test_shim_exits_zero_on_clean_tree(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "good.py").write_text("x = 1\n")
    rc = subprocess.call(
        [sys.executable, str(REPO_ROOT / "scripts/portability_lint.py"), str(pkg)],
    )
    assert rc == 0


def test_shim_exits_nonzero_on_offending_tree(tmp_path: Path):
    pkg = tmp_path / "synthetic"
    pkg.mkdir()
    (pkg / "bad.py").write_text(
        "from scripts.housekeep import main\n"
    )
    rc = subprocess.call(
        [sys.executable, str(REPO_ROOT / "scripts/portability_lint.py"), str(pkg)],
        stderr=subprocess.DEVNULL,
    )
    assert rc == 1


# --------------------------------------------------------------------------
# Checked-in package passes clean (smoke test)
# --------------------------------------------------------------------------


def test_real_package_passes_clean():
    findings = lint(REPO_ROOT / "src" / "partsledger")
    assert findings == [], "\n".join(findings)
