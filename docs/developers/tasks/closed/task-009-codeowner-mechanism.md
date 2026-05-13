---
id: TASK-009
title: Port codeowner reminder mechanism (hook + registry + PreToolUse)
status: closed
closed: 2026-05-13
opened: 2026-05-12
effort: Small
effort_actual: Small (<2h)
complexity: Junior
human-in-loop: No
epic: align-with-circuitsmith
order: 9
prerequisites: [TASK-005]
---

## Description

Port the **mechanism** (not the contents) of CircuitSmith's
codeowner reminder system. Edits to high-blast-radius files trigger
a `PreToolUse` hook that prints invariants captured in a `co-<name>`
skill. The starter `co-*` skills themselves land in TASK-010.

Six artefacts:

1. **`scripts/codeowner_hook.py`** — port verbatim. Project-
   agnostic: reads a JSON tool-use payload from stdin, matches the
   target file path against `.claude/codeowners.yaml`, and prints
   the bound skill body on a match. Silent on no-match.
2. **`scripts/tests/test_codeowner_hook.py`** — port verbatim
   from `scripts/tests/test_codeowner_hook.py`. The full test suite
   (parser, glob, hook flow). Coexists with PartsLedger's other
   unittest-style tests under `scripts/tests/`.
3. **`.claude/codeowners.yaml`** — registry file. Author with
   PartsLedger-specific entries:
   - `inventory/parts/*.md` → `co-inventory-schema` (the MD
     frontmatter schema; pin-aliasing rules).
   - The embeddings-cache invariant ("never write to
     `inventory/.embeddings/` without a matching MD update") — bound
     to whichever file/script ends up writing the cache once that
     code lands.

   At authoring time the registry can list entries for skills that do
   not yet exist (the hook prints a stderr warning, never blocks).
   TASK-010 authors the skill bodies.
4. **`docs/developers/CODE_OWNERS.md`** — port verbatim.
   Substitutions: replace the "initial three skills" example list
   (CircuitSmith's `co-netgraph`, `co-schema`, `co-erc-engine`) with
   PartsLedger's planned skills (`co-inventory-schema`, …).
5. **`.claude/settings.json`** — add the PreToolUse hook block:

   ```json
   "hooks": {
     "PreToolUse": [
       {
         "matcher": "Edit|Write",
         "hooks": [
           {
             "type": "command",
             "command": "python3 ${CLAUDE_PROJECT_DIR}/scripts/codeowner_hook.py"
           }
         ]
       }
     ]
   }
   ```

   Also add `Bash(python scripts/codeowner_hook.py:*)` to the
   allowlist (so manual invocations don't prompt).
6. **`.vibe/config.toml`** — the `co-*` skills get registered here
   under TASK-010 when their bodies are authored. Nothing to do in
   this task.

## Acceptance Criteria

- [x] `scripts/codeowner_hook.py` exists; `pytest
      scripts/tests/test_codeowner_hook.py` exits 0 with the full
      suite green (26/26).
- [x] `.claude/codeowners.yaml` exists with at least one PartsLedger-
      bound entry; the registry parses (no `ValueError` from the
      hook).
- [x] `.claude/settings.json` has the `PreToolUse` hook block AND
      `Bash(python scripts/codeowner_hook.py:*)` in the allowlist.
- [x] `docs/developers/CODE_OWNERS.md` exists and lints clean.
- [x] An `Edit` tool call on `inventory/parts/<any>.md` triggers the
      hook (verified via tests). Until TASK-010 lands the skill
      bodies, the hook prints a stderr warning that the skill is
      missing.

## Test Plan

1. Run `python3 -m unittest scripts.tests.test_codeowner_hook` —
      all tests green.
2. Echo a synthetic Edit payload through the hook and confirm match
      vs no-match behaviour.

## Notes

The hook is purely informational — it never blocks an edit; the
worst case is a malformed `codeowners.yaml`, which exits non-zero.
Blocking enforcement lives in CI / pre-commit gates, not here.
