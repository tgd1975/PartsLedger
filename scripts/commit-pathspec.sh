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
# Untracked files are NOT auto-added. The caller (the /commit skill)
# must `git add` any untracked pathspec entries before invoking this
# script. Auto-adding masks parallel-session races: a foreign session
# can land a commit that adds the same path to the tree between the
# wrapper's untracked check and its `git commit`, producing two
# "successful" commits that both add the same file (TASK-329).
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
#
# Exit codes:
#   0  commit succeeded
#   1  commit failed (hook, git, or invalid args)
#   2  pathspec contains an untracked entry

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
GIT_DIR="$(git rev-parse --git-dir)"

TOKEN_FILE="${GIT_DIR}/pl-commit-token"

# Parse --no-verify flag (must come before message if present).
NO_VERIFY=""
if [ "${1:-}" = "--no-verify" ]; then
    NO_VERIFY="--no-verify"
    shift
fi

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 [--no-verify] \"<message>\" <file> [<file> …]" >&2
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
    echo "ERROR: untracked pathspec entries (run 'git add' first):" >&2
    for f in "${UNTRACKED[@]}"; do
        echo "  $f" >&2
    done
    exit 2
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
