---
name: tasks
description: Show all open and active tasks from docs/developers/tasks/OVERVIEW.md (paused hidden by default; --paused or --all to include)
---

# tasks

> **Source of truth: `docs/developers/tasks/OVERVIEW.md`**
> Do NOT scan individual task files to discover epics, IDs, or effort values.
> The `<!-- GENERATED -->` … `<!-- END GENERATED -->` block in `OVERVIEW.md` is
> auto-maintained by `scripts/update_task_overview.py` and is always up to date.
> Read it directly — it is faster and avoids re-deriving what the script already computed.

Read `docs/developers/tasks/OVERVIEW.md` (the `<!-- GENERATED -->` block) and
reformat its content as a structured list.

`open` and `active` tasks appear by default. `paused` tasks are hidden
unless the user passes `--paused` (show paused too) or `--all`
(show open + active + paused) — the default matches the "what should I
work on?" intent. Active tasks are visually distinguished — render
their title in **bold** and include an `active` badge in the status
column. Paused tasks (when shown) get a `paused` badge.

**Un-epic'd tasks** (no `epic` field) — one compact table, sorted by ID ascending:

```
ID        Status  Effort              Complexity  Title
TASK-033  open    Large (8-24h)       Medium      Create Setup/Installation Demo Video
TASK-049  open    Small (<2h)         Junior      Setup video platform channel
TASK-217  active  Medium (2-8h)       Medium      **Create task-system.yaml config**
...
```

**Epic'd tasks** — rendered under `### Task Epics` → `#### <EpicName>` sub-sections,
sorted alphabetically by epic name, tasks within each epic sorted by `order` (ascending).
Show a richer table with Order, Human-in-loop, and mark `Main` with ★:

```
#### task-system

Order  ID        Effort        Complexity  Human-in-loop  Title
1      TASK-208  Small (<2h)   Junior      No             Migrate frontmatter group: → epic:
2      TASK-209  Small (<2h)   Medium      Clarification  Update tooling to read epic: field
...
```

After all sections, print the total count of open tasks (un-epic'd + all epics).
Do not suggest actions or next steps — just display the list.
