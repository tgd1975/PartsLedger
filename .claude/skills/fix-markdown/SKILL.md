---
name: fix-markdown
description: Auto-fix markdown lint issues across all .md files and report what changed
---

# fix-markdown

Run markdownlint-cli2 in fix mode across all Markdown files and report what was changed.

Steps:

1. Record which `.md` files currently have unstaged changes:

   ```bash
   git diff --name-only -- '*.md'
   ```

2. Run:

   ```bash
   make lint-markdown
   ```

3. Compare the git status before and after to determine which files were auto-fixed by
   the linter.

4. Report:
   - Files fixed (if any), one per line
   - "All Markdown files already lint-clean." if nothing changed

5. If files were fixed, remind the user to review the changes and stage them before
   committing. The pre-commit hook runs markdownlint on staged `.md` files automatically.

Do not stage or commit — leave that to the user.
