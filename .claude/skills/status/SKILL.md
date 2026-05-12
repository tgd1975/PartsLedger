---
name: status
description: Run the routine git reconnaissance bundle in a single Bash call — current branch, last 3 commits, staged short, working short. Use this instead of separate `git branch --show-current` / `git log` / `git status --short` calls.
---

# status

Invoked as `/status` whenever you would otherwise reach for any of:

- `git status` / `git status --short`
- `git log --oneline -3` (or `-5`, `-8`, `-10`)
- `git rev-parse --abbrev-ref HEAD` / `git branch --show-current`
- Composites like `git log --oneline -3 && git status --short`

The skill prints a four-section report from one Bash invocation, which
collapses dozens of permission prompts per session into one.

## Steps

Run the command below as a single Bash call:

```bash
{
  printf '== branch ==\n'
  git rev-parse --abbrev-ref HEAD
  printf '\n== last 3 commits ==\n'
  git log --oneline -3
  printf '\n== staged ==\n'
  git diff --cached --name-status
  printf '\n== working tree ==\n'
  git status --short
}
```

Print the captured output verbatim. If any of the inner commands fails
(e.g. not in a git repo), let the error surface — do not swallow it.

## When to use

- At the start of a session to anchor on current state before deciding next steps.
- After a commit or branch switch to confirm the new state.
- Whenever you'd otherwise reach for two or more of the recon commands above.

## When NOT to use

- When you only need one specific piece (e.g. just the branch name for a
  conditional). Reach for the targeted command — `/status` is for the bundle.
- For diff content. Use `git diff` / `git diff --cached` directly.
