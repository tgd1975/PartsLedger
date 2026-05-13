---
name: ts-idea-archive
description: Move an idea from docs/developers/ideas/open/ to archived/ and commit
---

# ts-idea-archive

The user invokes this as `/ts-idea-archive IDEA-NNN` (or with a partial
ID like `26`).

Steps:

0. Run `/check-branch` to verify the current branch is not `main`.
1. Find the matching file in `docs/developers/ideas/open/` whose
   filename contains the given ID (case-insensitive, e.g. `idea-026`).
   If no file is found, report the error and stop.
2. Ask the user for a one-line archive reason (e.g. "Converted to
   TASK-123", "Superseded by IDEA-042", "No longer relevant"). If the
   user declines with an empty answer, skip step 3.
3. Prepend a `## Archive Reason` section to the body (immediately after
   the frontmatter `---` closing line) containing today's date
   (YYYY-MM-DD) and the reason on one line, e.g.:

   ```markdown
   ## Archive Reason

   2026-04-23 — Converted to TASK-123.
   ```

4. Move the file to `docs/developers/ideas/archived/` using `git mv`.
5. Run `python scripts/update_idea_overview.py` to regenerate
   `docs/developers/ideas/OVERVIEW.md`.
6. Stage the moved file and the regenerated OVERVIEW.md, then create a
   commit with the message:
   `archive IDEA-NNN: <idea title from frontmatter>`
   Do NOT push.
7. Report: "IDEA-NNN archived, OVERVIEW.md updated, and committed."
