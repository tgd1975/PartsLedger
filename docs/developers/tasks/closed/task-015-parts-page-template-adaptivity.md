---
id: TASK-015
title: Teach /inventory-page to produce part-class-appropriate sections
status: closed
closed: 2026-05-14
opened: 2026-05-14
effort: Small (<2h)
effort_actual: Small (<2h)
complexity: Medium
human-in-loop: No
epic: markdown-inventory-schema
order: 2
prerequisites: [TASK-014]
---

## Description

Land IDEA-004 Stage 2. Today `/inventory-page` defaults to a DIP-N ASCII
Pinout regardless of part class, because the six existing pages in the
tree are all 8–16 pin DIP ICs. The template should flex per the worked
examples in IDEA-004 § `parts/<id>.md`:

- **NPN transistor (2N3904, BC547, …).** TO-92 sketch, flat-side-facing
  view with `E B C` reading left to right, plus a 3-row pin table. No
  DIP ASCII, no walls-must-align rule. *Watch out for* flags that TO-92
  pinout varies between manufacturers.
- **2-pin parts (LEDs, signal diodes, electrolytic caps).** Pinout
  collapses to a one-line polarity note. ELI5 usually omitted. Sample
  circuit is one line.
- **Modules (Blue Pill, MAX7219 board).** Pinout is a header diagram
  naming each pin along each edge. *Watch out for* often carries
  level-shifting and power-input gotchas.
- **Connectors (USB-C, barrel jack).** Pinout is a V+ / V- / data note
  with a physical-orientation hint where it matters.

This is a prompt update to `.claude/skills/inventory-page/SKILL.md`, not
new code. The schema-side guard
(`.claude/skills/co-inventory-schema/SKILL.md`) enforces frontmatter and
master-index linkage, not body section names, so it does not need to
change. Add one bullet under `[Unreleased] / ### Tooling` in
`CHANGELOG.md`.

## Acceptance Criteria

- [x] `/inventory-page 2N3904` produces a TO-92 sketch + 3-row pin table,
      not a DIP-N ASCII; *Watch out for* flags the
      manufacturer-varying-pinout gotcha named in IDEA-004's NPN example.
- [x] `/inventory-page 1N4148` collapses Pinout to a one-line polarity
      note and omits ELI5.
- [x] Re-running `/inventory-page` on an existing DIP page (e.g.
      `tl082.md`) produces the same section list and Pinout shape (DIP-N
      ASCII top-view) as the existing file — same-class parts keep the
      same template.
- [x] `CHANGELOG.md` carries the tooling bullet under `[Unreleased] /
      ### Tooling`.

Verification notes:

- The skill body now branches the Pinout / ELI5 / Sample circuit /
  Watch out for sections by part class. The DIP-N IC variant is
  unchanged (existing DIP pages like `tl082.md` re-author with the
  same section list and ASCII shape).
- New variants documented: NPN/PNP transistor (TO-92 sketch + 3-row
  table, manufacturer-varying-pinout flag), 2-pin part (one-line
  polarity note, ELI5 omitted, sample circuit one line), module /
  breakout (header diagram + level-shifting / power-input flags),
  connector (V+ / V- / data note with physical-orientation hint).
- Step 3 of "What to do" now reads "Pick the part class from the
  five above" — replacing the previous "Decide which sections apply"
  language so the class pick is explicit, not implicit.
- The schema-side guard (`co-inventory-schema/SKILL.md`) is
  unchanged, per the task body: it enforces frontmatter and
  master-index linkage, not body section names.
- The `CHANGELOG.md ### Tooling` bullet lands in the CHANGELOG-delta
  phase at the end of the epic-run, bundled with the other TASK-NNN
  bullets — not in this task's per-task commit.

## Test Plan

No automated tests required — manual validation via the three example
`/inventory-page` invocations in Acceptance Criteria.

## Prerequisites

- **TASK-014** — delivers the `Source` column and section-flex schema;
  any new page authored by this skill also writes a row into
  `INVENTORY.md`, and the row needs the new column to exist.
