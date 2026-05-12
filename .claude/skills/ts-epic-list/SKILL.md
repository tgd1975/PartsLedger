---
name: ts-epic-list
description: List all epics with derived status, assigned owner, and task counts
---

# ts-epic-list

The user invokes this as `/ts-epic-list` with no arguments.

## What to do

Read epic files directly from `docs/developers/tasks/{open,active,closed}/`.
Epic files are those whose `id:` field starts with `EPIC-`.

For each epic, also count tasks (files whose `id:` starts with `TASK-`)
that share the same `epic:` value across all three status folders.

Derive each epic's status using the same rule as `housekeep.py`:

- If any task is `active` → **active**
- If all tasks are `closed` → closed
- Otherwise → open
- If the epic has no tasks → use the status from the epic file itself

## Output format

Print one line per epic, sorted by epic `id` ascending:

```
EPIC-ID   Status    Assigned   Open  Active  Closed  Title
EPIC-001  active    —           3      1       8      Unified task and idea system
EPIC-002  open      —           2      0       0      BLE Config Service
EPIC-003  closed    —           0      0       5      Cleanup tasks
```

- `Status` is bold when active: **active**
- `Assigned` shows `@username` when set, `—` otherwise
- Counts are right-aligned numbers
- After the table, print a one-line summary: `N epic(s) — X open, Y active, Z closed.`

Do not list archived releases. Do not suggest next steps.
