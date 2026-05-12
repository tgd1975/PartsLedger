---
id: TASK-011
title: Rewrite CLAUDE.md to mirror CircuitSmith's verbatim
status: open
opened: 2026-05-12
effort: Small
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 11
prerequisites: [TASK-001, TASK-002, TASK-003, TASK-004, TASK-005]
---

## Description

Full rewrite of PartsLedger's `CLAUDE.md` to mirror CircuitSmith's
verbatim. User directive (per IDEA-002): every rule in CircuitSmith's
`CLAUDE.md` was learned the hard way; no cherry-picking.

**Substitutions** (mechanical):

- `CircuitSmith` → `PartsLedger`
- `circuitsmith` → `partsledger`
- `CS_` → `PL_`
- `cs-commit-token` → `pl-commit-token`
- `cs-commit-bypass.log` → `pl-commit-bypass.log`
- `tgd1975/CircuitSmith` → `tgd1975/PartsLedger`
- `idea-001-circuit-skill` references → `idea-001-partsledger-concept`
- `CS_PARTSLEDGER_PATH` → drop (PartsLedger has no sibling-reference
  env var for itself; mirror with a PartsLedger-meaningful variable
  if any apply, or omit the line).

**PartsLedger-shaped retentions** (same structural slot as
CircuitSmith project-specific content, different content):

1. Keep PartsLedger's `## Inventory is the source of truth` section.
   CircuitSmith has no analogue because it has no inventory; this is
   PartsLedger's domain rule and must stay.
2. Keep PartsLedger's more-detailed `## Missing executables` body
   (`torch`, `cv2`, `sqlite_vec`, optional PaddleOCR/Tesseract,
   `/check-tool`). PartsLedger's expanded list is accurate for its
   heavyweight deps. **Swap `pip` → `uv pip`** in the fallback
   wording (the project uses uv from TASK-002 onwards).

**Drop entirely:**

- PartsLedger's existing `## Task-system source-of-truth` section.
  Replace with CircuitSmith's `## Task-system installation` section
  verbatim — PartsLedger is now installed-copy-no-sync per TASK-001.

**Add (sections currently missing from PartsLedger):**

- `## Bash commands — no diagnostic suffix`
- `## No end-of-turn "continue?" checkpoints`
- `## Branch merges — squash, not fast-forward`
- `## CHANGELOG updates ride with the merge`
- `## Autonomy` (points at `AUTONOMY.md`, which lands in TASK-012)

## Acceptance Criteria

- [ ] `CLAUDE.md` mirrors CircuitSmith's section ordering and content
      apart from the substitutions and the two PartsLedger retentions
      above.
- [ ] `## Inventory is the source of truth` is present and
      unchanged from current PartsLedger.
- [ ] `## Missing executables` keeps PartsLedger's expanded deps
      list with `pip` → `uv pip` swap.
- [ ] `## Task-system source-of-truth` is gone; `## Task-system
      installation` is present per CircuitSmith's wording.
- [ ] No occurrence of `CircuitSmith` / `circuitsmith` / `CS_` /
      `cs-commit` token after the rewrite (run a final grep).
- [ ] The `## Autonomy` section points at
      `docs/developers/AUTONOMY.md`. If TASK-012 has not landed yet,
      the link is forward-dangling; acceptable within the epic
      branch.
- [ ] `markdownlint-cli2` passes.

## Test Plan

1. `diff` the resulting `CLAUDE.md` against CircuitSmith's, allowing
      for the planned retentions and substitutions; everything else
      should be identical.
2. Open a fresh Claude Code session in the repo; confirm the agent
      is operating under the new rules (e.g. it no longer types
      `git add` directly, it does not append diagnostic suffixes to
      Bash invocations).

## Notes

This task lands after TASK-005 because the new `CLAUDE.md` references
the `Bash(git add:*)` deny that lives in `.claude/settings.json`
(TASK-005), the `/commit` skill changes (TASK-004), and the
pre-commit / commit-pathspec wiring (TASK-003). The forward-reference
to `AUTONOMY.md` is intentional — TASK-012 closes that dangling link.
