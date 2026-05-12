---
name: ts-idea-list
description: Show all open ideas from docs/developers/ideas/open/
---

# ts-idea-list

> **Source of truth: `docs/developers/ideas/OVERVIEW.md`**
> Do NOT scan individual idea files to discover IDs or titles.
> `OVERVIEW.md` is auto-maintained by
> `scripts/update_idea_overview.py` and is always up to date.

Read `docs/developers/ideas/OVERVIEW.md` and reformat the `## Open
Ideas` table as a compact list.

Format, sorted by ID ascending:

```
ID        Title                                         Description
IDEA-003  Additional Hardware Support                   Extend compatibility to platforms like Arduino Nano
IDEA-004  nRF Hardware Testing                          Thoroughly test and validate the nRF52840 implementation
...
```

After the list, print a one-line summary: `N open idea(s).`
Do not list archived ideas and do not suggest next steps.
