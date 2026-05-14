# Security Review

PartsLedger ships an autonomous-loop workflow: Claude can edit files,
run scripts, invoke `git`, and execute allowlisted shell commands
without prompting. That power means a malicious pull / merge / rebase
could quietly install a backdoor — a new allowlist entry, a tweaked
hook script, a SKILL.md that references something it shouldn't — and
the next agent session would honour it. This doc covers both the
automated scan that defends against that, and the human-review layer
that catches what the scan misses.

This is the project-local convention layer. It is **not** a substitute
for OWASP / language-specific security training; it complements them.

## The automated layer — `security_review_changes.py`

[`scripts/security_review_changes.py`](../../scripts/security_review_changes.py)
inspects the diff between two refs for backdoor-shaped changes. Three
git hooks invoke it:

| Hook | Fires on | Refs compared |
|---|---|---|
| `pre-merge-commit` | About to record a merge commit. | Pre-merge HEAD vs incoming `MERGE_HEAD`. Blocks the merge on HIGH/CRITICAL. |
| `post-merge` | Just-completed pull / merge (including fast-forward). | The before-pull and after-pull HEADs. Cannot block (already merged) — surfaces a report and `git reset`-able state. |
| `pre-rebase` | About to rebase onto a different branch. | Current branch vs the upstream target. Blocks on HIGH/CRITICAL. |

The hooks live at
[`scripts/git-hooks/`](../../scripts/git-hooks/) and are installed by
[`scripts/install_git_hooks.sh`](../../scripts/install_git_hooks.sh).

### Static rules

The script flags:

- New entries in `.claude/settings.json` `permissions.allow`,
  especially with `*` wildcards.
- Removed `permissions.deny` entries (loosening guard rails).
- New `hooks` blocks in `settings.json`.
- Changes to scripts already referenced by allowlist patterns.
- SKILL.md files newly referencing scripts they did not reference
  before.
- Shell patterns: `curl|sh`, `base64|sh`, `eval`, `sudo`, `chmod +x`,
  `--no-verify`.
- Exfil patterns: `~/.ssh`, `~/.aws`, `~/.netrc`, `/etc/passwd`,
  `.env`.
- Network egress added to scripts (`curl`, `wget`, `requests`,
  `urllib`, `fetch`).
- **Hardcoded API keys / tokens / private keys** — scanned on
  **every changed file regardless of suffix** (so a key pasted into
  a `.md`, `.toml`, `.yaml`, or `.json` is caught too). Patterns:
  - **Provider-specific prefixes**: Anthropic (`sk-ant-…`), OpenAI
    (`sk-…`), GitHub PATs (`ghp_…`, `gho_…`, `ghs_…`, `ghr_…`,
    `github_pat_…`), Slack (`xoxb-…`, `xoxa-…`, `xoxp-…`, `xoxr-…`,
    `xoxs-…`), AWS access keys (`AKIA…`), Google API (`AIza…`),
    Stripe (`sk_live_…`, `pk_test_…`, etc.), JWTs (`eyJ…`), PEM
    private-key blocks (`-----BEGIN … PRIVATE KEY-----`).
  - **Generic `name = '…'` assignment** where `name` is one of
    `api_key`, `secret`, `token`, `password`, `credential`
    (case-insensitive, hyphen / underscore / plural tolerated) and
    the quoted value is ≥ 20 characters of typical key alphabet.
    The length minimum is tuned to keep short placeholders
    (*"your-api-key-here"*, *"REPLACE_ME"*) below the threshold.
  - Findings have the **secret masked** in the report snippet
    (first 4 chars + asterisks) so the report itself does not
    re-leak the key into CI logs or developer terminals.

### Semantic pass

If the `claude` CLI is on `PATH`, the script also runs a semantic
review of the diff for patterns the static rules miss. Set
`PL_SKIP_CLAUDE_REVIEW=1` to disable the semantic pass and run static
rules only.

### Reading the report

Findings land at `.claude/security-review-latest.md`. The file is
overwritten on each run. Sections:

- **Summary** — overall verdict (`CLEAN` / `LOW` / `MEDIUM` / `HIGH` /
  `CRITICAL`).
- **Findings** — one per detected pattern, with file:line and the
  rule that fired.
- **Diff sample** — relevant excerpts for context.

A `HIGH` or `CRITICAL` finding blocks the merge / rebase. `MEDIUM` and
below are advisory; the report still lands, and the user / agent
reads it before acting.

### Re-running on demand

```bash
python scripts/security_review_changes.py <old_ref> <new_ref> [--label <name>]
```

Useful when you want to scan a branch before opening a PR, or
re-check a previous merge.

## The human-review layer — reviewer checklist

The automated layer catches a *pattern set*. A reviewer's eyes catch
the novel cases. Both are needed.

When reviewing a diff (your own or someone else's), grep / scan for:

- [ ] **Secrets in commits.** Files: `.env`, `.envrc`, `*.key`,
  `*.pem`, credentials JSON. In-line: API tokens / bearer values
  in any file regardless of suffix (the automated layer catches
  the common provider prefixes — see `## Static rules` — but a
  reviewer should still scan diffs of `.md`, `.toml`, `.yaml`,
  `.json`, and CI configs for hand-pasted secrets that don't match
  a known prefix).
- [ ] **Shell-execution risks.** `eval`, `exec`, `subprocess(...,
  shell=True)`, `os.system`, dynamic `import` of attacker-controlled
  names.
- [ ] **Path traversal.** `Path(...)` joined with user input,
  `open(arg)` without containment, archive extraction without
  `is_within_directory` checks.
- [ ] **Dependency surface.** New entries in `requirements-dev.txt`,
  `pyproject.toml` `dependencies`, `package.json`. Is the package
  well-known? Recently created? Does its README match its name?
- [ ] **Permissions / hooks.** New `Bash(...)` allowlist entries in
  `.claude/settings.json`, new `hooks` blocks, looser `deny` rules.
  Each one expands the autonomous-loop's blast radius.
- [ ] **`gh` API mutations.** `gh api ... --method PUT/DELETE/POST` —
  these write to GitHub. Was it user-approved per
  [`AUTONOMY.md` § No-published-effect](AUTONOMY.md#no-published-effect-without-approval)?
- [ ] **Skill changes.** New `.claude/skills/*/SKILL.md` files, or
  edits to existing ones — they directly steer Claude's behaviour.
- [ ] **CI workflow edits.** `.github/workflows/*.yml` — the CI
  environment can leak secrets through logs or env-vars.
- [ ] **Personal data leak.** The maintainer's email / real name /
  phone in committed text.

The checklist is short on purpose — it's for use under time pressure,
not for essays. When a check fires, drop into the relevant file and
decide; do not handwave.

## Two-layer model — when each fires

```text
edit time     →  code-owner skills (`co-inventory-schema`, …)
                 reminders surface invariants before the change lands.
                 See docs/developers/CODE_OWNERS.md.

merge time    →  security_review_changes.py
                 scans the incoming diff; blocks on HIGH/CRITICAL.

review time   →  human reviewer checklist (this doc § above).
                 catches the novel cases the script does not pattern-match.
```

A finding can hit any layer. The earliest layer to catch it is the
cheapest fix.

## Bypass policy

```bash
PL_SKIP_SECURITY_REVIEW=1 git pull   # bypass the merge / pull / rebase hooks
PL_SKIP_CLAUDE_REVIEW=1 …            # static rules only, skip semantic pass
```

Bypasses are **deliberate, logged, and rare**. Use cases:

- A pull you authored yourself coming back from a fresh re-base — the
  diff is already known.
- A pull from a known-good branch where the report was reviewed at
  push time, not pull time.
- Debugging the hook itself.

Bypasses are reviewed in batch by the user — they are **not** the
normal path. If you find yourself bypassing repeatedly for the same
reason, fix the rule (add an allowlist entry to the script, or open
a task to refine the pattern), don't normalise the bypass.

## Escalation — when a real finding lands

1. **Don't merge / push.** If the hook is blocking, leave it
   blocking. If it is not (e.g. `post-merge`), `git reset --hard
   HEAD@{1}` is your friend — but ask the user first if you are an
   agent.
2. **File the finding as a security-tagged task.** Use `/ts-task-new`
   with the `human-in-loop: Main` field — security findings always
   escalate to the user. Describe the finding, the file:line, the
   affected blast radius, and the suggested fix.
3. **Surface in the next review packet.** Per
   [`AUTONOMY.md` § Review packet](AUTONOMY.md#review-packet), every
   open security finding lands in the packet so the user sees it
   the next time they read the loop's output.
4. **Do not normalise.** A real finding is rare; treating it as
   routine trains the wrong reflex. The first response is always to
   stop and surface, not to fix-and-continue.

## Updating this doc

If you change `security_review_changes.py` or any of the three git
hooks, sweep this doc in the same commit. The script's docstring is
authoritative; the doc summarises it for human reviewers. The two
must agree.
