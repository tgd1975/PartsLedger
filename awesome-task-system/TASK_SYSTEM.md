# Task System — User Guide

A lightweight docs-as-code task and idea management system for small teams.
Tasks and ideas are Markdown files with YAML frontmatter; folder = status.
Claude Code skills provide the CLI. `housekeep.py` keeps everything in sync.

---

## Prerequisites

- Python 3.10+
- Claude Code CLI with `.vibe/config.toml` for skill registration

---

## Source-of-truth (in-repo)

Within this repository, `awesome-task-system/` is the canonical source.
The scripts under `scripts/`, the skills under `.claude/skills/`, and
`docs/developers/task-system.yaml` are generated artifacts — edit the
package copy and run `python scripts/sync_task_system.py --apply` to
propagate. The pre-commit hook calls `sync_task_system.py --check` and
rejects any commit where the two sides drift. See `LAYOUT.md` for the
full mirror set and the divergence-fix command.

---

## Installation

1. **Copy the distribution artifacts** from `awesome-task-system/` into your repo:

   ```
   cp -r awesome-task-system/scripts/* scripts/
   cp -r awesome-task-system/skills/* .claude/skills/
   cp awesome-task-system/config/task-system.yaml docs/developers/
   ```

2. **Edit `docs/developers/task-system.yaml`** — set your `base_folder` paths:

   ```yaml
   tasks:
     base_folder: docs/developers/tasks   # or wherever you want tasks
   ideas:
     base_folder: docs/developers/ideas
   ```

3. **Register skills** in `.vibe/config.toml`:

   ```toml
   enabled_skills = ["ts-epic-list", "ts-epic-new", "ts-idea-archive",
                     "ts-idea-list", "ts-idea-new", "ts-task-active",
                     "ts-task-pause", "ts-task-reopen"]
   ```

4. **Create the folder structure**:

   ```bash
   python scripts/housekeep.py --init
   ```

5. **Generate overview files** (run after any file changes):

   ```bash
   python scripts/housekeep.py --apply
   ```

---

## Config reference (`task-system.yaml`)

| Key | Default | Effect |
|-----|---------|--------|
| `tasks.base_folder` | `docs/developers/tasks` | Root folder for task files |
| `tasks.active.enabled` | `true` | Create and scan `active/` subfolder |
| `tasks.paused.enabled` | `true` | Create and scan `paused/` subfolder. Forced off when `tasks.active.enabled` is false (paused depends on active). |
| `tasks.epics.enabled` | `true` | Process epic files; generate `EPICS.md` |
| `tasks.releases.enabled` | `true` | Create `archive/` subfolder for releases |
| `ideas.enabled` | `true` | Create and scan ideas folder |
| `ideas.base_folder` | `docs/developers/ideas` | Root folder for idea files |
| `visualizations.epics.enabled` | `true` | Generate `EPICS.md` |
| `visualizations.epics.style` | `dependency-graph` | `dependency-graph` or `gantt` |
| `visualizations.kanban.enabled` | `true` | Generate `KANBAN.md` |

Override any key by setting `TASK_SYSTEM_CONFIG=/path/to/your-config.yaml`.

---

## Skill reference

| Skill | Usage | Effect |
|-------|-------|--------|
| `/ts-task-active TASK-NNN` | Mark task as active (or resume from paused) — invoked by the user, or auto-invoked by the agent the moment it starts editing for the task | Moves file to `active/`, runs housekeep |
| `/ts-task-pause TASK-NNN` | Pause active task | Sets `status: paused`, moves file to `paused/`, runs housekeep |
| `/ts-task-reopen TASK-NNN` | Reopen closed task | Moves file to `open/`, runs housekeep |
| `/ts-epic-new <name> "Title"` | Create epic | Scaffolds `EPIC-NNN` file in `open/` |
| `/ts-epic-list` | List epics | Shows all epics with status and task counts |
| `/ts-idea-new <id> "Title"` | Create idea | Scaffolds `IDEA-NNN` file in `ideas/open/` |
| `/ts-idea-list` | List ideas | Shows open ideas from `OVERVIEW.md` |
| `/ts-idea-archive IDEA-NNN` | Archive idea | Moves idea to `archived/`, commits |

---

## Task lifecycle

```
open/ ──[activate]──▶ active/ ──[pause]──▶ paused/
                         │                    │
                         │                    └─[continue]─▶ active/
                         │                    │
                         │                    └─[done]─────▶ closed/
                         └─────[done]────────────────────────▶ closed/

closed/ ──[release]──▶ archive/vX.Y.Z/

(escape hatch: active/ or paused/ → open/ is manual — only when
 a task was activated by mistake. No skill flag; do a `git mv` and
 edit `status:` by hand.)
```

**Task frontmatter fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | `TASK-NNN` (auto-incremented) |
| `title` | yes | Short human-readable title |
| `status` | yes | `open` / `active` / `paused` / `closed` |
| `opened` | yes | `YYYY-MM-DD` |
| `effort` | no | `Trivial` / `Small (<2h)` / `Medium (2-8h)` / `Large` |
| `complexity` | no | `Junior` / `Medium` / `Senior` |
| `epic` | no | Epic name this task belongs to |
| `order` | no | Sort order within the epic |
| `prerequisites` | no | `[TASK-NNN, TASK-MMM]` — for dependency graph |
| `assigned` | no | Username of the owner |
| `human-in-loop` | no | `Main` / `Support` / `Clarification` / `None` |

---

## Idea lifecycle

```
ideas/open/ ──[convert to tasks]──▶ (archived after conversion)
ideas/open/ ──[deprioritise]──▶ ideas/archived/
```

**Idea frontmatter fields:** `id`, `title`, `description` (optional).

---

## Epic lifecycle

Epics are derived automatically: `housekeep.py` sets their status based on their tasks.

- Any task `active` → epic is `active`
- All tasks `closed` → epic is `closed`
- Otherwise → epic is `open`

---

## Generated files

`housekeep.py --apply` regenerates three files automatically:

| File | Contents |
|------|----------|
| `OVERVIEW.md` | Counts, open task table, per-epic tables, closed task list |
| `EPICS.md` | One section per epic with dependency graph or Gantt chart |
| `KANBAN.md` | Mermaid kanban board with Open / Active / Closed columns |

These files are always regenerated from source — do not edit them manually.

---

## Updating the task system

The task system is distributed as a directory snapshot. To update:

1. Pull the latest `awesome-task-system/` from the source repo.
2. Copy the updated scripts and skills over your existing ones.
3. Re-run `python scripts/housekeep.py --init` (safe — it is idempotent).
4. Re-run `python scripts/housekeep.py --apply` to regenerate views.
