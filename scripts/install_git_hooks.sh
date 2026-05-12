#!/usr/bin/env bash
# Install repo-side git hooks into .git/hooks/.
#
# Two install patterns:
#   - Security-review hooks (pre-merge-commit, post-merge, pre-rebase): symlinked
#     from scripts/git-hooks/, with a copy-fallback for Windows + Git Bash setups
#     where symlinks are unavailable. Re-install required after edits.
#   - Pre-commit hook: a tiny wrapper is written to .git/hooks/pre-commit that
#     execs scripts/pre-commit. The wrapper does not need re-installation when
#     scripts/pre-commit is edited — works the same on Linux and Windows.
#
# Re-run is idempotent. Existing non-link / non-matching files are backed up
# to <name>.backup.<timestamp> rather than overwritten.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC_DIR="$REPO_ROOT/scripts/git-hooks"
DST_DIR="$REPO_ROOT/.git/hooks"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ ! -d "$SRC_DIR" ]; then
    echo -e "${RED}error: $SRC_DIR not found${NC}" >&2
    exit 1
fi
if [ ! -d "$DST_DIR" ]; then
    mkdir -p "$DST_DIR"
fi

ts() { date +%Y%m%d-%H%M%S; }

install_one() {
    local name="$1"
    local src="$SRC_DIR/$name"
    local dst="$DST_DIR/$name"

    chmod +x "$src" 2>/dev/null || true

    if [ -L "$dst" ]; then
        local cur
        cur="$(readlink "$dst" || true)"
        if [ "$cur" = "$src" ] || [ "$cur" = "../../scripts/git-hooks/$name" ]; then
            echo -e "  ${GREEN}ok${NC}    $name (already linked)"
            return
        fi
        echo -e "  ${YELLOW}backup${NC} $name -> $name.backup.$(ts) (was symlink to $cur)"
        mv "$dst" "$dst.backup.$(ts)"
    elif [ -e "$dst" ]; then
        echo -e "  ${YELLOW}backup${NC} $name -> $name.backup.$(ts)"
        mv "$dst" "$dst.backup.$(ts)"
    fi

    if ln -s "../../scripts/git-hooks/$name" "$dst" 2>/dev/null; then
        echo -e "  ${GREEN}link${NC}  $name"
    else
        cp "$src" "$dst"
        chmod +x "$dst"
        echo -e "  ${YELLOW}copy${NC}  $name (symlink failed; re-run installer after hook script changes)"
    fi
}

install_wrapper() {
    # Write a tiny wrapper hook into .git/hooks/$name that execs the real
    # script at $target_rel (relative to $REPO_ROOT). Wrappers don't need
    # re-installation when the target script is edited — Windows-friendly,
    # because no symlink is involved.
    local name="$1"
    local target_rel="$2"
    local dst="$DST_DIR/$name"
    local target_abs="$REPO_ROOT/$target_rel"

    if [ ! -f "$target_abs" ]; then
        echo -e "  ${RED}skip${NC}  $name (target $target_rel not found)"
        return
    fi
    chmod +x "$target_abs" 2>/dev/null || true

    local desired
    desired="$(printf '#!/usr/bin/env bash\nexec "$(git rev-parse --show-toplevel)/%s" "$@"\n' "$target_rel")"

    if [ -f "$dst" ] && [ ! -L "$dst" ]; then
        if [ "$(cat "$dst")" = "$desired" ]; then
            echo -e "  ${GREEN}ok${NC}    $name (wrapper already current)"
            return
        fi
        echo -e "  ${YELLOW}backup${NC} $name -> $name.backup.$(ts)"
        mv "$dst" "$dst.backup.$(ts)"
    elif [ -L "$dst" ]; then
        echo -e "  ${YELLOW}backup${NC} $name -> $name.backup.$(ts) (was symlink)"
        mv "$dst" "$dst.backup.$(ts)"
    fi

    printf '%s' "$desired" > "$dst"
    chmod +x "$dst"
    echo -e "  ${GREEN}wrap${NC}  $name -> $target_rel"
}

echo "Installing security-review git hooks into .git/hooks/:"
for h in pre-merge-commit post-merge pre-rebase; do
    install_one "$h"
done

echo ""
echo "Installing pre-commit wrapper into .git/hooks/:"
install_wrapper "pre-commit" "scripts/pre-commit"

echo ""
echo -e "${GREEN}done.${NC} Hooks active. To bypass security review: PL_SKIP_SECURITY_REVIEW=1 git pull"
echo "Reports are written to .claude/security-review-latest.md"
