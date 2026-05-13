---
name: commit
description: Commit user-named files atomically via scripts/commit-pathspec.sh (which wraps `git commit -m "..." -- <files>` and writes the provenance token the pre-commit hook validates). Runs registered auto-fixers (markdownlint --fix, etc.) scoped to the pathspec entries first so trivially-fixable lint issues don't bounce off the hook. Applies the CLAUDE.md "Pre-commit hook failures on unrelated changes" protocol when the hook still fails. Never adds --no-verify silently — explicit user approval is required.
---

# commit

Invoked as `/commit "<message>" <file> [<file> …]`. The skill exists to
make the project's commit protocol — encoded in CLAUDE.md under
"Parallel sessions" and "Pre-commit hook failures on unrelated changes"
— consistent and auditable instead of relying on prose-only guidance.

## Atomicity property — why pathspec form is mandatory

This skill **always** commits via git's pathspec form:

```bash
git commit -m "..." -- <file> [<file> …]
```

It **never** uses the two-step `git add <files> && git commit -m "..."`.
The reason is parallel-session safety:

- Pathspec form builds a **temporary index** containing only the named
  files, runs the pre-commit hook against that temporary index, and
  only updates the real index if the commit succeeds. Hook failure
  leaves the real index untouched.
- Two-step form mutates the real index *before* the hook runs. If the
  hook fails, the named files stay staged in the shared index — and
  any foreign files staged by a parallel session are now mixed in
  with them. The next commit attempt (yours or theirs) starts dirty.

In a repo where multiple Claude Code sessions run concurrently, this
is the difference between "your hook failure is your problem" and
"your hook failure clobbers another session's staged work". Pathspec
keeps blast radius scoped to the single commit attempt.

## Steps

> **These steps describe what *the skill body* (i.e. the agent acting
> *as* the skill, after `/commit` is invoked) does — not preconditions
> the caller must satisfy beforehand.** Callers pass `/commit "<msg>"
> <files…>` with no manual `git add`, no index inspection, no working-
> tree clean-up. Anything mentioned below — including staging untracked
> entries — happens *inside* this skill's flow, not in front of it.

1. **Validate input.** If the user passed no files, stop and ask which
   files belong to this commit. Never sweep with `-A` / `.` / `-u`.
   Per the project's "Parallel sessions — commit only your own work"
   rule, the file list must be explicit.

2. **Run auto-fixers scoped to the pathspec.** Before involving git
   at all, group the pathspec entries by file class and, for each
   class with a registered fixer, run the fixer against just those
   files. Fixers are cheap; pre-commit hook failures are not (parse
   stderr, diagnose, retry).

   **Scope: pathspec only.** Never invoke a fixer on the whole tree,
   even when the hook itself lints the whole tree (the markdown gate
   uses `**/*.md`). Editing files outside the pathspec violates the
   "commit only your own work" rule and would clobber parallel
   sessions' working trees.

   **No expensive operations.** Only lint / format auto-fixes that
   complete in well under a second per file. No compilation, no
   type-checking, no full test runs — those belong in the hook or CI,
   not in the commit flow.

   **Fixer registry.** The table below IS the contract — extend it
   when the project adopts new tooling, and keep it in sync with
   [`scripts/pre-commit`](../../../scripts/pre-commit).

   | File class | Fixer (run only on pathspec entries in this class) |
   | ---------- | --------------------------------------------------- |
   | `*.md`     | `markdownlint-cli2 --fix <files>`                   |
   | `*.py`     | `ruff check --fix <files>`                          |

   Classes not in the table (`*.sh`, `*.yml`, `*.json`, …) are passed
   through untouched until a follow-up task adopts tooling for them.
   The Python row was added in TASK-061; ruff was chosen over black /
   black+isort+flake8 / autopep8 because it subsumes lint + import
   sort + most of black's formatting in a single fast binary (see
   commit message + task body for rationale).

   **Missing-tool behaviour.** If the pathspec contains files in a
   class that *is* in the registry, but the fixer binary is not on
   `$PATH`, stop and ask the user to install it before proceeding.
   The pre-commit hook enforces the same tooling as a gate (e.g.
   `markdownlint-cli2` is mandatory there too), so a missing fixer
   here would just produce a slower failure at hook time. Per
   CLAUDE.md's "Missing executables" rule: ask once, don't spiral
   through fallbacks.

   After fixers run, the pathspec files' working-tree contents may
   have changed. Pathspec form (step 4) reads the working tree at
   commit time, so the fixed content is what gets committed — no
   extra `git add` is needed for already-tracked files. For untracked
   files, the fixer runs before step 3's `git add`, so the staged
   content is post-fix.

3. **Untracked pathspec entries — handled by the wrapper, never by
   you.** Pathspec form requires every named file to be known to git.
   When the pathspec contains an untracked file, the wrapper takes
   care of it via `--stage-untracked` (passed automatically in step
   4 below). The wrapper detects untracked entries, stages them, and
   commits — all in one process.

   **You must never type `git add`.** Not before invoking the wrapper,
   not after a hook failure, not "just this once because the file is
   untracked." The project enforces this with a `permissions.deny`
   entry on `Bash(git add:*)` in `.claude/settings.json`. If you try,
   the harness blocks the tool call.

   The original design (TASK-329) required the skill to `git add`
   untracked entries before invoking the wrapper, because always-on
   in-wrapper staging masked parallel-session races. The current
   design is opt-in: callers that want strict fail-fast behaviour
   call the wrapper without `--stage-untracked`; the /commit skill
   passes the flag because its workflow already brackets the staging
   inside a single agent action. The race window with the flag is
   one wrapper process; without it, the window spans skill-add +
   wrapper-commit (two processes) — so in-wrapper staging is
   strictly tighter than skill-side staging.

   **Renames and deletions — name BOTH (or the deleted) path.** These
   rules are caller-side, not staging actions:

   - **Rename via `git mv A B`**: include *both* `A` and `B` in the
     pathspec list. Naming only `B` makes git's temp-index build see
     `A` as still-present-in-HEAD and skip the deletion side, so the
     commit records an addition of `B` while leaving `A` orphaned in
     the working tree as a `D` entry. This is the bug TASK-347 fixed
     end-to-end; the wrapper now accepts rename sources, but it can
     only commit the deletion side if you name it.
   - **Plain deletion (file removed from disk, with or without
     `git rm`)**: include the deleted path in the pathspec. The
     wrapper accepts paths that are in HEAD even when missing from
     both disk and index, so a `rm A` followed by
     `/commit "..." A` commits the deletion.
   - **Pure addition** (untracked → committed): just name the path.
     The wrapper's `--stage-untracked` (passed in step 4) does the
     staging.

4. **Invoke the wrapper script** with the commit message. Always pass
   `--stage-untracked` — it's a no-op when every pathspec entry is
   already tracked, and it's what handles new files without you ever
   typing `git add`. Use a heredoc for multi-line messages so newlines
   survive shell quoting. Do **not** append a `Co-Authored-By:`
   trailer or any other "generated with" attribution — the user has
   explicitly rejected those:

   ```bash
   scripts/commit-pathspec.sh --stage-untracked "$(cat <<'EOF'
   <commit message>
   EOF
   )" <file> [<file> …]
   ```

   The wrapper handles two things you must not duplicate:

   1. Writing the provenance token at `.git/pl-commit-token` that the
      pre-commit hook validates.
   2. Running `git commit -m "..." -- <files>` in pathspec form.

   Do **not** call `git commit` directly — the pre-commit hook will
   reject it for missing the provenance token.

5. **On hook success** — report the new commit's short hash + subject
   (one line). Done.

6. **On hook failure** — do **not** retry, do **not** add `--no-verify`
   silently. Pathspec form leaves the real index untouched, so any
   foreign staged files from parallel sessions are still where they
   were before; do not "clean up" `git status` between failure and
   retry. Run the three CLAUDE.md checks and present a structured
   message to the user before proposing a bypass:

   - **Pathspec files only** — are *all* files in the pathspec list
     unrelated to the hook failure? (e.g. only `.md` files in this
     commit, but C++ tests fail.) Identify the failing check from
     the hook's stderr; map it to a file class (`*.cpp`/`*.h` for
     clang-format / unit tests, `*.md` for markdownlint, etc.).
     Compare to the pathspec list — *not* to `git status`, since the
     real index is not touched in pathspec mode.
   - **Pre-existing breakage** — is the failing check broken on `main`
     or in the working tree already, not caused by this commit? Run
     the failing check against `HEAD` (or `main` if quick) to confirm.
   - **No silent regression** — would bypassing hide a real regression
     introduced by the pathspec changes? If the pathspec files
     plausibly could affect the failing check (even indirectly via
     includes / imports / generated code), the answer is "yes, fix
     it" — do not bypass.

7. **If all three checks pass**, present the standard message verbatim:

   > The pre-commit hook failed, but the failure is in `<file/check>`
   > which is unrelated to the files in this commit
   > (`<list pathspec files>`). This appears to be a pre-existing
   > issue. It may be OK to bypass the hook for this commit with
   > `--no-verify`. Do you want me to proceed with `--no-verify`, or
   > fix the hook failure first?

   Wait for explicit user approval. On approval, retry via the
   wrapper with `--no-verify`:

   ```bash
   scripts/commit-pathspec.sh --no-verify --stage-untracked "<message>" <file> [<file> …]
   ```

   On refusal, stop — the user will fix the hook failure first.

8. **If any of the three checks fails**, do **not** offer `--no-verify`.
   Report which check failed, surface the relevant hook output, and
   stop — the user diagnoses or fixes.

## Caller anti-patterns

These are the failure modes that motivated the actor-clarification at
the top of `## Steps`. Recognise and avoid them — every one of them
duplicates work the skill is about to do.

- **Typing `git add` anywhere — under any circumstance.** Not "to
  help". Not "the file is untracked." Not "the hook failed, let me
  clean up." The wrapper's `--stage-untracked` flag is the *only*
  mechanism that stages files in this project, and the harness
  enforces this with a `permissions.deny` on `Bash(git add:*)`. If
  you find yourself reaching for `git add`, you are in the wrong
  branch of the flow — re-read step 3.
- **Inspecting / unstaging the index before invoking.** The wrapper
  uses pathspec form, which builds a temp index from HEAD + the named
  files; it does not read the real index for the commit content. The
  real index's pre-state is irrelevant to what gets committed.
- **Trying to "clean up" the working tree after a hook failure.**
  Pathspec hook failures leave the real index untouched on purpose —
  that's the parallel-session safety property. There is nothing to
  clean up. Re-invoke `/commit` with the same arguments after fixing
  the underlying cause, or follow step 7's three-check `--no-verify`
  flow.

## Local success ≠ mergeability — the CI gate

A successful `/commit` only means the local pre-commit hook accepted
the change. The PR still has to clear the CI merge gate on `main`
before the **Merge pull request** button on GitHub is enabled. The
gate runs every required workflow on a real GitHub runner and
catches things a fast local hook cannot — flaky integration tests,
cross-platform formatting drift, generated-file staleness.

Bypassing the local hook with `--no-verify` per step 7's three-check
protocol does **not** bypass the gate. The PR still fails CI.

The required-checks list and the recipe for adding a new gate live in
[`docs/developers/DEVELOPMENT_SETUP.md`](../../../docs/developers/DEVELOPMENT_SETUP.md#ci-merge-gate-branch-protection-on-main).

## When NOT to use

- **Partial-hunk commits** (committing some hunks of a file but not
  others). Pathspec form has no equivalent of `git add -p`; the whole
  file is committed. Partial-hunk policy is decided in TASK-327. For
  now, split the file or commit the whole change.
- Multi-step commits where each commit needs human review of the
  message and contents (use `git commit` interactively).
- Amending an existing commit. The CLAUDE.md "Git Safety Protocol"
  (system-prompt level) prefers new commits over amends.
- Committing on `main`. `/check-branch` should fire first; this skill
  does not bypass that.

## Skill registration

Registered in [.vibe/config.toml](../../../.vibe/config.toml)'s
`enabled_skills` list per the project's CLAUDE.md skill-registration
rule.
