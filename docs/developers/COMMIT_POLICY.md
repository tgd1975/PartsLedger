# Commit Policy

PartsLedger enforces a stricter commit protocol than most Python
projects:

- Every commit flows through the `/commit` skill.
- `/commit` invokes `scripts/commit-pathspec.sh`, which uses git's
  **pathspec form** rather than the staging-area form.
- The pre-commit hook validates a one-shot provenance token that only
  the wrapper script writes, so raw `git commit` is rejected.
- Topic branches squash-merge to `main`; CHANGELOG `[Unreleased]`
  rides along in the same squash.
- LLM-attribution trailers (`Co-Authored-By: Claude …`) are stripped
  from both commits and PR bodies.

This doc explains *why* — the rationale that turns the rules from
arbitrary policy into self-evident plumbing.

## Why pathspec, not `git add` + `git commit`

The two forms look equivalent for a solo session. They are not.

### The two-step form (mainstream)

```bash
git add file_a.py file_b.py
git commit -m "..."
```

This mutates the **real index** in two steps. The pre-commit hook
runs against the real index. If the hook fails, the named files stay
staged.

### The pathspec form (what `/commit` uses)

```bash
git commit -m "..." -- file_a.py file_b.py
```

This builds a **temporary index** containing only the named files,
runs the pre-commit hook against that temp index, and updates the
real index **only if the commit succeeds**. Hook failure leaves the
real index exactly as it was.

### The race-condition story — concretely

Two Claude sessions are running concurrently in the same checkout.
Session A is working on `docs/developers/ARCHITECTURE.md`. Session B
is working on `scripts/foo.py`.

**With the two-step form:**

```text
t=0   Session A: git add docs/developers/ARCHITECTURE.md
                 → real index has ARCHITECTURE.md staged.
t=1   Session B: git add scripts/foo.py
                 → real index has BOTH ARCHITECTURE.md AND foo.py staged.
t=2   Session A: git commit -m "..."
                 → commits BOTH files. Session B's foo.py is now in
                   Session A's commit, with Session A's message.
```

The commit is structurally wrong — Session A claims authorship for
work it didn't do — and the message is misleading.

**With the pathspec form:**

```text
t=0   Session A: git commit -m "..." -- docs/developers/ARCHITECTURE.md
                 → temp index = HEAD + ARCHITECTURE.md.
                   Hook runs, commit succeeds. Real index untouched.
t=1   Session B: git commit -m "..." -- scripts/foo.py
                 → temp index = HEAD + foo.py. Independent commit.
                   No clobber, no message mix-up.
```

Each session's commit contains exactly the files it named, regardless
of what was happening elsewhere. The two-step form's failure mode is
silent (the commit looks like a normal merge of two sessions' work);
the pathspec form makes the isolation structural.

This is the **why** behind the policy. Once you've internalised it,
the rule "always use `/commit`" is no longer arbitrary — it is the
only form that survives concurrent sessions.

## The provenance token

Pathspec form alone is not enough — a contributor could still type
the pathspec command by hand, skip `/commit`, and accidentally invoke
behaviour the skill is supposed to enforce (auto-fix scoping, the
three-check hook-failure protocol). To prevent that, the pre-commit
hook validates a **one-shot provenance token**.

The flow:

1. `scripts/commit-pathspec.sh` runs, writes
   `.git/pl-commit-token` with the form `<pid> <nonce> <unix-ts>`.
2. The script invokes `git commit -m "..." -- <files>`.
3. Git invokes `.git/hooks/pre-commit` (the wrapper installed by
   `scripts/install_git_hooks.sh`), which delegates to
   `scripts/pre-commit`.
4. `scripts/pre-commit` reads the token, validates it:
   - Age ≤ 60 seconds.
   - `pid` is an ancestor of the hook process.
5. If valid → hook continues with its lint / commit-policy
   checks. If missing or stale → hook rejects with a structured error.
6. After the commit completes (success or failure), the wrapper
   deletes the token (one-shot).

This means **only `scripts/commit-pathspec.sh` can produce a commit**.
A raw `git commit -m "..." -- foo.py` will fail at step 4 because the
token is absent. A second `git commit` invocation in the same window
will fail because the token is single-use.

Read the source for both halves:
[`scripts/commit-pathspec.sh`](../../scripts/commit-pathspec.sh)
and [`scripts/pre-commit`](../../scripts/pre-commit).

## The three-check hook-failure protocol

When a pre-commit hook fails on changes you didn't author (e.g. the
markdown lint reports an unrelated file you didn't touch), the
`/commit` skill applies a three-check protocol from
[`.claude/skills/commit/SKILL.md`](../../.claude/skills/commit/SKILL.md)
before any `--no-verify`. Summary:

1. **Pathspec files only.** Is the failing check unrelated to every
   file in the pathspec list?
2. **Pre-existing breakage.** Does the failing check already fail on
   `HEAD` or `main`, independent of this commit?
3. **No silent regression.** Could the pathspec files plausibly affect
   the failing check (via include / import / generated code)?

All three must pass before `--no-verify` is even on the table. If any
fails → fix the underlying issue, do not bypass.

If all three pass, the skill presents a verbatim message asking for
**explicit user approval** before retrying with `--no-verify`. The
agent never silently bypasses.

## Bypass policy — `PL_COMMIT_BYPASS`

There is one escape hatch for the provenance-token check:

```bash
PL_COMMIT_BYPASS="<reason>" git commit ...
```

Set the env var to a non-empty reason; the hook accepts the commit
and **logs the bypass** to `.git/pl-commit-bypass.log` with timestamp,
reason, and review state (`pending`).

Legitimate uses:

- Interactive rebase (`git rebase -i`) where individual commits
  cannot be re-routed through `/commit`.
- Recovery from a broken `/commit` skill (a hook bug, a wrapper
  bug).
- Rare manual repo surgery (squash-merge mechanic, history rewrite).

**Not** legitimate uses:

- Silencing a hook to land work.
- "Just this once" — every "just this once" should be logged with a
  real reason and reviewed.
- Routine commits when `/commit` is available — the wrapper exists
  for a reason.

Bypasses are reviewed in batch by the user. If the same reason fires
repeatedly, the right move is to fix the underlying tooling (open a
task to refine the hook, add an allowlist), not normalise the
bypass.

## Squash-merge to `main`

Server-side enforcement of the merge gate lives at
[`BRANCH_PROTECTION_CONCEPT.md`](BRANCH_PROTECTION_CONCEPT.md) (the
ruleset that backs this policy via GitHub branch protection).

Topic branches (`release/epic-NNN-…`, `chore/<scope>`,
`fix/<scope>`, `refactor/<scope>`) land on `main` as **one squashed
commit per branch** — never plain fast-forward, never a merge commit.

The commit subject names the branch's primary purpose:

- `close EPIC-NNN: <name>` for an epic branch.
- `chore(<scope>): <summary>` for a chore branch.
- `fix(<scope>): <summary>` for a bug fix.
- `refactor(<scope>): <summary>` for a refactor.

Commits that rode along on the same branch but aren't the named work
are rolled into the same squash; the commit body enumerates them so
the rollup is traceable.

Mechanic (local): from `main`, `git merge --squash <topic-tip>`
stages the change, you add the CHANGELOG bullets (see next section),
and `/commit` records it as one commit. GitHub's "Squash and merge"
PR button is the remote equivalent.

The rule applies to **every** merge to `main`, not just release
boundaries.

## CHANGELOG rides with the squash

`CHANGELOG.md`'s `[Unreleased]` section is updated **as part of the
same squash commit** that lands the work, not in a follow-up. One
bullet per closed task (with `TASK-NNN` reference) or per logical
non-task change, filed under the appropriate Keep-a-Changelog
heading (`### Added`, `### Tooling`, `### Policy`, etc.).

If you finish a branch and realise the CHANGELOG wasn't updated,
**amend before merging**. Do not merge first and "circle back" — a
CHANGELOG diff that lags behind `git log` defeats the purpose of
having a changelog.

## LLM-attribution trailers — no

`Co-Authored-By: Claude …`, "Generated with Claude Code", "🤖
Generated with …" — none of these appear in PartsLedger's commit
messages or PR bodies. The user has explicitly rejected the trailer
form; the `/commit` skill strips them; reviewers should flag them on
sight.

The reasoning: a commit's authorship is the maintainer's, and the
LLM is a tool, not a contributor. The trailer creates ambiguity
about who owns the change, which matters for security review and for
the audit trail.

## Recipe — recover from a hook failure that flags unrelated files

You are in the middle of a `/commit` invocation; the hook reports a
markdown-lint failure in a file you didn't touch. The pathspec mode
left the real index untouched.

1. **Don't touch `git status`.** The "dirty" state is the
   parallel-session protection working — there is nothing to clean
   up.
2. Read the hook output. Identify the file and the rule. Is it
   actually unrelated to your pathspec?
3. Apply the three checks above.
4. If all three pass, the skill will surface the verbatim
   `--no-verify` request. Approve it explicitly.
5. If any check fails → fix the underlying issue first, then re-run
   `/commit` with the same arguments.

## When this policy hurts

It does, occasionally. The pathspec form has no equivalent of `git
add -p` (partial-hunk staging). Renames must name both old and new
path in the pathspec. Untracked files require the wrapper's
`--stage-untracked` flag (the `/commit` skill passes it
automatically).

The decision was: parallel-session safety is worth the friction,
because the alternative — silent cross-session clobbering — is the
kind of bug that is invisible until a commit looks fine but is
subtly wrong, which is the worst kind. The friction is paid once per
commit; the bug is paid in lost trust.

If you find a workflow this policy genuinely breaks (not just
"makes slower"), file an idea: maybe the tooling can be extended,
or maybe the policy needs a narrow exception. Don't bypass and
move on.
