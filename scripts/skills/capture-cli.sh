#!/usr/bin/env bash
# Skill wrapper for /capture — TASK-038.
#
# Runs `python -m partsledger.capture` with all flags forwarded verbatim.
# Interpreter resolution order:
#   1. $PL_PYTHON if set in the environment.
#   2. The project venv at `<repo>/.venv/bin/python`, if it exists. The
#      Claude-Code Bash tool spawns non-interactive shells that don't load
#      direnv, so $PL_PYTHON from .envrc is invisible here. Auto-detecting
#      the sibling venv covers that case without forcing every developer to
#      hard-code the path.
#   3. Plain `python` on PATH.
#
# $PL_* env vars from the surrounding session are inherited automatically.
# Exit codes are the CLI's exit codes — propagated as the skill outcome.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ -n "${PL_PYTHON:-}" ]]; then
    PYTHON_BIN="$PL_PYTHON"
elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
else
    PYTHON_BIN="python"
fi

exec "$PYTHON_BIN" -m partsledger.capture "$@"
