---
id: TASK-019
title: Hedge-language lint over inventory/parts/*.md + pre-commit hook
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Medium
human-in-loop: No
epic: skill-path-today
order: 1
---

## Description

Land IDEA-005 Stage 1 — a mechanical backstop for the sincere-language
convention. The convention is enforced today by prompt examples inside
`/inventory-add` and `/inventory-page`; prompt-example enforcement
drifts, lint doesn't.

The lint walks `inventory/parts/*.md` and flags absolute-claim phrasing
that should be hedged (`~`, `up to`, `typically`) — e.g. rhetorical
uses of `is the`, `must`, `always`, `never` outside of exempt contexts.

**Scope — parts pages only.** The lint does **not** walk `INVENTORY.md`.
The master index's Notes cells are short, hand-curated, and frequently
quote datasheet language verbatim — a table-cell lint would generate
mostly noise. The convention's real failure mode is long-form prose
drift inside parts pages, which is what the lint is sized for. If the
Notes column ever starts attracting LLM-authored hedge violations in
practice, a narrower row-level lint can be added then.

**Exempt contexts.** Fenced code blocks, ASCII-pinout blocks, quoted
datasheet excerpts. An inline `<!-- lint: ok -->` marker overrides on a
specific line when a phrase is intentional.

Two pieces of work:

1. Lint script under `scripts/` (e.g. `scripts/lint_hedge_language.py`)
   — Python, walks `inventory/parts/*.md`, flags banned literals
   outside exempt contexts.
2. Pre-commit hook integration — add a stanza to `scripts/pre-commit`
   so the lint fires on every commit touching `inventory/parts/*.md`.
   Same gate shape as the existing markdownlint stanza.

`CHANGELOG.md` carries one bullet under `[Unreleased] / ### Tooling`.

## Acceptance Criteria

- [ ] The six existing parts pages pass clean (any failures are real
      finds, not lint false positives).
- [ ] A synthetic *"this is the LM358"* outside a code block fails.
- [ ] *"walls must align"* inside an ASCII-pinout block passes
      (exempt-context works).
- [ ] A synthetic *"is the LM358"* inside an `INVENTORY.md` Notes cell
      passes (scope is parts pages only, by design).
- [ ] `<!-- lint: ok -->` on a line suppresses the diagnostic for that
      line.
- [ ] `scripts/pre-commit` is wired to fire the lint on every commit
      touching `inventory/parts/*.md`.
- [ ] `CHANGELOG.md` carries the tooling bullet under `[Unreleased] /
      ### Tooling`.

## Test Plan

**Host tests (pytest):** positive + negative fixtures per hedge pattern.
Pre-commit hook activation verified manually on a deliberately-bad page.
