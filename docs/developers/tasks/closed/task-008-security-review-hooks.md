---
id: TASK-008
title: Port security-review hooks (pre-merge-commit, post-merge, pre-rebase)
status: closed
closed: 2026-05-13
opened: 2026-05-12
effort: Medium
effort_actual: Small (<2h)
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 8
prerequisites: [TASK-005]
---

## Description

Port CircuitSmith's security-review layer. Catches backdoor-shaped
changes in incoming pulls / merges / rebases (new
`.claude/settings.json` allowlist entries with wildcards, removed
deny entries, new hook blocks, new SKILL.md references to scripts,
shell exfil patterns, network egress added to scripts, etc.). Five
artefacts plus three follow-on edits:

1. **`scripts/security_review_changes.py`** — port verbatim.
   Substitute `CS_SKIP_SECURITY_REVIEW` → `PL_SKIP_SECURITY_REVIEW`
   and `CS_SKIP_CLAUDE_REVIEW` → `PL_SKIP_CLAUDE_REVIEW`. The
   static-rule patterns are project-agnostic and need no edits.
2. **`scripts/git-hooks/pre-merge-commit`** — port verbatim. Calls
   `security_review_changes.py HEAD MERGE_HEAD`. Blocks on
   HIGH/CRITICAL.
3. **`scripts/git-hooks/post-merge`** — port verbatim. Calls the
   script in `--non-blocking` mode (merge already happened); prints
   `git reset --hard ORIG_HEAD` recipe on HIGH/CRITICAL.
4. **`scripts/git-hooks/pre-rebase`** — port verbatim. Calls the
   script HEAD vs upstream-ref.
5. **`scripts/install_git_hooks.sh`** — port verbatim. Installs
   pre-commit wrapper (already present from TASK-003) AND the three
   security-review hooks (this task). Symlinks on Ubuntu, copies on
   Windows.

**Follow-on edits:**

- `.claude/settings.json` — add `Bash(python scripts/security_review_changes.py:*)` to the allowlist.
- `.gitignore` — already added `.claude/security-review-latest.md` under TASK-002.
- `docs/developers/SECURITY_REVIEW.md` — port verbatim (the doc lives in TASK-006's scope structurally but ships here so it lands with the mechanism).

## Acceptance Criteria

- [x] `scripts/security_review_changes.py` exists and runs (`python
      scripts/security_review_changes.py HEAD HEAD` exits 0 with a
      "no changes" finding).
- [x] The three git-hooks files exist under `scripts/git-hooks/` and
      are executable.
- [x] `bash scripts/install_git_hooks.sh` succeeds; `.git/hooks/`
      now contains pre-commit, pre-merge-commit, post-merge, and
      pre-rebase entries pointing at this repo's scripts.
- [x] An intentional bad-pull simulation (a branch with a new
      `Bash(curl:*)` allow entry merged into a test branch)
      triggers a HIGH finding from `pre-merge-commit` and blocks
      the merge.
- [x] `PL_SKIP_SECURITY_REVIEW=1 git pull` bypasses the hook and
      logs the bypass.
- [x] `docs/developers/SECURITY_REVIEW.md` exists, links into
      `AUTONOMY.md § No-published-effect` (forward-link will resolve
      when TASK-012 lands AUTONOMY.md).

## Test Plan

1. Apply the installer; verify `.git/hooks/` symlinks.
2. Create a throw-away branch with a benign-looking but flagged
      change (`+ "Bash(curl:*)"` in a fake settings file). Merge
      into another throw-away branch; `pre-merge-commit` should
      block.
3. `PL_SKIP_SECURITY_REVIEW=1` re-runs the same merge cleanly.

## Notes

CircuitSmith's `security_review_changes.py` runs an optional Claude
CLI pass when the `claude` binary is on PATH. PartsLedger inherits
this behaviour — set `PL_SKIP_CLAUDE_REVIEW=1` to skip the semantic
pass and run static rules only.
