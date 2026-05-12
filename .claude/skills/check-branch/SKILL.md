---
name: check-branch
description: Guard against committing directly to main — verifies the current branch and warns or stops if on main
---

# check-branch

Used internally by other skills (e.g. `ts-task-done`) and invokable as `/check-branch` before any commit.

Steps:

1. Run `git rev-parse --abbrev-ref HEAD` to get the current branch name.
2. If the branch is **not** `main`: report the branch name and proceed. No action needed.
3. If the branch **is** `main`:
   - Warn the user: "You are on the `main` branch. Committing directly to main is usually wrong."
   - Ask: "Do you want to create a feature branch first, or do you intentionally want to commit to main?"
   - Wait for the user's answer before proceeding.
   - If the user wants a branch: ask for a branch name, run `git checkout -b <name>`, then continue.
   - If the user confirms they want to stay on main: note this and continue.
