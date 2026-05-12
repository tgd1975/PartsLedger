---
name: ts-task-new
description: Scaffold a new task file in docs/developers/tasks/open/ and update OVERVIEW.md
---

# ts-task-new

The user invokes this as `/ts-task-new "Short task title"` (optionally with
`--effort S|M|L|XL`, `--complexity Junior|Medium|Senior`,
`--epic <EpicName>`, `--order <N>`, and `--assigned <username>`).

Steps:

1. Determine the next task ID by reading `docs/developers/tasks/OVERVIEW.md` — the
   `<!-- GENERATED -->` block lists every open and closed task ID. Find the highest
   TASK-NNN number there and add 1. Do **not** scan individual task files for this;
   OVERVIEW.md is the authoritative index and is always up to date.
2. Build the filename slug from the title: lowercase, spaces/special chars → hyphens,
   max 50 chars, prefixed with the new ID (e.g. `task-059-my-new-task.md`).
3. Generate detailed suggestions for the task:
   - Expand the description with context and purpose
   - Propose 2-3 specific acceptance criteria
   - Determine the test plan (see below)
   - Add relevant notes about dependencies, risks, or considerations

4. **Soft nudge to split L/XL tasks.** If `--effort L` or `--effort XL`
    was supplied (or, when the user did not supply `--effort`, the
    suggestion you arrived at in step 3 is L/XL), pause before writing
    the file and propose a candidate split. Sketch 2–4 smaller tasks,
    each ideally `S` or `M`, that together cover the same ground. Then
    let the user choose one of three paths:

    - **Accept split** → scaffold the smaller tasks instead of the
      original. Chain them via `prerequisites:` (each new task lists
      the previous one), give them the same `epic:` as the original
      proposal, and assign contiguous `order:` values starting from
      whatever `next_order` was derived for the original. Skip step
      4 (the split nudge) recursively for these children — they are already small.
    - **Keep whole** → write the original task, but add a
      `## Sizing rationale` section to the body capturing the user's
      one-line reason for keeping it whole. Ask the user for that
      one-liner before writing the file.
    - **Skip nudge** (genuinely exploratory scope, the user does not
      yet know how to decompose) → write the original task and add
      `## Sizing rationale` containing the single line:
      `Scope not yet decomposable.`

    The nudge is a prompt to think, not a gate. Sometimes a Large
    task really is atomic (a refactor that breaks the build mid-way,
    a third-party migration, a single transactional change) — the
    rationale captures *why* the size is intentional so future readers
    do not have to re-litigate the decision.

    Scope is **scaffold time only**: do not run this check at activation
    time, do not warn from `housekeep.py`, do not block at pre-commit.
    Effort that is bumped up to L/XL after creation is out of scope for
    this nudge.

5. Present the suggestions to the user for review and correction
6. Write the file to `docs/developers/tasks/open/` with this enhanced template:

```markdown
---
id: TASK-NNN
title: <title>
status: open
opened: <YYYY-MM-DD>
effort: <effort label>
complexity: <complexity>
human-in-loop: <hil value>
epic: <EpicName>          # omit entirely if no epic
order: <N>                # omit entirely if no epic; integer execution order within the epic
assigned: <username>      # omit entirely if not provided
prerequisites: [TASK-NNN, TASK-NNN]   # omit entirely if none
---

## Description

<expanded description with context and purpose>.

## Acceptance Criteria

- [ ] <specific criterion 1>
- [ ] <specific criterion 2>
- [ ] <specific criterion 3>

## Test Plan

<See rules below — fill in the appropriate section(s)>

## Prerequisites

<!-- Omit this section entirely if the frontmatter prerequisites field is absent -->

- **TASK-NNN** — <one line: what this task delivers that the current task needs>
- **TASK-NNN** — <one line: what this task delivers that the current task needs>

## Sizing rationale

<!-- Include this section ONLY when effort is L or XL AND the user kept the
     task whole (or skipped the split nudge per step 4). Omit otherwise. -->

<one line explaining why this task is intentionally sized L/XL and not split>

## Notes

<dependencies, risks, considerations, and other context>
```

   Set `opened` to today's date in `YYYY-MM-DD` format.

   **Effort labels** — `--effort` accepts only the canonical six t-shirt sizes:

   | Flag value | Frontmatter label |
   |---|---|
   | `XS`  | `XS (<30m)` |
   | `S`   | `Small (<2h)` |
   | `M`   | `Medium (2-8h)` |
   | `L`   | `Large (8-24h)` |
   | `XL`  | `Extra Large (24-40h)` |
   | `XXL` | `XXL (>40h)` |

   Never write any other string into `effort:`. Legacy labels like
   `Trivial (<30m)`, `Small (1-2h)`, `Small (1-3h)`, `Small (2-4h)`, or
   `Large (>8h)` may still appear in already-closed tasks — readers tolerate
   them on input, but new files use only the canonical six.

   Complexity values (`--complexity`): `Junior`, `Medium`, `Senior`.
   `human-in-loop` values: `No`, `Clarification`, `Support`, `Main`.
   `epic`: free-form epic name. Omit the field entirely if the task does not belong to an
   epic. When provided, also set `order` to the integer execution sequence within the epic
   (1 = first). Tasks in the same epic are displayed together in OVERVIEW.md, sorted by `order`.

   **Deriving `order` when `--order` is not supplied:** scan **every** task file
   across `open/`, `active/`, and `closed/` for tasks belonging to this epic, take
   the maximum `order` value, and add 1. Closed tasks must be included — orders
   are not recycled when a task closes; they remain part of the epic's historical
   execution sequence. Never derive `order` from "the most recently created task"
   or "the highest open order" — both will collide with closed tasks. If the epic
   has no tasks yet, use `order: 1`.

   Concrete derivation command (run from repo root):

   ```bash
   grep -l "^epic: <EpicName>$" docs/developers/tasks/*/*.md \
     | xargs grep -h "^order:" \
     | awk '{print $2}' | sort -n | tail -1
   ```

   Then `next_order = that_value + 1`.

   **Collision check when `--order <N>` is supplied:** run the same scan and verify
   N does not already appear among existing orders for this epic. If it does, stop
   and report the collision (which task already holds that order) instead of writing
   a duplicate. Do not attempt to "shift" or renumber other tasks to make room.
   `assigned`: optional username of the task owner. Omit the field entirely if not provided.
   `prerequisites`: optional list of TASK-IDs that must be complete before this task starts.
   Omit the field entirely if the task has no prerequisites. When present, also add a
   `## Prerequisites` section in the body explaining what each predecessor delivers.
   If the user does not supply required values, infer them from context or ask. Do not leave
   these as `?` — they must be set so the overview table is meaningful.

<!-- markdownlint-disable MD029 -->
7. Run `python scripts/housekeep.py --apply` to regenerate `OVERVIEW.md`, `EPICS.md`,
   and `KANBAN.md`.
8. **Documentation check** — after writing the task file, assess whether the work
   described would require updating user-facing or developer documentation:

   - **User-facing docs** (`docs/builders/`, `docs/musicians/`, `README.md`): new
     features, changed behaviour, new config keys, new CLI commands, new action types.
   - **Developer docs** (`docs/developers/ARCHITECTURE.md`, `TESTING.md`, etc.):
     new classes, changed interfaces, new test patterns, changed data-flow.
   - **Inline tool docs** (`docs/simulator/`, `docs/tools/config-builder/`): new
     action types or config keys that the simulator or builder need to support.

   Apply this rule:

   | Situation | Action |
   |-----------|--------|
   | The task explicitly says to update docs, or the scope obviously requires it (e.g. "add new action type") | Add a **Documentation** section to the task body listing which files need updating and what to add/change. |
   | The task description is silent on docs and the impact is unclear | Ask the user: *"Should this task include updating [specific doc files]? Or is that a separate follow-up task?"* — then wait for the answer before writing the file. |
   | The task is purely internal (tests, refactors, CI, infra) with no user-visible change | No documentation step needed — omit the section. |

   When a Documentation section is warranted, add it to the task body after the Test Plan:

   ```markdown
   ## Documentation

   - `docs/builders/KEY_REFERENCE.md` — add a section for the new action type with a JSON example
   - `docs/developers/ARCHITECTURE.md` — update the Action class hierarchy diagram
   ```

9. Report the new task ID and file path.
<!-- markdownlint-enable MD029 -->

Do not commit.

---

## Test Plan rules

Every task **must** include a Test Plan section. Use the decision table below to fill it in.

### Decision table

| The task changes… | Test layer |
|---|---|
| Pure logic in `lib/PedalLogic/` with no Arduino/GPIO calls | Host tests only (`test/unit/`) |
| GPIO, ISRs, interrupts, pin state, hardware timing | On-device tests (`test/test_*_esp32/` or `test/test_*_nrf52840/`) |
| Both layers | Both |
| Only docs, config, scripts, or CI — no C++ logic | "No automated tests required — change is non-functional" |

### Host-only example

```markdown
## Test Plan

**Host tests** (`make test-host`):
- Add `test/unit/test_<feature>.cpp`
- Register in `test/CMakeLists.txt`
- Cover: <list key scenarios>
```

### On-device example

```markdown
## Test Plan

**On-device tests** (`make test-esp32-button`):
- Extend `test/test_buttons_esp32/test_main.cpp`
- Cover: <list key scenarios>
- Requires: ESP32 connected via USB
```

### Both layers example

```markdown
## Test Plan

**Host tests** (`make test-host`):
- Add `test/unit/test_<feature>.cpp`
- Cover: <logic scenarios>

**On-device tests** (`make test-esp32-button`):
- Extend `test/test_buttons_esp32/test_main.cpp`
- Cover: <hardware scenarios>
- Requires: ESP32 connected via USB
```
