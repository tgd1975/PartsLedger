---
name: ts-epic-new
description: Scaffold a new epic file in docs/developers/tasks/open/ and run housekeep
---

# ts-epic-new

The user invokes this as `/ts-epic-new <epic-name> "Short title"`
(e.g. `/ts-epic-new task-system "Unified task and idea system"`).

If either argument is missing, ask for it before proceeding.

## Epic file format

Epic files live alongside task files under
`docs/developers/tasks/{open,active,closed}/`. `housekeep.py` moves
them to the folder that matches their derived status (all-closed →
`closed/`, any-active → `active/`, otherwise `open/`).

```markdown
---
id: EPIC-NNN            # auto-incremented across all epic files
name: <epic-name>       # the value that tasks reference via `epic: <name>`
title: <Short title>    # human-readable heading
status: open            # derived by housekeep.py — do not edit manually
opened: YYYY-MM-DD
closed:                 # set by housekeep.py when all tasks close
assigned:               # optional — username of the owner
branch: feature/<slug>  # optional — suggested git branch for tasks in this epic.
                        # Auto-filled with feature/<slug> (the same slug used in
                        # the filename). The user may edit or delete this line
                        # before committing. /ts-task-active soft-warns when the
                        # current branch differs from this value.
---

# <Short title>

<body — short motivation and scope. If the epic was seeded by one or more
ideas, name them explicitly in plain text, e.g.:
  "Seeded by IDEA-006 (Macros)."
  "Seeded by IDEA-009 (Long Press Event) and IDEA-010 (Double Press Event)."
Use the idea ID and title only — no markdown links, no hrefs.>

## Tasks

Tasks are listed automatically in the Task Epics section of
`docs/developers/tasks/OVERVIEW.md` and in `EPICS.md` / `KANBAN.md`.
```

## Idea linking

When the epic is rooted in one or more ideas, include a plain-text sentence in
the body naming those ideas by ID and title:

```
Seeded by IDEA-006 (Macros).
Seeded by IDEA-009 (Long Press Event) and IDEA-010 (Double Press Event).
```

Do **not** use markdown links or href syntax — idea files move between
`open/` and `archived/` as they are resolved, so paths rot. Plain text stays
accurate indefinitely.

## Steps

0. Run `/check-branch`.
1. Determine the next EPIC-NNN by scanning
   `docs/developers/tasks/{open,active,closed}/` for `epic-*.md`
   filenames and frontmatter `id: EPIC-NNN`. Add 1.
2. Build the filename: `epic-NNN-<slug>.md` where the slug is the
   epic name (lowercase, hyphenated, max 50 chars).
3. Ask the user (in the same message as any other missing-arg questions):
   "Does this epic originate from one or more ideas? If so, provide the
   IDEA-NNN IDs and titles." Skip this question if the user already
   supplied idea context in their invocation.
4. Write the file to `docs/developers/tasks/open/` using the template
   above. Fill `id`, `name`, `title`, `opened` (today in YYYY-MM-DD),
   and leave `status: open`, `closed:` empty, `assigned:` empty. Set
   `branch: feature/<slug>` using the **exact slug from step 2** —
   reuse the value verbatim, do not re-derive it from the title. If
   the user provided idea IDs, include the plain-text seeding sentence
   in the body (see **Idea linking** above). The user can add
   `assigned:` manually later — not prompted by default.
5. Run `python scripts/housekeep.py --apply` to regenerate OVERVIEW.md.
6. Report the new epic ID and file path.

The filename slug is already lowercase + hyphens + digits, which is
always a valid git ref — no extra sanitization is needed before
writing it as `feature/<slug>`. Do not invent one.

Do not commit — epics are usually introduced together with their first
tasks, and the user will commit the bundle.
