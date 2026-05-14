# Releasing PartsLedger

How PartsLedger cuts a release — the operational counterpart of
[ADR-0001](docs/developers/adr/0001-library-as-installable-package.md)
(the *decision* to publish as a Python package) and
[`docs/developers/COMMIT_POLICY.md`](docs/developers/COMMIT_POLICY.md)
(the *mechanics* of how the bump commit lands).

The agent-facing driver is the [`/release`](.claude/skills/release/SKILL.md)
skill — point it at a target version and it walks the steps in this
document. This document is the *source of truth*; the skill is the
*operational driver*.

## When to cut a release

- **Closed-epic boundary.** When an epic with public-surface impact
  closes (a new public symbol under `partsledger.*`, a new CLI flag,
  an additive frontmatter key in `inventory/parts/*.md`), cut a minor
  or patch release so consumers can pin to a tag.
- **Fix rollup.** A handful of patch-worthy fixes have landed since
  the last release and at least one consumer is asking for them.
- **Manual trigger.** The maintainer wants to anchor a stability
  claim against the most recent `main`.

There is no fixed cadence. PartsLedger ships when there is something
worth shipping, not on a calendar.

## Semver policy — three public surfaces

`partsledger` follows [Semantic Versioning](https://semver.org/) for
**three** public surfaces. CircuitSmith keys its semver on two (Python
API + CLI); PartsLedger adds a third, because the inventory-MD schema
is consumed downstream by CircuitSmith's `--prefer-inventory` adapter
and a schema break there is exactly the kind of integration regression
semver exists to communicate.

The three surfaces, listed in the order they appear in this section:

1. **Python API** — names exposed via `from partsledger import …`,
   including every public submodule (`partsledger.inventory.writer`,
   `partsledger.inventory.lint`, `partsledger.inventory.hedge_lint`,
   `partsledger.inventory.family`, etc.). Public means "documented or
   reasonably-discoverable to a downstream importer"; private helpers
   live under `partsledger._dev.*` and are exempt.
2. **CLI** — every command registered via `[project.scripts]` in
   `pyproject.toml`, plus the documented `python -m partsledger.<sub>`
   entry points (capture, recognition, enrichment as those land).
3. **Inventory-MD schema** — the frontmatter schema in
   `inventory/parts/<part>.md` (per IDEA-004 + IDEA-027) **and** the
   row format / column shape of `inventory/INVENTORY.md`.

| Bump | When |
|------|------|
| `MAJOR` (X.0.0) | Backwards-incompatible removal or rename of a public Python symbol; removed CLI command or removed CLI flag with no replacement; changed CLI flag default; renamed or removed frontmatter key in `inventory/parts/*.md`; renamed or removed column in `inventory/INVENTORY.md` parts tables; row-format change that breaks downstream parsers. |
| `MINOR` (0.Y.0) | New public Python symbol; new CLI command or new flag; additive frontmatter key (e.g. new optional field); additive `INVENTORY.md` column appended at the end of the existing canonical seven; new lint rule (the diagnostic codes carried by `partsledger.inventory.{lint,hedge_lint}` are stable per the Python-API surface). |
| `PATCH` (0.0.Z) | Bug fix, internal refactor, documentation, lint-message tweak that does not change the diagnostic code, hedge-language marker additions to existing parts pages. |

Until the first non-`dev` release, `0.x` versions are considered
pre-stable; consumers should pin to an exact version. Once `1.0.0`
ships, semver applies as documented above.

The inventory-MD schema is governed jointly with CircuitSmith via the
`--prefer-inventory` adapter contract (IDEA-009 → CircuitSmith
IDEA-010). A MAJOR bump driven by a schema break should be coordinated
with the corresponding CircuitSmith release that picks up the new
shape; the coordination is per-release, not per-commit.

## Tag-naming convention

Tags use the literal `v` prefix followed by the semver triple:

```text
v0.1.0
v0.1.1
v0.2.0
```

This mirrors CircuitSmith and AwesomeStudioPedal so a maintainer
fluent in either project's release flow doesn't have to relearn the
tag shape. The `v` prefix is reserved for **tags only**; both
`src/partsledger/__init__.py` and `pyproject.toml` carry the
unprefixed triple (`0.1.0`).

## Version lockstep — two files, one truth

The package version is mirrored in exactly two files:

| File | Field | Format |
|------|-------|--------|
| `src/partsledger/__init__.py` | `__version__ = "X.Y.Z"` | unprefixed semver |
| `pyproject.toml` | `[project] version = "X.Y.Z"` | unprefixed semver |

Both must be edited in the same commit. A drift between the two is a
shipping bug — the wheel built from `pyproject.toml` reports one
version while `import partsledger; partsledger.__version__` reports
another.

## CHANGELOG promotion

`CHANGELOG.md` follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
On release, the working `[Unreleased]` section is renamed to
`[vX.Y.Z] — YYYY-MM-DD` and a fresh empty `[Unreleased]` block is
seeded above it:

```diff
+ ## [Unreleased]
+
- ## [Unreleased]
+ ## [vX.Y.Z] — 2026-05-14

  ### Schema
  - …
```

The promotion is **manual** — `/release` performs it as part of the
bump commit. No bullets are reordered, reworded, or merged during
promotion; the section as-built is what ships.

## Task-system snapshot

After the release commit lands (but before tagging) the live
`OVERVIEW.md` / `EPICS.md` / `KANBAN.md` get frozen into a
per-release snapshot:

```bash
python scripts/release_snapshot.py vX.Y.Z
```

The script writes `archive/<version>/{OVERVIEW,EPICS,KANBAN}_vX.Y.Z.md`,
stripping the auto-generation markers so `housekeep.py` doesn't try
to touch them on later runs. The snapshot answers "what was the task
state as of this release" without forcing later edits to leave
historical entries untouched.

## Burn-up regeneration

The cumulative burn-up at the top of `OVERVIEW.md` gets re-rendered:

```bash
python scripts/release_burnup.py
```

This block lives between `<!-- BURNUP:START -->` and
`<!-- BURNUP:END -->` markers and counts closed tasks / closed epics
/ effort hours since the last tag. Rides into the same commit as the
version bump and CHANGELOG promotion.

## Tag-and-push hand-off to release.yml

The final step is an annotated tag pushed to GitHub:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push
git push --tags
```

The `git push` invocations are **remote-effecting actions** and
require explicit per-invocation user approval per
[`docs/developers/AUTONOMY.md` § No-published-effect-without-approval](docs/developers/AUTONOMY.md#no-published-effect-without-approval).
The `/release` skill must not push without surfacing a confirmation
prompt.

The tag push triggers [`.github/workflows/release.yml`](.github/workflows/release.yml),
which:

1. Checks out the tag.
2. Sets up Python 3.11 (the lower bound of `requires-python`).
3. Runs `uv build` to produce
   `dist/partsledger-X.Y.Z-py3-none-any.whl` and
   `dist/partsledger-X.Y.Z.tar.gz`.
4. Publishes both artefacts to PyPI via
   [trusted publishing](https://docs.pypi.org/trusted-publishers/)
   using `pypa/gh-action-pypi-publish`. No long-lived API tokens.
5. Creates a GitHub Release on the tag with the `dist/*` files
   attached and the matching `CHANGELOG.md` slice as the release
   body.

Trusted publishing requires a one-time registration on pypi.org tying
this GitHub repository to the `partsledger` project. The
**token-based fallback** is documented for completeness but not wired
by default: if PyPI trusted publishing is unavailable, generate an
API token scoped to the `partsledger` project on pypi.org, store it
as the GitHub secret `PYPI_API_TOKEN`, and uncomment the
`password: ${{ secrets.PYPI_API_TOKEN }}` line in `release.yml`.

The release distribution carries every optional extra declared in
`[project.optional-dependencies]` — currently `dev` (developer
tooling) and `resistor-reader` (EPIC-008's reader; the metadata is
seeded by TASK-029 before EPIC-008 lands the implementation). One
distribution, multiple installation profiles via PEP 517 extras.

## End-to-end summary

The `/release vX.Y.Z` skill drives this whole flow. The verbatim step
order it follows is:

1. Verify clean working tree on `main`.
2. Confirm the new version with the user.
3. Bump `__version__` in `src/partsledger/__init__.py` and
   `version` in `pyproject.toml`.
4. Promote CHANGELOG `[Unreleased]` → `[vX.Y.Z] — YYYY-MM-DD`.
5. Regenerate task overviews (`/housekeep`) and burn-up
   (`release_burnup.py`); snapshot overviews
   (`release_snapshot.py vX.Y.Z`).
6. Commit the bump + CHANGELOG + snapshot + burn-up via `/commit`.
7. Create annotated tag `vX.Y.Z`.
8. Push commit + tag (requires explicit user approval).
9. Print the `release.yml` workflow URL so the user can watch the
   PyPI upload and GitHub Release publish.

If any step fails before the tag push, every edit is locally
reversible. After the push, the PyPI upload is **irreversible** —
PyPI does not permit file-name reuse for a given `(project, version)`
combination.

## Cross-references

- [ADR-0001](docs/developers/adr/0001-library-as-installable-package.md) — why PartsLedger ships as a Python package.
- [`docs/developers/CI_PIPELINE.md`](docs/developers/CI_PIPELINE.md) — CI workflows including the release gate.
- [`docs/developers/AUTONOMY.md`](docs/developers/AUTONOMY.md) — autonomy contract, including the push-approval rule.
- [`docs/developers/COMMIT_POLICY.md`](docs/developers/COMMIT_POLICY.md) — pathspec form, provenance tokens, bypass policy.
- [`CHANGELOG.md`](CHANGELOG.md) — the log this flow promotes from.
- [`/release` skill](.claude/skills/release/SKILL.md) — the agent-facing driver for this procedure.
