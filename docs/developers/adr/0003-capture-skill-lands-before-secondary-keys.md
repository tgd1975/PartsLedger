---
id: ADR-0003
title: /capture slash-skill ships in EPIC-005 Phase 1 without waiting for TASK-037 secondary-key dispatch
status: Accepted
date: 2026-05-14
dossier-section: docs/developers/ideas/archived/idea-006-usb-camera-capture.md#stage-7--thin-capture-slash-skill
---

## Context

EPIC-005's TASK-038 is the thin `/capture` slash-skill subprocess wrapper.
Per the original task body, TASK-038 depends on TASK-037 (Phase 3 — secondary
key dispatch for `R` / `X` / `U`) "so the in-session UX is end-to-end useful,
not a stub." TASK-037 in turn depends on TASK-036, which depends on TASK-043
in EPIC-006 — a chain of five unstarted tasks across two epics.

The EPIC-005 phasing comment, however, explicitly places TASK-038 in **Phase 4**
and Phase 1 ends at TASK-035 (CLI). The user, scoping this run, asked for
Phase 1 + TASK-038 (skill-only), explicitly accepting that the in-session UX
will not yet have `R` / `X` / `U` because EPIC-006's pipeline does not exist.

## Decision

Ship TASK-038 in this run on top of the TASK-035 CLI. The slash-skill is a
pure subprocess wrapper: it spawns `python -m partsledger.capture`, streams
stdout/stderr to the Claude session, and surfaces the subprocess exit code.
The wrapper does not depend on the secondary-key dispatch existing — it only
requires the CLI itself to be stable.

When TASK-037 eventually lands, no change to the slash-skill or the wrapper
script is needed: the new key dispatchers live entirely inside the
`Viewfinder` event loop that the CLI already drives.

## Consequences

**Easier:**

- The maker can invoke `/capture` from inside a Claude Code session today
  to take stills + identify-via-`/inventory-add` manually, even before the
  recognition pipeline exists. Useful as a fixture-generation surface during
  EPIC-006 development.
- TASK-038 closes in the same epic-run as the rest of Phase 1, avoiding a
  separate per-task /epic-run invocation later.

**Harder:**

- The TASK-037 prerequisite annotation on TASK-038 is technically violated.
  Mitigation: the prerequisite captures a *recommendation* about UX
  completeness, not a code-level dependency. TASK-038 is a 6-line wrapper
  script + SKILL.md + one `.vibe/config.toml` edit; nothing about it requires
  TASK-037 code to exist.
- If TASK-038 needs to grow logic later (e.g. message-handler integration
  with Claude session state), the no-state-of-its-own contract from
  IDEA-006 Stage 7 must hold.

## See also

- [TASK-038 — /capture thin slash-skill subprocess wrapper](../tasks/active/task-038-capture-slash-skill.md)
- [TASK-037 — Secondary key dispatch (deferred until EPIC-006 Stage 5)](../tasks/open/task-037-secondary-key-dispatch.md)
- [IDEA-006 § Stage 7](../ideas/archived/idea-006-usb-camera-capture.md#stage-7--thin-capture-slash-skill)
