#!/usr/bin/env bash
# scripts/commit-pathspec.sh — wrapper for git's pathspec-form commit
#
# This is the executable behind the /commit skill. It writes the
# provenance token at .git/pl-commit-token and runs
# `git commit -m "..." -- <files>`.
#
# The pre-commit hook validates the token and rejects commits that
# did not come from this wrapper. See docs/developers/COMMIT_POLICY.md
# for the full design.
#
# Untracked files: by default the wrapper rejects pathspec entries that
# are unknown to git with exit code 2. Pass --stage-untracked to opt
# into atomic in-wrapper staging — the wrapper detects untracked
# entries, `git add`s them itself, then commits, all in one process.
#
# Why an opt-in flag instead of always auto-adding: TASK-329 removed
# the original always-on auto-add because it masked parallel-session
# races (a foreign session could land a commit that adds the same path
# between the wrapper's untracked check and its `git commit`, producing
# two "successful" adds of the same file). The flag preserves that
# default-strict behaviour for any caller that wants race detection,
# while giving the /commit skill a way to handle untracked files
# without the agent typing `git add` (the project bans agent-typed
# `git add` via a deny rule in .claude/settings.json — see the
# no-git-add-use-commit-pathspec memory). The race window with the
# flag is one wrapper process; without it, the window spans
# skill-add + wrapper-commit (two processes) — so in-wrapper staging
# is strictly tighter than skill-side staging, just less strict than
# fail-fast.
#
# Renames and deletions ARE supported (TASK-347). The pre-flight check
# accepts any pathspec entry that is in HEAD or has an index entry —
# rename sources (after `git mv A B`, A is in HEAD but not in index)
# and on-disk-deleted tracked files both pass. Only paths unknown to
# both HEAD and index are rejected as truly untracked.
#
# Usage:
#   scripts/commit-pathspec.sh "<message>" <file> [<file> …]
#   scripts/commit-pathspec.sh --no-verify "<message>" <file> [<file> …]
#   scripts/commit-pathspec.sh --stage-untracked "<message>" <file> [<file> …]
#   (flags may be combined; order does not matter)
#
# Exit codes:
#   0  commit succeeded
#   1  commit failed (hook, git, or invalid args)
#   2  pathspec contains an untracked entry (and --stage-untracked
#      was not passed)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
GIT_DIR="$(git rev-parse --git-dir)"

TOKEN_FILE="${GIT_DIR}/pl-commit-token"

# Parse flags (must come before message if present). Accept --no-verify
# and --stage-untracked in either order.
NO_VERIFY=""
STAGE_UNTRACKED=0
while [ "$#" -gt 0 ]; do
    case "${1:-}" in
        --no-verify)
            NO_VERIFY="--no-verify"
            shift
            ;;
        --stage-untracked)
            STAGE_UNTRACKED=1
            shift
            ;;
        *)
            break
            ;;
    esac
done

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 [--no-verify] [--stage-untracked] \"<message>\" <file> [<file> …]" >&2
    exit 1
fi

MESSAGE="$1"
shift

# Reject empty pathspec — the whole point is explicit file lists.
if [ "$#" -eq 0 ]; then
    echo "ERROR: no files in pathspec. /commit requires at least one file." >&2
    exit 1
fi

# Step 1: reject truly-untracked pathspec entries.
#
# Pathspec form requires every named file to be known to git in *some*
# capacity — either tracked in HEAD (so it can be modified or deleted)
# or staged in the index (so it can be added or rename-destinationed).
# The /commit skill is responsible for `git add`ing new files before
# invoking this wrapper; if any pathspec entry is unknown to git here,
# fail fast so the agent refreshes (and may discover a foreign-session
# commit) rather than silently adding.
#
# A naïve `git ls-files --error-unmatch -- "$f"` check rejects rename
# *sources*: after `git mv A B`, A is removed from the index and only
# B is present, so `ls-files A` fails — but A is not untracked, it is
# the source side of an in-progress rename and must reach the commit
# for git to record it as a rename rather than a delete + add. The
# correct primitive is: accept if the path is in HEAD OR has any index
# entry (add, modify, delete-source, etc.). Reject only if it is
# unknown to both.
UNTRACKED=()
for f in "$@"; do
    # In the index? Catches: tracked-modified, staged-add,
    # rename-destination. Misses: rename-source (no index entry).
    if git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
        continue
    fi
    # In HEAD? Catches: rename-source, staged-deletion of a tracked
    # file, plain on-disk deletion of a tracked file (no `git rm`).
    if git cat-file -e "HEAD:$f" 2>/dev/null; then
        continue
    fi
    UNTRACKED+=("$f")
done
if [ "${#UNTRACKED[@]}" -gt 0 ]; then
    if [ "${STAGE_UNTRACKED}" -eq 1 ]; then
        # In-wrapper staging: add each untracked entry. One process, one
        # race window — see the header comment for the rationale.
        for f in "${UNTRACKED[@]}"; do
            git add -- "$f"
        done
    else
        echo "ERROR: untracked pathspec entries (pass --stage-untracked or stage them yourself):" >&2
        for f in "${UNTRACKED[@]}"; do
            echo "  $f" >&2
        done
        exit 2
    fi
fi

# Step 2: write the provenance token. Format: <pid> <nonce> <unix-ts>.
# PID is the shell that will run `git commit` next (i.e. $$).
PID="$$"
NONCE="$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
NOW="$(date +%s)"
echo "${PID} ${NONCE} ${NOW}" > "${TOKEN_FILE}"

# Best-effort cleanup if anything below this point fails before the
# hook reads (and deletes) the token. Without this, a stale token
# could authorise a later raw `git commit` within the 60s TTL.
trap 'rm -f "${TOKEN_FILE}"' EXIT

# Step 3: commit in pathspec form. The hook will validate and delete
# the token. On hook success, EXIT trap runs but file is already gone
# (rm -f is no-op).
if [ -n "${NO_VERIFY}" ]; then
    git commit "${NO_VERIFY}" -m "${MESSAGE}" -- "$@"
else
    git commit -m "${MESSAGE}" -- "$@"
fi
