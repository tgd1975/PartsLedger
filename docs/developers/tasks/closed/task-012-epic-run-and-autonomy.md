---
id: TASK-012
title: Port /epic-run skill and AUTONOMY.md, sweep HIL frontmatter on open tasks
status: closed
closed: 2026-05-13
opened: 2026-05-12
effort: Medium
effort_actual: Small (<2h)
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 12
prerequisites: [TASK-006]
---

## Description

Port CircuitSmith's autonomous-implementation mode. Three artefacts
plus one data sweep:

1. **`docs/developers/AUTONOMY.md`** — port verbatim.
   Substitutions: link rewrites to PartsLedger paths (none of the
   AUTONOMY content is circuit-specific). Confirms the four HIL
   levels (`No`, `Clarification`, `Support`, `Main`), the
   ADR-on-ambiguity rule, the epic-driver loop, the review-packet
   format, the no-published-effect-without-approval policy.
2. **`.claude/skills/epic-run/SKILL.md`** — port verbatim. The
   skill description includes `/check-branch`, `/ts-task-active`,
   `/commit`, `/housekeep`, `/ts-task-done`, plus AUTONOMY.md's
   review-packet template.
3. **`.vibe/config.toml`** — add `epic-run` to `enabled_skills`
   (alongside any `co-*` skills registered in TASK-010).
4. **Open-task HIL frontmatter sweep** — every open task file under
   `docs/developers/tasks/open/` and `active/` gets a
   `human-in-loop:` field if missing. Default to `No` unless the
   task is clearly Clarification (a one-shot decision in the body),
   Support (a stop-line for collaborative work), or Main (a remote-
   effect action). All EPIC-001 tasks already carry HIL in their
   frontmatter — this sweep covers any other open tasks the
   PartsLedger task system has at sweep time.

## Acceptance Criteria

- [x] `docs/developers/AUTONOMY.md` exists; all internal links
      resolve; `markdownlint-cli2` passes.
- [x] `.claude/skills/epic-run/SKILL.md` exists.
- [x] `epic-run` is in `.vibe/config.toml`'s `enabled_skills`.
- [x] Every open task file in `docs/developers/tasks/{open,active}/`
      has a `human-in-loop:` field set to one of `No`,
      `Clarification`, `Support`, or `Main` (sweep was a no-op —
      all EPIC-001 tasks already carried HIL).
- [x] The `## Autonomy` section in `CLAUDE.md` (from TASK-011)
      points at `AUTONOMY.md` and the link resolves.

## Test Plan

1. `/epic-run EPIC-001` from a clean working tree on the epic
      branch — the loop picks up the next task with all
      prerequisites met (would be TASK-013 by this point, the last
      open task) and either drives it or hands off if HIL-gated.
      (Actual `/epic-run` execution is not part of TASK-012's DoD;
      the skill just has to exist and be invocable.)
2. `python -c "import yaml, pathlib; [yaml.safe_load(p.read_text().split('---')[1])['human-in-loop'] for p in pathlib.Path('docs/developers/tasks').rglob('task-*.md')]"`
      — exits 0 (every open task has the field).

## Notes

The HIL sweep is mechanical for tasks lacking the field — default
`No` and let the user fix outliers. For tasks where the body
explicitly says "needs user decision" or "stop and ask", set
`Clarification`. For tasks involving `gh api -X PUT` or other
remote effects, set `Main`.
