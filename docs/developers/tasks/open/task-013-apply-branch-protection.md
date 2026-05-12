---
id: TASK-013
title: Apply server-side branch protection to tgd1975/PartsLedger main
status: open
opened: 2026-05-12
effort: Small
complexity: Senior
human-in-loop: Main
epic: align-with-circuitsmith
order: 13
prerequisites: [TASK-002, TASK-006]
---

## Description

Apply the server-side branch-protection ruleset to
`tgd1975/PartsLedger`'s `main` branch via the GitHub REST API. This
is the **server** half of the two-layer policy documented in
`docs/developers/BRANCH_PROTECTION_CONCEPT.md` (the client half is
already in place via the new `/commit` skill, the `/check-branch`
skill, and `.claude/settings.json`'s deny entries).

**`human-in-loop: Main`** because `gh api -X PUT` is a remote-effect
action that requires explicit per-invocation user approval per
`AUTONOMY.md § No-published-effect-without-approval`. The agent
prepares the JSON body and the command line; the user runs it.

## Ruleset

Per `BRANCH_PROTECTION_CONCEPT.md`:

| Rule | Setting |
|---|---|
| Require status checks | **Yes** — `Test (ubuntu-latest)`, `Test (windows-latest)` |
| Require branches up to date | **Yes** (strict) |
| Require PR review | **No** (solo project; flip on contributor #2 lands) |
| Enforce for administrators | **No** (owner keeps hot-fix path) |
| Allow force pushes | **No** |
| Allow deletions | **No** |
| Require linear history | **Yes** |

## Implementation

```bash
gh api -X PUT /repos/tgd1975/PartsLedger/branches/main/protection \
   --input <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Test (ubuntu-latest)", "Test (windows-latest)"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

(The exact JSON body is per the GitHub API schema —
[docs](https://docs.github.com/en/rest/branches/branch-protection).
Validate the field names against the live API before invoking;
spelling drift here is silent.)

## Acceptance Criteria

- [ ] CI workflow from TASK-002 has run at least once on a PR and
      produced the named status checks (`Test (ubuntu-latest)`,
      `Test (windows-latest)`), otherwise the protection rule cannot
      reference them.
- [ ] `gh api -X GET /repos/tgd1975/PartsLedger/branches/main/protection`
      returns the ruleset above (the GET is the verifier after the
      PUT).
- [ ] A test direct push to `main` from a contributor without
      admin enforcement disabled is **rejected**.
- [ ] A test PR with red CI is **not mergeable**.
- [ ] A force push to `main` is **rejected** (verify via the API or
      attempt — careful).
- [ ] `BRANCH_PROTECTION_CONCEPT.md` (TASK-006) ruleset table
      matches the live config (the doc is the source of intent —
      drift between doc and live is a bug to fix in the doc, not
      in the live config).

## Test Plan

1. Verify the prerequisite: open a throwaway PR with a trivial doc
      change; confirm both `Test (ubuntu-latest)` and
      `Test (windows-latest)` checks appear in the PR view.
2. Apply the protection via the `gh api -X PUT` command above
      (user-driven, explicit approval).
3. `gh api -X GET ...` confirms the live ruleset.
4. Try `git push origin main` from a fresh clone — rejected (or
      requires admin-enforcement-off, which is intentionally
      retained on this repo).

## Notes

The PR-review rule is intentionally off (solo project). The trigger
to flip it is contributor #2 landing — captured in
`BRANCH_PROTECTION_CONCEPT.md § When to revisit`. Until then,
admin-bypass is acceptable and logged in the GitHub event log.
