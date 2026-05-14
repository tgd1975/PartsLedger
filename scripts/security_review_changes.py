#!/usr/bin/env python3
"""Security review for incoming changes (pull / merge / rebase).

Inspects the diff between two refs and flags anything that could turn into a
backdoor given that scripts and skills in this repo can be auto-invoked by
Claude Code without further prompts:

  - new entries in .claude/settings.json permissions.allow (especially with *)
  - removed permissions.deny entries (loosening)
  - new hook commands in settings.json
  - changes to scripts already referenced by allow-list patterns
  - SKILL.md files newly referencing scripts they did not reference before
  - shell patterns: curl|sh, base64|sh, eval, sudo, chmod +x, --no-verify
  - exfil patterns: ~/.ssh, ~/.aws, ~/.netrc, /etc/passwd, .env
  - network egress added to scripts (curl, wget, requests, urllib, fetch)
  - hardcoded API keys / tokens / private-key blocks (Anthropic, OpenAI,
    GitHub PAT, Slack, AWS, Google, Stripe, JWT, PEM private keys, plus
    a generic "secret = '...'" assignment pattern). Scanned on EVERY
    changed file regardless of suffix — secrets pasted into .md, .toml,
    .yaml, .json, etc. are caught too.

Then, if the `claude` CLI is on PATH, runs a semantic review on the diff for
anything the static rules missed.

Writes findings to .claude/security-review-latest.md and exits non-zero on any
HIGH or CRITICAL finding so the calling git hook can block the merge.

Usage:
  python3 scripts/security_review_changes.py <old_ref> <new_ref> [--label <name>]

Env:
  PL_SKIP_SECURITY_REVIEW=1  bypass entirely (escape hatch)
  PL_SKIP_CLAUDE_REVIEW=1    skip the semantic Claude pass, static rules only
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
)
REPORT_PATH = REPO_ROOT / ".claude" / "security-review-latest.md"

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "CLEAN": 0}
BLOCKING = {"CRITICAL", "HIGH"}

INTERESTING_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts"}
INTERESTING_PATHS = {
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".vibe/config.toml",
    ".envrc",
    ".envrc.example",
    "Makefile",
    "pyproject.toml",
    "package.json",
}
INTERESTING_PREFIXES = (
    ".claude/skills/",
    ".claude/hooks/",
    "scripts/git-hooks/",
)


@dataclass
class Finding:
    severity: str
    file: str
    rule: str
    detail: str
    snippet: str = ""


@dataclass
class Report:
    old_ref: str
    new_ref: str
    label: str
    findings: list[Finding] = field(default_factory=list)
    claude_output: str | None = None
    claude_skipped_reason: str | None = None

    @property
    def max_severity(self) -> str:
        if not self.findings and not self._claude_severity():
            return "CLEAN"
        sevs = [f.severity for f in self.findings]
        cs = self._claude_severity()
        if cs:
            sevs.append(cs)
        return max(sevs, key=lambda s: SEVERITY_ORDER.get(s, 0))

    def _claude_severity(self) -> str | None:
        if not self.claude_output:
            return None
        m = re.search(r"^SEVERITY:\s*(\w+)", self.claude_output, re.MULTILINE)
        if not m:
            return None
        sev = m.group(1).upper()
        return sev if sev in SEVERITY_ORDER else None

    def is_blocking(self) -> bool:
        return self.max_severity in BLOCKING


def run_git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=REPO_ROOT
    )
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def changed_files(old_ref: str, new_ref: str) -> list[tuple[str, str]]:
    """Return list of (status, path). status is one of A/M/D/R/...."""
    raw = run_git("diff", "--name-status", "-z", old_ref, new_ref)
    parts = raw.split("\x00")
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(parts):
        token = parts[i]
        if not token:
            i += 1
            continue
        status = token[0]
        if status in ("R", "C"):
            if i + 2 >= len(parts):
                break
            out.append((status, parts[i + 2]))
            i += 3
        else:
            if i + 1 >= len(parts):
                break
            out.append((status, parts[i + 1]))
            i += 2
    return out


def is_interesting(path: str) -> bool:
    if path in INTERESTING_PATHS:
        return True
    if any(path.startswith(p) for p in INTERESTING_PREFIXES):
        return True
    suf = Path(path).suffix
    if suf in INTERESTING_SUFFIXES:
        return True
    return False


def file_at_ref(ref: str, path: str) -> str:
    out = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if out.returncode != 0:
        return ""
    return out.stdout


def diff_for(old_ref: str, new_ref: str, path: str) -> str:
    out = subprocess.run(
        ["git", "diff", "--unified=3", old_ref, new_ref, "--", path],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return out.stdout


def added_lines(diff: str) -> list[str]:
    """Return only the added lines from a unified diff (without the +)."""
    out = []
    for line in diff.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            out.append(line[1:])
    return out


def removed_lines(diff: str) -> list[str]:
    out = []
    for line in diff.splitlines():
        if line.startswith("---"):
            continue
        if line.startswith("-"):
            out.append(line[1:])
    return out


SHELL_PATTERNS: list[tuple[str, str, str]] = [
    # (severity, rule, regex)
    ("CRITICAL", "pipe-to-shell", r"(curl|wget|fetch)\b[^\n]*\|\s*(sh|bash|zsh|python|python3|node|perl|ruby)\b"),
    ("CRITICAL", "base64-to-shell", r"base64\s+(-d|--decode)[^\n]*\|\s*(sh|bash|zsh|python|python3|node|perl|ruby)\b"),
    ("CRITICAL", "reverse-shell", r"\bnc\b\s+-e\b|/dev/tcp/|bash\s+-i\b\s*>&"),
    ("CRITICAL", "ssh-key-write", r">>\s*~?/?\.?ssh/authorized_keys|ssh-copy-id\b"),
    ("HIGH", "credential-read", r"(~/\.ssh/|~/\.aws/|~/\.netrc|/etc/passwd|/etc/shadow|\.env\b)"),
    ("HIGH", "sudo", r"\bsudo\s+\S"),
    ("HIGH", "no-verify", r"--no-verify\b|--no-gpg-sign\b"),
    ("HIGH", "chmod-exec", r"\bchmod\s+[+0-7]*x\b"),
    ("HIGH", "shell-eval-py", r"\bsubprocess\.(Popen|run|call)\([^)]*shell\s*=\s*True"),
    ("HIGH", "shell-eval-py-2", r"\b(os\.system|os\.popen|exec|eval)\s*\("),
    ("HIGH", "shell-eval-sh", r"^\s*eval\s+[\"'$]"),
    ("HIGH", "rm-rf-var", r"\brm\s+-rf?\s+\"?\$"),
    ("MEDIUM", "network-egress-py", r"\b(requests\.|urllib\.request|urllib2|httpx\.|aiohttp\.|socket\.socket\()"),
    ("MEDIUM", "network-egress-js", r"\b(fetch\(|XMLHttpRequest|axios\.|http\.request\()"),
    ("MEDIUM", "network-egress-sh", r"\b(curl|wget)\s+(-[^|\s]*\s+)*https?://"),
    ("MEDIUM", "dynamic-import", r"\bimportlib\.import_module\(|__import__\("),
]


# Secret patterns — scanned on EVERY added line of EVERY changed file
# (not just INTERESTING ones), because secrets pasted into .md / .toml /
# .yaml / .json should be caught too. Patterns are conservative —
# provider-specific prefixes with vendor-published character ranges, plus
# a generic assignment shape that requires ≥ 20 chars of quoted content
# to keep false positives off short placeholder strings like
# "your-api-key-here".
SECRET_PATTERNS: list[tuple[str, str, str]] = [
    # (severity, rule, regex)
    ("HIGH", "anthropic-key", r"\bsk-ant-[A-Za-z0-9_-]{32,}"),
    ("HIGH", "openai-key", r"\bsk-[A-Za-z0-9]{48,}\b"),
    ("HIGH", "github-pat", r"\b(ghp|gho|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}"),
    ("HIGH", "slack-token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("HIGH", "aws-access-key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("HIGH", "google-api-key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("HIGH", "stripe-key", r"\b(sk|pk|rk)_(live|test)_[A-Za-z0-9]{24,}\b"),
    ("HIGH", "jwt-token", r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
    ("HIGH", "private-key-block", r"-----BEGIN ([A-Z]+ )?PRIVATE KEY( BLOCK)?-----"),
    # Generic "name = 'value'" — name is one of api_key / secret / token /
    # password / credential (case-insensitive, optional underscore /
    # hyphen / pluralisation), value is a quoted string of ≥ 20 chars of
    # the alphabet API keys typically use. Requires the assignment shape
    # so prose like "the api key" doesn't trigger.
    ("HIGH", "generic-secret-assign",
        r'(?i)\b(api[_-]?key|secret|token|password|passwd|credential)s?\s*[:=]\s*[\'"][A-Za-z0-9+/=_.\-]{20,}[\'"]'),
]


def scan_added_lines(path: str, diff: str) -> list[Finding]:
    findings: list[Finding] = []
    adds = added_lines(diff)
    if not adds:
        return findings
    for sev, rule, pattern in SHELL_PATTERNS:
        rx = re.compile(pattern)
        for line in adds:
            # ignore comment-only lines (cheap heuristic to cut FP noise)
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            if rx.search(line):
                findings.append(
                    Finding(severity=sev, file=path, rule=rule, detail=f"matched /{pattern}/", snippet=line.strip()[:200])
                )
                break  # one finding per rule per file
    return findings


def scan_for_secrets(path: str, diff: str) -> list[Finding]:
    """Run SECRET_PATTERNS against every added line, regardless of file suffix.

    Comment-only lines are NOT skipped here — a key pasted into a code
    comment is still a leaked key. The snippet attached to a finding is
    truncated and partially masked so the report itself doesn't echo the
    full secret back into git history (.claude/security-review-latest.md
    is gitignored, but the report can also surface in CI logs).
    """
    findings: list[Finding] = []
    adds = added_lines(diff)
    if not adds:
        return findings
    for sev, rule, pattern in SECRET_PATTERNS:
        rx = re.compile(pattern)
        for line in adds:
            m = rx.search(line)
            if not m:
                continue
            # Mask the secret in the snippet so the report doesn't re-leak it.
            masked_line = line.replace(m.group(0), _mask(m.group(0)))
            findings.append(
                Finding(
                    severity=sev,
                    file=path,
                    rule=rule,
                    detail=f"matched /{pattern}/ — value redacted in snippet",
                    snippet=masked_line.strip()[:200],
                )
            )
            break  # one finding per rule per file — enough signal to act
    return findings


def _mask(secret: str) -> str:
    """Replace the body of a secret with asterisks, keep first 4 chars for context."""
    if len(secret) <= 8:
        return "*" * len(secret)
    return secret[:4] + "*" * (len(secret) - 4)


def scan_settings_json(path: str, old_ref: str, new_ref: str) -> list[Finding]:
    """Special-case .claude/settings.json: parse JSON before/after, diff allow/deny/hooks."""
    findings: list[Finding] = []
    try:
        old_text = file_at_ref(old_ref, path) or "{}"
        new_text = file_at_ref(new_ref, path) or "{}"
        old = json.loads(old_text) if old_text.strip() else {}
        new = json.loads(new_text) if new_text.strip() else {}
    except json.JSONDecodeError as e:
        findings.append(
            Finding(severity="MEDIUM", file=path, rule="settings-json-parse", detail=f"could not parse settings.json: {e}")
        )
        return findings

    old_allow = set((old.get("permissions") or {}).get("allow", []) or [])
    new_allow = set((new.get("permissions") or {}).get("allow", []) or [])
    old_deny = set((old.get("permissions") or {}).get("deny", []) or [])
    new_deny = set((new.get("permissions") or {}).get("deny", []) or [])

    added_allow = new_allow - old_allow
    removed_deny = old_deny - new_deny
    for entry in sorted(added_allow):
        # Broad bash wildcards are the scariest
        sev = "CRITICAL" if re.search(r"^Bash\([^)]*\*[^)]*\)", entry) and ("/" not in entry or entry.endswith("*)")) else "HIGH"
        # Tighten: very narrow Bash() entries with explicit binaries are HIGH not CRITICAL.
        #
        # The demotion list below encodes "well-known, broadly audited,
        # low-blast-radius even with wildcard args" — a judgment call made
        # under the project's current single-developer assumption. Each
        # entry is one human's "I trust this tool enough to let the agent
        # run it with any arguments."
        #
        # **Re-audit trigger:** whenever the project gains an additional
        # developer (or any other principal who can land commits without
        # the original maintainer's review), revisit this list. What is
        # "fine on my laptop" is not automatically "fine for someone
        # else's autonomous agent or someone else's threat model."
        # Consider tightening to per-subcommand allow entries
        # (`Bash(ruff check:*)`) or trusted-script wrappers
        # (`Bash(scripts/<tool>-safe:*)`) before broadening further.
        if sev == "CRITICAL" and re.search(r"^Bash\((git|adb|python3|flutter|grep|ls|stat|wc|head|tail|jq|ruff)\b", entry):
            sev = "HIGH"
        findings.append(
            Finding(severity=sev, file=path, rule="permissions-allow-added", detail=f"new allow entry: {entry}")
        )
    for entry in sorted(removed_deny):
        findings.append(
            Finding(severity="HIGH", file=path, rule="permissions-deny-removed", detail=f"deny entry removed: {entry}")
        )

    # Hooks: any new entry, anywhere
    def hook_commands(d: dict) -> list[str]:
        out: list[str] = []
        for event_name, event_list in (d.get("hooks") or {}).items():
            for entry in event_list or []:
                for h in (entry.get("hooks") or []):
                    cmd = h.get("command")
                    if cmd:
                        out.append(f"{event_name}: {cmd}")
        return out

    old_hooks = set(hook_commands(old))
    new_hooks = set(hook_commands(new))
    for h in sorted(new_hooks - old_hooks):
        findings.append(
            Finding(severity="HIGH", file=path, rule="hook-added", detail=f"new hook command: {h}")
        )

    # env vars
    old_env = (old.get("env") or {})
    new_env = (new.get("env") or {})
    for k in set(new_env) - set(old_env):
        findings.append(
            Finding(severity="MEDIUM", file=path, rule="env-var-added", detail=f"new env var: {k}={new_env[k]}")
        )
    for k in set(new_env) & set(old_env):
        if old_env[k] != new_env[k]:
            findings.append(
                Finding(severity="MEDIUM", file=path, rule="env-var-changed", detail=f"env var changed: {k}: {old_env[k]!r} -> {new_env[k]!r}")
            )
    return findings


SKILL_SCRIPT_RX = re.compile(r"\b(?:scripts|\.claude/skills|\.claude/hooks)/[\w./-]+\.(?:py|sh|bash|js|mjs|cjs|ts)\b")


def scan_skill_md(path: str, old_ref: str, new_ref: str) -> list[Finding]:
    findings: list[Finding] = []
    old_text = file_at_ref(old_ref, path)
    new_text = file_at_ref(new_ref, path)
    old_refs = set(SKILL_SCRIPT_RX.findall(old_text))
    new_refs = set(SKILL_SCRIPT_RX.findall(new_text))
    for r in sorted(new_refs - old_refs):
        findings.append(
            Finding(severity="HIGH", file=path, rule="skill-new-script-ref", detail=f"skill now references: {r}")
        )
    return findings


def scripts_referenced_by_allowlist() -> set[str]:
    """Read the CURRENT settings.json and extract referenced script paths."""
    refs: set[str] = set()
    for sf in (".claude/settings.json", ".claude/settings.local.json"):
        p = REPO_ROOT / sf
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for entry in (data.get("permissions") or {}).get("allow", []) or []:
            for m in re.finditer(r"(?:scripts|\.claude/[\w-]+)/[\w./-]+\.(?:py|sh|bash|js|mjs|cjs|ts)", entry):
                refs.add(m.group(0))
    return refs


def find_claude_cli() -> str | None:
    """Find the `claude` binary. Order:
    1. PL_CLAUDE_BIN env var (explicit override).
    2. `claude` on PATH (standalone CLI install).
    3. Highest-versioned VSCode extension bundle on Linux/Mac.
    """
    explicit = os.environ.get("PL_CLAUDE_BIN")
    if explicit and Path(explicit).is_file() and os.access(explicit, os.X_OK):
        return explicit
    on_path = shutil.which("claude")
    if on_path:
        return on_path
    home = Path.home()
    candidates = sorted(
        glob.glob(str(home / ".vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude")),
        reverse=True,  # lexicographic sort puts highest version first
    )
    for c in candidates:
        if os.access(c, os.X_OK):
            return c
    return None


def run_claude_review(diff: str) -> tuple[str | None, str | None]:
    """Run `claude -p` for semantic review. Returns (output, skip_reason)."""
    if os.environ.get("PL_SKIP_CLAUDE_REVIEW") == "1":
        return None, "PL_SKIP_CLAUDE_REVIEW=1"
    claude = find_claude_cli()
    if not claude:
        return None, "claude CLI not found (set PL_CLAUDE_BIN or install on PATH)"
    if not diff.strip():
        return None, "empty diff"

    # Cap diff size to avoid blowing up the API call
    MAX = 80_000
    if len(diff) > MAX:
        diff = diff[:MAX] + "\n\n... [truncated for review] ...\n"

    prompt = (
        "You are a security reviewer. The diff below is about to be merged into a local clone "
        "of a project where scripts and skills can be auto-invoked by Claude Code without further "
        "user prompts. Some of the changed files may be referenced by allow-list patterns in "
        ".claude/settings.json. Look for backdoors, exfiltration, privilege escalation, supply-chain "
        "tampering, sneaky permission widening, or pipe-to-shell-style attacks.\n\n"
        "Output STRICTLY in this format and nothing else:\n"
        "SEVERITY: <CRITICAL|HIGH|MEDIUM|LOW|CLEAN>\n"
        "SUMMARY: <one line>\n"
        "FINDINGS:\n"
        "- <file>: <issue>\n"
        "(or 'FINDINGS: none' if clean)\n\n"
        "Diff:\n"
        f"{diff}\n"
    )
    try:
        out = subprocess.run(
            [claude, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return None, "claude review timed out after 180s"
    if out.returncode != 0:
        return None, f"claude exited {out.returncode}: {out.stderr.strip()[:200]}"
    return out.stdout.strip(), None


def write_report(report: Report) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# Security review — {report.label}")
    lines.append("")
    lines.append(f"- old: `{report.old_ref}`")
    lines.append(f"- new: `{report.new_ref}`")
    lines.append(f"- max severity: **{report.max_severity}**")
    lines.append(f"- blocking: **{'yes' if report.is_blocking() else 'no'}**")
    lines.append("")
    if report.findings:
        lines.append("## Static findings")
        lines.append("")
        for f in sorted(report.findings, key=lambda x: -SEVERITY_ORDER.get(x.severity, 0)):
            lines.append(f"### [{f.severity}] {f.rule} — `{f.file}`")
            lines.append("")
            lines.append(f.detail)
            if f.snippet:
                lines.append("")
                lines.append("```")
                lines.append(f.snippet)
                lines.append("```")
            lines.append("")
    else:
        lines.append("## Static findings")
        lines.append("")
        lines.append("_None._")
        lines.append("")

    lines.append("## Semantic review (Claude)")
    lines.append("")
    if report.claude_output:
        lines.append("```")
        lines.append(report.claude_output)
        lines.append("```")
    elif report.claude_skipped_reason:
        lines.append(f"_skipped: {report.claude_skipped_reason}_")
    else:
        lines.append("_no output_")
    lines.append("")

    if report.is_blocking():
        lines.append("## How to abort")
        lines.append("")
        lines.append(
            "If the findings are real, abort the in-flight operation:\n\n"
            "- merge in progress: `git merge --abort`\n"
            "- rebase in progress: `git rebase --abort`\n"
            "- already merged (fast-forward): `git reset --hard ORIG_HEAD`\n"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def print_summary(report: Report, blocked: bool) -> None:
    sev = report.max_severity
    color = {
        "CRITICAL": "\033[1;31m",
        "HIGH": "\033[0;31m",
        "MEDIUM": "\033[0;33m",
        "LOW": "\033[0;36m",
        "CLEAN": "\033[0;32m",
    }.get(sev, "")
    reset = "\033[0m"
    print(f"{color}[security-review] {report.label}: {sev}{reset}", file=sys.stderr)
    if report.findings:
        for f in sorted(report.findings, key=lambda x: -SEVERITY_ORDER.get(x.severity, 0))[:10]:
            print(f"  [{f.severity}] {f.rule}: {f.file} — {f.detail}", file=sys.stderr)
        if len(report.findings) > 10:
            print(f"  ... {len(report.findings) - 10} more (see report)", file=sys.stderr)
    if report.claude_skipped_reason:
        print(f"  semantic review: {report.claude_skipped_reason}", file=sys.stderr)
    print(f"  full report: {REPORT_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)
    if blocked:
        print(
            f"{color}[security-review] BLOCKING — review .claude/security-review-latest.md before continuing.{reset}",
            file=sys.stderr,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("old_ref")
    parser.add_argument("new_ref")
    parser.add_argument("--label", default="incoming changes")
    parser.add_argument(
        "--non-blocking",
        action="store_true",
        help="exit 0 even on HIGH/CRITICAL (use for post-merge where the merge already happened)",
    )
    args = parser.parse_args()

    if os.environ.get("PL_SKIP_SECURITY_REVIEW") == "1":
        print("[security-review] skipped (PL_SKIP_SECURITY_REVIEW=1)", file=sys.stderr)
        return 0

    try:
        run_git("rev-parse", "--verify", args.old_ref)
        run_git("rev-parse", "--verify", args.new_ref)
    except RuntimeError as e:
        print(f"[security-review] cannot resolve refs: {e}", file=sys.stderr)
        return 0  # fail-open: don't block when refs aren't resolvable

    files = changed_files(args.old_ref, args.new_ref)
    interesting = [(s, p) for s, p in files if is_interesting(p)]

    # Also flag any change to scripts referenced by the allow-list, even if not
    # otherwise "interesting" by suffix (mostly redundant but cheap).
    referenced = scripts_referenced_by_allowlist()

    report = Report(old_ref=args.old_ref, new_ref=args.new_ref, label=args.label)

    # Secret scan runs on EVERY changed file regardless of suffix — secrets
    # in .md / .toml / .yaml / .json are just as dangerous as in code.
    for status, path in files:
        if status == "D":
            continue
        d = diff_for(args.old_ref, args.new_ref, path)
        report.findings.extend(scan_for_secrets(path, d))

    if not interesting:
        # Secret scan may still have produced findings — write the report
        # and exit accordingly, but skip the semantic / shell-pattern pass.
        report.claude_skipped_reason = "no script/settings/skill files in diff"
        write_report(report)
        blocked = report.max_severity in BLOCKING
        print_summary(report, blocked=blocked)
        return 1 if blocked and not args.non_blocking else 0

    full_diff_parts: list[str] = []
    for status, path in interesting:
        if status == "D":
            report.findings.append(
                Finding(severity="LOW", file=path, rule="file-deleted", detail="file removed by incoming change")
            )
            continue

        d = diff_for(args.old_ref, args.new_ref, path)
        full_diff_parts.append(d)

        if path in ("​",):  # placeholder
            pass
        if path in (".claude/settings.json", ".claude/settings.local.json"):
            report.findings.extend(scan_settings_json(path, args.old_ref, args.new_ref))
            continue
        if path.startswith(".claude/skills/") and path.endswith("SKILL.md"):
            report.findings.extend(scan_skill_md(path, args.old_ref, args.new_ref))
            # also content scan in case the SKILL.md itself contains shell snippets
            report.findings.extend(scan_added_lines(path, d))
            continue

        report.findings.extend(scan_added_lines(path, d))

        if path in referenced:
            report.findings.append(
                Finding(
                    severity="HIGH",
                    file=path,
                    rule="trusted-script-modified",
                    detail="this script is referenced by an allow-list entry — its behaviour change is auto-approved",
                )
            )

    full_diff = "\n".join(full_diff_parts)
    report.claude_output, report.claude_skipped_reason = run_claude_review(full_diff)

    write_report(report)

    blocked = report.is_blocking() and not args.non_blocking
    print_summary(report, blocked=blocked)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
