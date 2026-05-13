# Code-owner skills

This project surfaces architectural invariants **at edit time** via
small Claude Code skills bound to file patterns. When a file matching
a registered pattern is about to be edited or written, a
`PreToolUse` hook reads the bound skill's `SKILL.md` body and prints
it as a reminder. The hook is purely informational — it never blocks
the edit; it only ensures the invariants are in front of the editor
before the change lands.

This is the edit-time analogue of GitHub's `CODEOWNERS` — fitted to
the current solo, Claude-driven workflow. When a second contributor
joins, layer literal GitHub CODEOWNERS on top: the two compose
cleanly (skill at write-time, CODEOWNERS at PR-time).

## Moving parts

| Component | Path | Role |
|---|---|---|
| Registry | [`.claude/codeowners.yaml`](../../.claude/codeowners.yaml) | Binds file globs to skill names. |
| Hook | [`scripts/codeowner_hook.py`](../../scripts/codeowner_hook.py) | Reads the PreToolUse payload, matches, prints the skill body. |
| Hook registration | [`.claude/settings.json`](../../.claude/settings.json) | `hooks.PreToolUse` with `matcher: "Edit\|Write"`. |
| Code-owner skills | `.claude/skills/co-<name>/SKILL.md` | One per high-blast-radius module. Authored in TASK-010. |

## How to add a code-owner skill

1. **Identify the file.** Pick a single load-bearing file (or a
   tightly coupled set — `inventory/parts/*.md`). Anything an
   accidental edit could quietly break downstream is a candidate. The
   initial set in TASK-010: `co-inventory-schema` (binds
   `inventory/parts/*.md`) and `co-inventory-master-index` (binds
   `inventory/INVENTORY.md`).
2. **Author the skill.** Create
   `.claude/skills/co-<name>/SKILL.md` with:

   ```markdown
   ---
   name: co-<name>
   description: one-line summary surfaced when the editor matches this pattern
   ---

   # Invariants (checklist, not prose)

   - [ ] Invariant 1 — terse, specific.
   - [ ] Invariant 2 …

   ## Authority

   See [`docs/developers/ideas/open/idea-NNN-<dossier>.md §<section>`](…)
   or the IDEA-027 vocabulary in the AwesomeStudioPedal repo.

   ## Downstream consumers

   A breaking change here affects:

   - `path/to/consumer-a.py`
   - …
   ```

3. **Register the skill.** Add it to `enabled_skills` in
   [`.vibe/config.toml`](../../.vibe/config.toml) per the project's
   `CLAUDE.md` skill-registration rule.
4. **Bind it.** Add an entry to `.claude/codeowners.yaml`:

   ```yaml
   entries:
     - pattern: inventory/parts/*.md
       skill: co-<name>
   ```

5. **Commit.** The new skill, registry entry, and `.vibe` registration
   land in one commit through `/commit`.

## Glob syntax

The registry uses a gitignore-flavoured subset, implemented in
`_glob_to_regex` in the hook:

- `**` matches any string including `/`.
- `*` matches one path segment (anything except `/`).
- `?` matches one character (anything except `/`).
- Everything else is literal.

Anchoring is implicit (patterns match the full repo-relative path).
Directory-only patterns (`foo/`) and negation (`!`) are not
supported — keep patterns simple.

## When the hook fires (and when it doesn't)

The hook fires only for **Claude-driven** `Edit` / `Write` tool
invocations. A human editing the same file directly in their editor
bypasses it entirely. That's fine for now (solo workflow); if a
second contributor joins, add GitHub CODEOWNERS at the PR layer for
the complementary case.

The hook is **non-blocking**: it always exits 0 on a normal match.
The one exception is a malformed `.claude/codeowners.yaml`, which
exits non-zero so the contributor notices the typo. Blocking
guardrails live in the contract tests and the lints — not here.

## Related

- TASK-009 — this mechanism.
- TASK-010 — the first PartsLedger code-owner skills
  (`co-inventory-schema`, `co-inventory-master-index`).
