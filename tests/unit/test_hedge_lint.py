"""Unit tests for ``partsledger.inventory.hedge_lint``.

One positive (violation rejected) + negative (clean accepted) test per
pattern, plus exempt-context and suppression tests covering the
acceptance criteria from TASK-019.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.inventory.hedge_lint import (  # noqa: E402
    PATTERNS,
    SUPPRESS_MARKER,
    Diagnostic,
    lint_path,
    lint_text,
)


# --------------------------------------------------------------------------
# Pattern matrix — one positive + one negative per banned literal
# --------------------------------------------------------------------------


class TestIsThePattern:
    def test_synthetic_identity_claim_fails(self):
        diagnostics = lint_text("this is the LM358 family chip")
        assert any(d.rule == "is-the" for d in diagnostics)

    def test_hedged_identity_passes(self):
        diagnostics = lint_text("Looks like the LM358 family chip")
        assert [d for d in diagnostics if d.rule == "is-the"] == []


class TestMustPattern:
    def test_must_fails(self):
        diagnostics = lint_text("All resistors must be 1%-tolerance")
        assert any(d.rule == "must" for d in diagnostics)

    def test_should_passes(self):
        diagnostics = lint_text("All resistors should be 1%-tolerance")
        assert [d for d in diagnostics if d.rule == "must"] == []


class TestAlwaysPattern:
    def test_always_fails(self):
        diagnostics = lint_text("Always set config bits explicitly.")
        assert any(d.rule == "always" for d in diagnostics)

    def test_typically_passes(self):
        diagnostics = lint_text("Typically set config bits explicitly.")
        assert [d for d in diagnostics if d.rule == "always"] == []


class TestNeverPattern:
    def test_never_fails(self):
        diagnostics = lint_text("Never float unused inputs.")
        assert any(d.rule == "never" for d in diagnostics)

    def test_rarely_passes(self):
        diagnostics = lint_text("Rarely float unused inputs.")
        assert [d for d in diagnostics if d.rule == "never"] == []


# --------------------------------------------------------------------------
# Exempt contexts (acceptance criteria 2 + 3 + 4 + 5)
# --------------------------------------------------------------------------


class TestExemptContexts:
    def test_fenced_code_is_exempt(self):
        """`walls must align` inside an ASCII-pinout block passes."""
        text = "```text\nwalls must align\n```\n"
        diagnostics = lint_text(text)
        assert diagnostics == []

    def test_fenced_code_without_language_is_exempt(self):
        text = "```\nthis is the LM358\n```\n"
        diagnostics = lint_text(text)
        assert diagnostics == []

    def test_blockquote_is_exempt(self):
        """Quoted datasheet excerpts are exempt."""
        text = "> The TL082 must be powered with ≥7 V single supply.\n"
        diagnostics = lint_text(text)
        assert diagnostics == []

    def test_suppress_marker_is_exempt(self):
        """`<!-- lint: ok -->` on a line suppresses the diagnostic."""
        text = f"This is the LM358 family pinout. {SUPPRESS_MARKER}\n"
        diagnostics = lint_text(text)
        assert diagnostics == []

    def test_inline_html_comment_is_stripped(self):
        """An inline `<!-- ... -->` block is removed before scanning."""
        text = "Hedged language <!-- must align with template --> applies here.\n"
        diagnostics = lint_text(text)
        assert diagnostics == []


# --------------------------------------------------------------------------
# Scope — only parts pages (the shim's job, but lint_text doesn't care
# about path; the smoke test below verifies the checked-in parts pages
# pass clean).
# --------------------------------------------------------------------------


class TestScopeAndSmokeChecks:
    def test_repo_parts_pages_are_clean(self):
        """The six existing parts pages pass clean."""
        parts_dir = REPO_ROOT / "inventory" / "parts"
        failures: list[Diagnostic] = []
        for path in sorted(parts_dir.glob("*.md")):
            failures.extend(lint_path(path))
        assert failures == [], "\n".join(str(d) for d in failures)

    def test_inventory_md_is_not_scoped(self):
        """Synthetic 'is the LM358' inside an INVENTORY.md Notes cell
        is not a parts-page file; ``lint_path`` is only invoked on
        ``inventory/parts/*.md`` by the shim, so this is a scoping
        invariant verified at shim level. Here we assert the same
        sentence in lint_text *does* fire — confirming the lint
        itself is content-only and scoping is the shim's job.
        """
        diagnostics = lint_text("This Notes cell: is the LM358 family chip.")
        assert any(d.rule == "is-the" for d in diagnostics)


# --------------------------------------------------------------------------
# Pattern coverage sanity check
# --------------------------------------------------------------------------


class TestPatternCoverage:
    def test_all_documented_rules_have_a_pattern(self):
        assert set(PATTERNS.keys()) == {"is-the", "must", "always", "never"}


# Ensure sys is referenced so the unused import lint doesn't trip.
assert sys
