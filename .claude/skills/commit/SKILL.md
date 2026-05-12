---
name: commit
description: Commit user-named files atomically via scripts/commit-pathspec.sh (which wraps `git commit -m "..." -- <files>` and writes the provenance token the pre-commit hook validates). Applies the CLAUDE.md "Pre-commit hook failures on unrelated changes" protocol when the hook fails. Never adds --no-verify silently — explicit user approval is required.
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

2. **Stage any untracked pathspec entries** (this skill — *not* the
   caller — performs this step). Pathspec form requires every named
   file to be known to git. For each file in the pathspec that does
   not yet exist in the index, the skill runs:

   ```bash
   git add -- <untracked-file>
   ```

   This is the **only** legitimate `git add` in the commit flow, and
   it lives inside this skill. The wrapper script deliberately rejects
   untracked pathspec entries with exit code 2 rather than auto-adding
   them — auto-adding once existed in the wrapper and was removed in
   TASK-329 because it masked parallel-session races (a foreign-session
   commit could land the same path between the wrapper's untracked
   check and its commit, producing two "added" commits). Failing fast
   forces a refresh, and the skill is the one place that reads stderr,
   re-checks state, and re-tries safely.

   **Caller contract:** never `git add` before invoking this skill,
   even "to be helpful". Pre-staging duplicates this step's work,
   defeats the wrapper's untracked-detection signal, and mixes the
   caller's intent with whatever foreign state the index already held.
   Just pass the files; the skill handles the rest.

   Do **not** `git add` tracked files (modified or otherwise) — those
   are committed directly via the pathspec on the next step. Staging
   them now would defeat the parallel-session safety property of
   pathspec form.

   **Renames and deletions — name BOTH (or the deleted) path.**

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
   - **Pure addition** (untracked → committed): `git add` first as
     described above, then name the path.

   Do **not** `git add` rename sources or deletions — those are *not*
   untracked, and adding them is at best a no-op and at worst stages
   working-tree state you didn't intend.

3. **Invoke the wrapper script** with the message via heredoc. Do **not**
   add any `Co-Authored-By: Claude …` (or any other LLM/agent) trailer
   — the project explicitly rejects such trailers as advertising. Write
   the commit message as if a human authored it.

   ```bash
   scripts/commit-pathspec.sh "$(cat <<'EOF'
   <commit message>
   EOF
   )" <file> [<file> …]
   ```

   The wrapper handles two things you must not duplicate:

   1. Writing the provenance token at `.git/asp-commit-token` that the
      pre-commit hook validates.
   2. Running `git commit -m "..." -- <files>` in pathspec form.

   Do **not** call `git commit` directly — the pre-commit hook will
   reject it for missing the provenance token.

4. **On hook success** — report the new commit's short hash + subject
   (one line). Done.

5. **On hook failure** — do **not** retry, do **not** add `--no-verify`
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

6. **If all three checks pass**, present the standard message verbatim:

   > The pre-commit hook failed, but the failure is in `<file/check>`
   > which is unrelated to the files in this commit
   > (`<list pathspec files>`). This appears to be a pre-existing
   > issue. It may be OK to bypass the hook for this commit with
   > `--no-verify`. Do you want me to proceed with `--no-verify`, or
   > fix the hook failure first?

   Wait for explicit user approval. On approval, retry via the
   wrapper with `--no-verify`:

   ```bash
   scripts/commit-pathspec.sh --no-verify "<message>" <file> [<file> …]
   ```

   On refusal, stop — the user will fix the hook failure first.

7. **If any of the three checks fails**, do **not** offer `--no-verify`.
   Report which check failed, surface the relevant hook output, and
   stop — the user diagnoses or fixes.

## Caller anti-patterns

These are the failure modes that motivated the actor-clarification at
the top of `## Steps`. Recognise and avoid them — every one of them
duplicates work the skill is about to do.

- **Pre-staging untracked files with `git add` "to help".** The skill
  does this in step 2; doing it externally defeats the wrapper's
  untracked-detection signal and mixes caller intent with whatever
  the index already held. Just pass the files.
- **Inspecting / unstaging the index before invoking.** The wrapper
  uses pathspec form, which builds a temp index from HEAD + the named
  files; it does not read the real index for the commit content. The
  real index's pre-state is irrelevant to what gets committed.
- **Running `git add` after a hook failure to "clean up".** Pathspec
  hook failures leave the real index untouched on purpose — that's
  the parallel-session safety property. There is nothing to clean
  up. Re-invoke `/commit` with the same arguments after fixing the
  underlying cause, or follow step 6's three-check `--no-verify` flow.

## Local success ≠ mergeability — the CI gate

A successful `/commit` only means the local pre-commit hook accepted
the change. The PR still has to clear the CI merge gate on `main`
before the **Merge pull request** button on GitHub is enabled. The
gate runs every required workflow on a real GitHub runner and
catches things a fast local hook cannot — flaky integration tests,
cross-platform formatting drift, generated-file staleness.

Bypassing the local hook with `--no-verify` per step 6's three-check
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
