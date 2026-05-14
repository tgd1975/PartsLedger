# Scripts Documentation

This folder contains utility scripts for development, CI/CD, and maintenance tasks.

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| [`codeowner_hook.py`](codeowner_hook.py) | Code-owner reminder hook — PreToolUse for ``Edit`` and ``Write``. | `python3 codeowner_hook.py` |
| [`commit-pathspec.sh`](commit-pathspec.sh) | scripts/commit-pathspec.sh — wrapper for git's pathspec-form commit | `./commit-pathspec.sh` |
| [`housekeep.py`](housekeep.py) | Central housekeeping for the task system. | `python3 housekeep.py` |
| [`install_git_hooks.sh`](install_git_hooks.sh) | Install repo-side git hooks into .git/hooks/. | `./install_git_hooks.sh` |
| [`lint_hedge_language.py`](lint_hedge_language.py) | Pre-commit shim for ``partsledger.inventory.hedge_lint``. | `python3 lint_hedge_language.py` |
| [`lint_inventory.py`](lint_inventory.py) | Pre-commit shim for ``partsledger.inventory.lint``. | `python3 lint_inventory.py` |
| [`pre-commit`](pre-commit) | Pre-commit hook for PartsLedger. | `python3 pre-commit` |
| [`release_burnup.py`](release_burnup.py) | Generate the burn-up section for OVERVIEW.md. | `python3 release_burnup.py` |
| [`release_snapshot.py`](release_snapshot.py) | Snapshot OVERVIEW / EPICS / KANBAN into `archive/<version>/` on release. | `python3 release_snapshot.py` |
| [`security_review_changes.py`](security_review_changes.py) | Security review for incoming changes (pull / merge / rebase). | `python3 security_review_changes.py` |
| [`task_system_config.py`](task_system_config.py) | Shared config loader for the task system. | `python3 task_system_config.py` |
| [`update_idea_overview.py`](update_idea_overview.py) | Regenerate docs/developers/ideas/OVERVIEW.md from idea files in | `python3 update_idea_overview.py` |
| [`update_scripts_readme.py`](update_scripts_readme.py) | Automatically update scripts/README.md based on current scripts in the folder. | `python3 update_scripts_readme.py` |
| [`update_task_overview.py`](update_task_overview.py) | DEPRECATED — prefer `scripts/housekeep.py` for the full flow (file | `python3 update_task_overview.py` |

## Script Details

### codeowner_hook.py

**Purpose**: Code-owner reminder hook — PreToolUse for ``Edit`` and ``Write``.

**Usage**: `python3 codeowner_hook.py`

### commit-pathspec.sh

**Purpose**: scripts/commit-pathspec.sh — wrapper for git's pathspec-form commit

**Usage**: `./commit-pathspec.sh`

### housekeep.py

**Purpose**: Central housekeeping for the task system.

**Usage**: `python3 housekeep.py`

### install_git_hooks.sh

**Purpose**: Install repo-side git hooks into .git/hooks/.

**Usage**: `./install_git_hooks.sh`

### lint_hedge_language.py

**Purpose**: Pre-commit shim for ``partsledger.inventory.hedge_lint``.

**Usage**: `python3 lint_hedge_language.py`

### lint_inventory.py

**Purpose**: Pre-commit shim for ``partsledger.inventory.lint``.

**Usage**: `python3 lint_inventory.py`

### pre-commit

**Purpose**: Pre-commit hook for PartsLedger.

**Usage**: `python3 pre-commit`

### release_burnup.py

**Purpose**: Generate the burn-up section for OVERVIEW.md.

**Usage**: `python3 release_burnup.py`

### release_snapshot.py

**Purpose**: Snapshot OVERVIEW / EPICS / KANBAN into `archive/<version>/` on release.

**Usage**: `python3 release_snapshot.py`

### security_review_changes.py

**Purpose**: Security review for incoming changes (pull / merge / rebase).

**Usage**: `python3 security_review_changes.py`

### task_system_config.py

**Purpose**: Shared config loader for the task system.

**Usage**: `python3 task_system_config.py`

### update_idea_overview.py

**Purpose**: Regenerate docs/developers/ideas/OVERVIEW.md from idea files in

**Usage**: `python3 update_idea_overview.py`

### update_scripts_readme.py

**Purpose**: Automatically update scripts/README.md based on current scripts in the folder.

**Usage**: `python3 update_scripts_readme.py`

### update_task_overview.py

**Purpose**: DEPRECATED — prefer `scripts/housekeep.py` for the full flow (file

**Usage**: `python3 update_task_overview.py`
