# Branch Protection — Concept

PartsLedger's branch policy (no direct commits to `main`,
squash-merge only) is enforced **client-side** today via
[`/check-branch`](../../.claude/skills/check-branch/) and the
[`/commit`](../../.claude/skills/commit/) skill. Adding **server-side**
enforcement via GitHub branch protection is the next layer: even a
push from a contributor without the local tooling — accidental or
deliberate — cannot bypass the rules.

This doc records the **ruleset and rationale**. The follow-on task
([TASK-013](tasks/open/task-013-apply-branch-protection.md)) applies
the config to the GitHub repo. Splitting concept from action means
the rationale survives even if the live config later drifts.

## Ruleset

| Rule | Setting | Rationale |
|---|---|---|
| Require status checks | **Yes** — `Test (ubuntu-latest)`, `Test (windows-latest)` | CI must be green before merge. |
| Require branches up to date | **Yes** (strict) | No merge of stale branches; the CI run that gates the merge is on the same merge base reviewers saw. |
| Require PR review | **No** | Solo project. Admin-self-approval is a deadlock on GitHub for branch protection — the owner cannot approve their own PR — and every solo merge would block. **Trigger to flip on:** contributor #2 lands. |
| Enforce for administrators | **No** | Owner needs to land hot-fixes without a bypass dance. The admin-bypass is logged in the GitHub event log. |
| Allow force pushes | **No** | Reflog-recovery property: anything that lands on `main` can be reconstructed from local clones. Force-push breaks that. See [`CLAUDE.md` § Branch merges](../../CLAUDE.md#branch-merges--squash-not-fast-forward). |
| Allow deletions | **No** | `main` is permanent; deletion would orphan every fork and re-clone. |
| Require linear history | **Yes** | Matches the squash-merge-only policy in CLAUDE.md. Merge commits on `main` would defeat the "one squashed commit per branch" rule. |

## Rejected alternative — "require PR review with admin-enforcement off"

The defensible alternative to "require PR review: No" was:

| Rule | Setting | Rationale (alt) |
|---|---|---|
| Require PR review | Yes — 1 approving review | Server-enforces the four-eye principle. |
| Enforce for administrators | **No** | Admin can self-merge by toggling enforcement off → merging → toggling back on. |

Why rejected at the current stage: the workflow is solo. The
toggle-merge-toggle dance is real per-commit friction without a
matching benefit (no second human is reviewing). The autonomous-loop
posture documented in [`AUTONOMY.md`](AUTONOMY.md) already gates
remote-effect actions on explicit per-invocation user approval — the
agent cannot push to `main` without that approval. The "require PR
review" rule adds a click-through on top of that approval, not a
qualitatively new check.

This alternative is **the planned flip** when contributor #2 joins —
keep the entry around as a one-line edit, not a re-derivation.

## When to revisit

Concrete triggers that should re-open this ruleset:

- **Contributor #2 lands.** Flip "require PR review" to "yes —
  1 approving review". Admin-enforcement stays off so the owner can
  still hot-fix.
- **A real incident.** A push that should have been blocked but
  wasn't, or a block that hurt a legitimate workflow. File a
  security-tagged task and revisit.

The trigger to **tighten further** (e.g. "require code-owner review",
"require signed commits") is sustained contributor growth, not
calendar.

## Implementation path

The live config is applied via the GitHub REST API:

```bash
gh api -X PUT /repos/tgd1975/PartsLedger/branches/main/protection \
   --input <json-body>
```

The JSON body translates the ruleset above into the protection schema
([GitHub docs](https://docs.github.com/en/rest/branches/branch-protection)).
The exact body lands in
[TASK-013](tasks/open/task-013-apply-branch-protection.md)'s implementation;
it is `human-in-loop: Main` because `gh api -X PUT` is a remote-effect
action that always requires explicit per-invocation user approval per
[`AUTONOMY.md` § No-published-effect](AUTONOMY.md#no-published-effect-without-approval).

## Branch naming

Per [`CLAUDE.md` § Branch merges](../../CLAUDE.md#branch-merges--squash-not-fast-forward):

| Branch kind | Pattern | Example |
|---|---|---|
| Epic | `release/epic-NNN-<slug>` or `feature/<slug>` | `feature/align-with-circuitsmith` |
| Chore | `chore/<scope>` | `chore/security-deny-list` |
| Fix | `fix/<scope>` | `fix/embedding-norm` |
| Refactor | `refactor/<scope>` | `refactor/inventory-loader` |

Names are topic-bound, hyphenated, lowercase. The squash commit's
subject names the same purpose (`close EPIC-NNN`, `chore(...)`,
`fix(...)`, `refactor(...)`).

## Client-side ≠ server-side — both layers

Client-side enforcement and server-side enforcement target different
threat models:

| Layer | Catches | Misses |
|---|---|---|
| Client (`/check-branch`, `/commit` provenance token) | Accidental `git commit` on main; raw `git commit` bypassing `/commit`; commits without the agent's discipline. | A push from a fork / a checkout without the hooks installed. |
| Server (GitHub branch protection) | Direct push to `main`; force-push; deletion; merge of stale branches; merge with CI red. | A commit landing on `main` *via* a PR merge — the server only enforces the merge gate, not the per-commit policy inside the branch. |

The two layers compose: a contributor without the local hooks can
still push to a feature branch and PR-merge to `main`; the
server-side rules ensure CI gates that PR; the client-side rules
ensure that once the contributor *does* install the hooks, every
commit on their feature branch follows the local policy.

Both are needed. Neither alone is enough.

## Updating this doc

If the ruleset changes (TASK-013 amends the live config, or a
future task flips a rule per a triggered revisit), update this doc
**before** running the `gh api -X PUT` — the doc is the source of
intent. The live config can drift from the doc only as long as it
takes to merge the doc update; after that, drift is a bug.
