---
id: TASK-030
title: Write ADR-0001 — library as installable package
status: closed
opened: 2026-05-14
closed: 2026-05-14
effort: Small (<2h)
effort_actual: Small (<2h)
complexity: Senior
human-in-loop: No
epic: project-setup
order: 9
prerequisites: [TASK-022]
---

## Description

Record the src-layout decision as PartsLedger's first ADR so the
rationale survives every future audit and the precedent applies
unambiguously to every Python module landing in EPICs 005-008 and
beyond.

Per IDEA-014 § Open questions — final bullet (ADR or just an idea
conversion): CircuitSmith captured the same decision as
[ADR-0012](../../../../../CircuitSmith/docs/developers/adr/0012-library-as-installable-package.md)
because it was reversing an earlier ADR (ADR-0007, "skill folder *is*
the library"). PartsLedger has no prior ADR to supersede here, so the
move *could* land via task conversion alone — but the cross-cutting
nature (touches every future skill that ships code) justifies writing
the ADR anyway so the rationale survives.

The ADR sets the precedent for every future Python module in
PartsLedger: code lives in `src/partsledger/<module>/`; `scripts/*.py`
and `.claude/skills/*/*.py` files are thin shims (TASK-027 documents
the shim convention; this ADR records the underlying layout
decision).

Structure follows the project ADR template at
[`docs/developers/adr/0000-template.md`](../../adr/0000-template.md).
Cross-reference CircuitSmith's ADR-0012 verbatim — much of the
"why src-layout?" reasoning transfers. The PartsLedger-specific
divergence is that this ADR is **not** superseding anything; it is
the founding decision.

## Acceptance Criteria

- [x] `docs/developers/adr/0001-library-as-installable-package.md`
      exists, follows the ADR template, status `Accepted`.
- [x] The ADR references CircuitSmith's ADR-0012 as the analogue
      decision in the sibling repo.
- [x] The ADR captures the layout decision (src-layout, package name
      `partsledger`), the shim convention (cross-link to CLAUDE.md per
      TASK-027), and the public-surface definition (cross-link to
      RELEASING.md per TASK-023).
- [x] The "Consequences" section names the EPICs that depend on this
      decision (EPICs 005, 006, 007, 008).
- [x] CHANGELOG bullet under `[Unreleased] / ### Policy` records the
      ADR.

## Test Plan

No automated tests required — change is documentation.

## Prerequisites

- **TASK-022** — delivers the layout the ADR records. Writing the
  ADR before the layout exists would record an aspiration, not a
  decision.

## Notes

ADR numbering starts at 0001 (the template at `0000-template.md` is
not a real ADR). If `docs/developers/adr/` does not exist yet, create
it as part of this task and seed it with the template if the template
is not already present.
