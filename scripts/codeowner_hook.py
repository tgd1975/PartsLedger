#!/usr/bin/env python3
"""Code-owner reminder hook — PreToolUse for ``Edit`` and ``Write``.

The hook reads the Claude Code tool-use JSON payload from stdin,
extracts the target file path, matches it against
``.claude/codeowners.yaml``, and on a match prints the bound
``co-*`` skill's ``SKILL.md`` body to stdout as an informational
reminder.

Contract:

- **Silent on no-match.** Exit 0 with no output.
- **Silent on missing registry.** Exit 0 with no output — the
  registry is optional; absence means "no code-owner skills yet".
- **Non-zero on malformed registry.** A clear error to stderr so
  the contributor notices the typo. This is the *only* path where
  the hook blocks an edit.
- **Never blocks for any other reason.** Even a missing referenced
  skill prints a stderr warning but exits 0 — the registry can list
  patterns whose skills are not yet authored.

The YAML reader is a tiny constrained-format parser (no library
dependency). It only understands the registry's specific shape,
documented in ``.claude/codeowners.yaml``.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Tiny YAML parser for the constrained codeowners.yaml format.
# ---------------------------------------------------------------------------
def parse_registry(text: str) -> dict:
    """Parse a string in the constrained codeowners format.

    Accepts:

        entries:
          - pattern: <value>
            skill:   <value>
          - pattern: <value>
            skill:   <value>

    Comments (``#``) and blank lines are skipped. String values may be
    bare, single-quoted, or double-quoted. Anything outside this shape
    raises :class:`ValueError`.
    """
    lines = text.splitlines()
    entries: list[dict] = []
    current: dict | None = None
    in_entries = False
    saw_root = False

    for raw_line_number, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        # strip end-of-line comment, but not '#' inside quoted strings
        # (the format does not permit '#' inside values, so a simple
        # split is safe)
        if "#" in line:
            line = line.split("#", 1)[0].rstrip()
        if not line:
            continue

        # Top-level `entries:` opens the list.
        if line.lstrip() == line and line == "entries:":
            in_entries = True
            saw_root = True
            continue
        # Any other top-level key is rejected (constrained format).
        if line.lstrip() == line:
            raise ValueError(
                f"line {raw_line_number}: unexpected top-level key "
                f"({line!r}); only `entries:` is allowed"
            )

        if not in_entries:
            raise ValueError(
                f"line {raw_line_number}: content before `entries:`"
            )

        stripped = line.lstrip()
        if stripped.startswith("- "):
            if current is not None:
                _validate_entry(current, raw_line_number)
                entries.append(current)
            current = {}
            rest = stripped[2:].lstrip()
            if rest:
                key, sep, val = rest.partition(":")
                if not sep:
                    raise ValueError(
                        f"line {raw_line_number}: expected `key: value`"
                    )
                current[key.strip()] = _strip_quotes(val.strip())
        elif ":" in stripped:
            if current is None:
                raise ValueError(
                    f"line {raw_line_number}: key without preceding "
                    f"`- ` entry marker"
                )
            key, _, val = stripped.partition(":")
            current[key.strip()] = _strip_quotes(val.strip())
        else:
            raise ValueError(
                f"line {raw_line_number}: unrecognised line {stripped!r}"
            )

    if current is not None:
        _validate_entry(current, len(lines))
        entries.append(current)

    if not saw_root:
        # Empty / comment-only file is fine — treat as no entries.
        return {"entries": []}
    return {"entries": entries}


def _validate_entry(entry: dict, line_number: int) -> None:
    if "pattern" not in entry or "skill" not in entry:
        missing = [k for k in ("pattern", "skill") if k not in entry]
        raise ValueError(
            f"line ~{line_number}: entry missing required field(s): "
            f"{', '.join(missing)}"
        )
    if not entry["pattern"] or not entry["skill"]:
        raise ValueError(
            f"line ~{line_number}: entry has empty pattern or skill"
        )


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


# ---------------------------------------------------------------------------
# Registry loading and matching.
# ---------------------------------------------------------------------------
def load_registry(registry_path: Path) -> list[dict]:
    """Read ``codeowners.yaml`` into a normalised entry list.

    Missing file → empty list (silent). Malformed file → ValueError.
    """
    if not registry_path.exists():
        return []
    text = registry_path.read_text(encoding="utf-8")
    data = parse_registry(text)
    return list(data.get("entries", []))


def _glob_to_regex(pattern: str) -> str:
    """Translate a gitignore-style glob into an anchored regex.

    - ``**`` matches any string, including ``/``.
    - ``*`` matches any string **not** containing ``/`` (one path segment).
    - ``?`` matches any single character **not** ``/``.
    - Other regex metacharacters are escaped to literal.

    Note: not a full gitignore implementation — directory-only patterns
    (``foo/``), negation (``!``), and anchoring (``/foo``) are not
    supported. The registry is matched against repo-relative POSIX
    paths and patterns are expected to be repo-relative too.
    """
    parts: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*" and i + 1 < len(pattern) and pattern[i + 1] == "*":
            parts.append(".*")
            i += 2
        elif c == "*":
            parts.append("[^/]*")
            i += 1
        elif c == "?":
            parts.append("[^/]")
            i += 1
        elif c in r".+^${}()|[]\\":
            parts.append("\\" + c)
            i += 1
        else:
            parts.append(c)
            i += 1
    return "^" + "".join(parts) + "$"


def match_entries(rel_path: str, entries: list[dict]) -> list[dict]:
    """Return entries whose pattern matches ``rel_path``.

    Patterns use a gitignore-flavoured subset (see :func:`_glob_to_regex`).
    """
    out: list[dict] = []
    for e in entries:
        if re.match(_glob_to_regex(e["pattern"]), rel_path):
            out.append(e)
    return out


def skill_body(repo: Path, skill_name: str) -> str | None:
    """Return the body of ``.claude/skills/<skill>/SKILL.md``.

    Skips a leading YAML frontmatter block if present. Returns None
    if the skill directory or SKILL.md is missing.
    """
    path = repo / ".claude" / "skills" / skill_name / "SKILL.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        try:
            close_idx = lines.index("---", 1)
            body = "\n".join(lines[close_idx + 1:]).lstrip("\n")
        except ValueError:
            body = text
    else:
        body = text
    return body


def emit_reminder(entry: dict, body: str, out=sys.stdout) -> None:
    out.write(
        f"\n=== code-owner reminder: {entry['skill']} "
        f"(matched pattern `{entry['pattern']}`) ===\n\n"
    )
    out.write(body)
    if not body.endswith("\n"):
        out.write("\n")
    out.write("=== end reminder ===\n\n")


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------
def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return Path.cwd()
    return Path(out.stdout.strip())


def run(payload_text: str, *, out=sys.stdout, err=sys.stderr) -> int:
    """Process a single hook invocation. Pure-ish for testing."""
    if not payload_text.strip():
        return 0
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return 0
    tool_name = payload.get("tool_name")
    if tool_name not in ("Edit", "Write"):
        return 0
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path")
    if not file_path:
        return 0

    repo = repo_root()
    abs_path = Path(file_path).resolve()
    try:
        rel = abs_path.relative_to(repo).as_posix()
    except ValueError:
        return 0  # outside repo — not our concern

    registry_path = repo / ".claude" / "codeowners.yaml"
    try:
        entries = load_registry(registry_path)
    except ValueError as e:
        err.write(f"codeowner-hook: malformed registry: {e}\n")
        return 1

    for m in match_entries(rel, entries):
        body = skill_body(repo, m["skill"])
        if body is None:
            err.write(
                f"codeowner-hook: skill '{m['skill']}' not found at "
                f".claude/skills/{m['skill']}/SKILL.md (continuing)\n"
            )
            continue
        emit_reminder(m, body, out=out)

    return 0


def main() -> int:
    return run(sys.stdin.read())


if __name__ == "__main__":
    raise SystemExit(main())
