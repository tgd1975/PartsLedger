# awesome-task-system — Distribution Layout

This directory is the **canonical source of truth** for the task system.
Inside this repo, edits land here once and `scripts/sync_task_system.py`
propagates them to the live locations under `scripts/`, `.claude/skills/`,
and `docs/developers/task-system.yaml`. For external projects copying the
package out, the directory mapping below describes where each file goes.

## Directory mapping

```
awesome-task-system/
├── scripts/                       → <your-repo>/scripts/
│   ├── housekeep.py
│   ├── task_system_config.py
│   ├── update_idea_overview.py
│   ├── update_task_overview.py
│   ├── sync_task_system.py        (in-repo source-of-truth sync; safe to omit
│   │                               in external installs that vendor the package
│   │                               only once)
│   └── tests/                     → <your-repo>/scripts/tests/
│       ├── test_housekeep.py
│       ├── test_task_system_config.py
│       └── test_update_idea_overview.py
├── skills/                        → <your-repo>/.claude/skills/
│   ├── tasks/
│   ├── ts-epic-list/
│   ├── ts-epic-new/
│   ├── ts-idea-archive/
│   ├── ts-idea-list/
│   ├── ts-idea-new/
│   ├── ts-task-active/
│   ├── ts-task-done/
│   ├── ts-task-list/
│   ├── ts-task-new/
│   ├── ts-task-pause/
│   └── ts-task-reopen/
└── config/
    └── task-system.yaml           → <your-repo>/docs/developers/task-system.yaml
                                     (or set TASK_SYSTEM_CONFIG env var to any path)
```

## Task folder layout

`housekeep.py` creates and scans these subfolders under
`docs/developers/tasks/` (or whatever `tasks.base_folder` points at):

```
tasks/
├── open/      newly scaffolded tasks; nothing has started yet
├── active/    work has begun (gated by tasks.active.enabled)
├── paused/    work has begun but is blocked on a prerequisite
│              (gated by tasks.paused.enabled — paused depends on active)
├── closed/    work is finished; awaits release archival
└── archive/   per-release snapshots: archive/v0.3.0/, archive/v0.4.0/, …
               (gated by tasks.releases.enabled)
```

Status transitions (see `TASK_SYSTEM.md` for the full lifecycle):

```
open ─activate─> active ─pause─> paused ─continue─> active ─done─> closed
                   │                                  │
                   └────── done ─────────────────────>┘
                                                      └─ done from paused ─> closed
```

`active`/`paused` → `open` is a manual escape hatch — used only when a
task was started by mistake. There is no skill flag for it; do a
`git mv` and edit `status:` by hand.

## Edit-and-sync workflow (in-repo)

`awesome-task-system/` is the source of truth. Live copies under
`scripts/`, `.claude/skills/`, and `docs/developers/task-system.yaml`
are generated artifacts.

1. **Edit the package copy** under `awesome-task-system/`. Never edit
   the live copy directly — the divergence guard will reject the commit.
2. **Run the sync script** to propagate changes:

   ```bash
   python scripts/sync_task_system.py --apply
   ```

3. **Commit both sides together.** The pre-commit hook calls
   `sync_task_system.py --check`; if package and live disagree, the
   commit is rejected with the file paths and the fix command.

If the sync script refuses to overwrite a live copy, that copy has
uncommitted modifications. Either commit them first or pass `--force`
to clobber them.

The sync direction is one-way: **package → live, never the reverse.**
The mirror set is defined in the `MIRRORS` list at the top of
`scripts/sync_task_system.py`. Add new mirrored files to that list when
they are introduced.

## First-time setup (external projects)

After copying:

1. Edit `task-system.yaml` to set your `base_folder` paths.
2. Register the skills in `.vibe/config.toml`:

   ```toml
   enabled_skills = ["tasks", "ts-epic-list", "ts-epic-new",
                     "ts-idea-archive", "ts-idea-list", "ts-idea-new",
                     "ts-task-active", "ts-task-done", "ts-task-list",
                     "ts-task-new", "ts-task-pause", "ts-task-reopen"]
   ```

3. Run `python scripts/housekeep.py --init` to create the folder structure
   — `open/`, `active/`, `paused/`, `closed/`, plus `archive/` if releases
   are enabled.
4. Run `python scripts/housekeep.py --apply` to generate overview files.

## Self-contained check

None of the scripts reference project-specific paths at module load time.
All paths are read from `task-system.yaml` (or its defaults) at runtime.
The default values (`docs/developers/tasks`, `docs/developers/ideas`) are
overridable — set your own `base_folder` in the config file.
