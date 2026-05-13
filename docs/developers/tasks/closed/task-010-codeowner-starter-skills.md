---
id: TASK-010
title: Author starter co-* skills capturing PartsLedger invariants
status: closed
closed: 2026-05-13
opened: 2026-05-12
effort: Small
effort_actual: Small (<2h)
complexity: Senior
human-in-loop: Clarification
epic: align-with-circuitsmith
order: 10
prerequisites: [TASK-009]
---

## Description

Author one or two starter `co-<name>` skills that capture
PartsLedger-specific invariants surfaced at edit time by the
codeowner hook from TASK-009. These are **PartsLedger-shaped
content**, not a port — TASK-010 is the design counterpart to
TASK-009's mechanism.

Candidate skills (decide in the Clarification pause):

1. **`co-inventory-schema`** — invariants for
   `inventory/parts/<part>.md`:
   - Frontmatter fields the skill expects (`part`, `manufacturer`,
     `package`, `pins`, `datasheet`, `octopart`, etc. — defined in
     IDEA-001 and IDEA-027).
   - Pin-aliasing rules (e.g. `VP` → `IO36` for ESP32-like
     components).
   - Required vs optional fields per part category (MCU vs IC vs
     passive).
   - **Forbidden edges:** never write to
     `inventory/.embeddings/vectors.sqlite` without a matching
     MD update.
2. **`co-inventory-master-index`** — invariants for
   `inventory/INVENTORY.md` (the master index):
   - Auto-generated nature (which script regenerates it once that
     code lands).
   - Schema for the per-part row (Part, Qty, Description, Datasheet,
     Octopart, Notes).
   - Category sections and when to add a new one.

Each `co-*` skill follows CircuitSmith's format:

```markdown
---
name: co-<name>
description: <one-line invariant summary surfaced when matching paths are edited>
---

# Invariants (checklist, not prose)

- [ ] Invariant 1 — terse, specific.
- [ ] Invariant 2 …

## Authority

See [`docs/developers/ideas/open/idea-001-partsledger-concept.md §<section>`](…)
or the IDEA-027 vocabulary in the AwesomeStudioPedal repo.

## Downstream consumers

A breaking change here affects:

- `path/to/consumer-a.py` (once it lands)
- `inventory-add` skill, `inventory-page` skill
- CircuitSmith's `--prefer-inventory` reader
```

Each new skill is added to `enabled_skills` in `.vibe/config.toml`
per the project skill-registration rule (CS CLAUDE.md `## Skill
registration`).

## Acceptance Criteria

- [x] At least one `co-<name>/SKILL.md` exists under
      `.claude/skills/` — both `co-inventory-schema` and
      `co-inventory-master-index` landed.
- [x] Each new skill is registered in `.vibe/config.toml`'s
      `enabled_skills` list.
- [x] Each new skill has a corresponding entry in
      `.claude/codeowners.yaml` (the registry pattern → skill
      binding).
- [x] Editing a file matched by an entry triggers the codeowner
      hook and surfaces the skill body (verified via synthetic
      Edit payload).
- [x] `markdownlint-cli2` passes on the SKILL.md files.

## Test Plan

1. Touch `inventory/parts/tl082.md` (an existing PartsLedger MD) and
      run an Edit tool call on it — confirm the hook surfaces the
      `co-inventory-schema` body (or whichever skill the registry
      binds).
2. Read the surfaced body and check that every invariant listed is
      something the user actually cares about preserving (the
      Clarification pause exists for this — if the invariants feel
      off, iterate before closing).

## Notes

`human-in-loop: Clarification` because the invariant set is a
PartsLedger-shaped design decision. The list above is a starting
point — the user may add or remove invariants in the Clarification
pause. Authoring 1 skill is acceptable; 2 is the upper bound for
this initial task.
