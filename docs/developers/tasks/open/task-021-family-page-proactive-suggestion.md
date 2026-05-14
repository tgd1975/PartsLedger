---
id: TASK-021
title: Family-page proactive suggestion at add-time + page-gen-time
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Medium
human-in-loop: Clarification
epic: skill-path-today
order: 3
---

## Description

Land IDEA-005 Stage 2. Detect MPN-stem siblings at add-time and
page-generation time so the maker doesn't accidentally create two
unconnected pages (or two unmerged rows) for what's really the same
chip. Advisory only — same maker-discretion principle as IDEA-004's
splitting suggestion: the suggestion fires, the maker decides.

**Touchpoints:**

- **`/inventory-add <new-mpn> <qty>`** — after locating the section,
  scan existing rows. If any shares an MPN base with the new entry
  (e.g. adding `LM358P` while `LM358N` is already in inventory), offer
  the family-page pattern: mark both rows' Notes with the *"Shares
  page with …"* breadcrumb per IDEA-004 § Family pages, and generate
  the family page now or defer.
- **`/inventory-page <mpn>`** — before generating a fresh page, check
  whether a stem-sibling already has one. If so, propose *"join the
  existing `<sibling>.md` as a family page"* rather than creating a
  new file.

**Heuristic** (per IDEA-005 § Stage 2). Stem match has two conjunctive
parts:

1. **Length gate** — common prefix is at least 4 alphanumeric
   characters. Drops `LM358` vs `LM2904` (prefix `LM`, 2 chars) and
   `LM358N` vs `LM386N` (prefix `LM3`, 3 chars).
2. **Suffix-only divergence** — once the common prefix is stripped,
   the remainders are pure package/grade suffixes (single letter,
   optional digit, optional trailing letter), not further alphanumeric
   stems. Drops `LM358` vs `LM3580` (remainder `0` is part of a
   different stem, not a suffix).

Both must hold. The IDEA-004 family-boundary worked examples are the
ground truth — if the regex disagrees with them, the examples win.
Conservative beats generous.

**Batched-add case.** `/inventory-add LM358P 2, LM358N 3` against an
empty inventory: first pair commits silently, second pair fires the
suggestion against the just-committed first pair. The scan runs against
**post-commit** state after each pair. Declining the second pair's
suggestion leaves both rows present without cross-links. No
retroactive prompt after the batch completes.

`CHANGELOG.md` carries one bullet under `[Unreleased] / ### Tooling`.

## Acceptance Criteria

- [ ] Adding `LM358P` while `LM358N` is already a row fires the
      suggestion; accepting it updates both Notes cells with the
      *"Shares page with …"* breadcrumb and produces a single family
      page.
- [ ] Adding `LM2904` while `LM358` exists does **not** fire the
      suggestion (IDEA-004's family-boundary ❌ example).
- [ ] Adding `LM358N` while `LM386N` exists does **not** fire either
      (common prefix `LM3` is below the 4-character threshold).
- [ ] Batched `/inventory-add LM358P 2, LM358N 3` against an empty
      inventory: first pair commits silently, second pair fires the
      suggestion against the just-committed first pair.
- [ ] A maker who declines and proceeds gets a clean fresh row / fresh
      page — no artefacts.
- [ ] `/inventory-page <mpn>` proposes the family-join when a
      stem-sibling page already exists.
- [ ] `CHANGELOG.md` carries the tooling bullet under `[Unreleased] /
      ### Tooling`.

## Test Plan

**Host tests (pytest):** family-boundary suggestion fires for ✅
examples in IDEA-004, stays silent for ❌ examples. Includes the
batched-add ordering case.
