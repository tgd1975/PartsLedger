---
name: ts-idea-new
description: Scaffold a new idea file in docs/developers/ideas/open/ and regenerate the ideas OVERVIEW.md
---

# ts-idea-new

The user invokes this as `/ts-idea-new "Short idea title"`.

If no title is provided, ask the user for one before proceeding.

Steps:

1. Determine the next IDEA-NNN by reading
   `docs/developers/ideas/OVERVIEW.md` and scanning the idea tables for
   the highest existing IDEA-NNN. Add 1. If OVERVIEW.md does not yet
   exist, fall back to scanning filenames in `docs/developers/ideas/open/`
   and `archived/` for `idea-NNN-*.md`.
2. Build the filename slug from the title: lowercase, spaces and special
   characters → hyphens, max 50 chars, prefixed with the new ID
   (e.g. `idea-042-my-new-idea.md`).
3. Ask the user for a one-line `description:` (shown in the OVERVIEW
   table). Keep it to ~120 chars. If the user declines, omit the field.
3a. Ask the user for a `category:`. Pick one of the project's existing
    categories — read the current set from
    `docs/developers/ideas/OVERVIEW.md` (the `Category` column in the
    Open and Archived tables). Don't invent a new category without
    discussing it with the user — the value is rendered in the index
    and ad-hoc additions break the grouping. If the user genuinely
    can't place the idea, omit the field; the OVERVIEW renders missing
    categories as an em dash.
4. Write the file to `docs/developers/ideas/open/` with this template:

```markdown
---
id: IDEA-NNN
title: <title>
description: <one-line description — optional>
category: <one of the existing categories — optional>
---

# <title>

<body — free-form markdown. Describe the idea, motivation, rough
approach, open questions. No prescribed structure.>
```

<!-- markdownlint-disable MD029 -->
5. Run `python scripts/update_idea_overview.py` to regenerate
   `docs/developers/ideas/OVERVIEW.md`.
6. Report the new idea ID and file path.
<!-- markdownlint-enable MD029 -->

Do not commit — ideas are usually created as part of a larger
brainstorming session, and the user will commit the batch together.

## Sub-notes (do not scaffold here)

If the user asks for a *sub-note* attached to an existing IDEA — a
companion design doc, discarded alternative, deep dive on one
sub-system — that is **not** a new IDEA-NNN. Per the convention in
[`docs/developers/ideas/README.md`](../../../docs/developers/ideas/README.md),
sub-notes are filenames of the form `idea-NNN.<sub-slug>.md` (dot
between the number and the slug, no frontmatter, never in OVERVIEW).
Create them by hand — this skill deliberately does not scaffold them.
