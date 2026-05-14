---
id: IDEA-014
title: Project setup review — mirror CircuitSmith's release + module layout
description: Mirror CircuitSmith's PyPI release pipeline and src/<package> + shim-scripts-in-skills layout in PartsLedger.
category: 🛠️ tooling
---

## Archive Reason

2026-05-14 — Promoted to EPIC-004 (project-setup), tasks TASK-022..TASK-031.

[CircuitSmith](../../../../../CircuitSmith/) and PartsLedger share most of
their repo plumbing (task system, `/commit` pathspec policy, `/housekeep`,
ruff/pytest config, `scripts/` layout). CircuitSmith has since moved ahead
on two fronts that PartsLedger has not adopted yet:

1. The library lives in an installable Python package at
   `src/circuitsmith/`, and the `.claude/skills/circuit/` folder is just
   the agent-facing surface (prompts + thin shims that `import
   circuitsmith.*`). This is canonised in
   [`CircuitSmith ADR-0012`](../../../../CircuitSmith/docs/developers/adr/0012-library-as-installable-package.md)
   and superseded the older "skill folder *is* the library" arrangement
   (ADR-0007).
2. There is a real release pipeline — `RELEASING.md`, a `/release`
   skill, a `.github/workflows/release.yml`, and a semver policy keyed
   to the public Python API and CLI surface.

PartsLedger today is structured the way CircuitSmith was *before* both
moves: scripts live flat under [`scripts/`](../../../../scripts/), the
existing skills ([`/inventory-add`](../../../../.claude/skills/inventory-add/SKILL.md),
[`/inventory-page`](../../../../.claude/skills/inventory-page/SKILL.md))
are markdown-only and LLM-orchestrated, and
[`pyproject.toml`](../../../../pyproject.toml) explicitly opts out of
package discovery (`[tool.setuptools] py-modules = []` with the comment
"No importable Python package yet"). That was fine while no Python
product code existed. It stops being fine the moment the camera path
([IDEA-006](idea-006-usb-camera-capture.md) /
[IDEA-007](idea-007-visual-recognition-dinov2-vlm.md) /
[IDEA-008](idea-008-metadata-enrichment.md)) lands real modules, and it
makes [IDEA-011](idea-011-resistor-color-band-detector.md)'s
"sub-package, pip-installable" plan a non-starter as long as there is
no parent package to hang off of.

This idea is the cross-cutting "audit CircuitSmith's setup, port what
applies, write down what doesn't" pass.

## What to port (provisional)

A first cut, to be honed:

- **`src/partsledger/` package layout.** Move pipeline code (camera
  capture, DINOv2 cache, VLM client, Nexar client, schema validators)
  into a normal src-layout package; have skills `import partsledger.*`
  rather than carrying logic inline. Drop the `py-modules = []`
  workaround in [`pyproject.toml`](../../../../pyproject.toml) and
  switch to `[tool.setuptools.packages.find] where = ["src"]`.
- **`RELEASING.md` + `/release` skill.** Lift CircuitSmith's
  [`RELEASING.md`](../../../../../CircuitSmith/RELEASING.md) and
  [`.claude/skills/release/`](../../../../../CircuitSmith/.claude/skills/release/SKILL.md),
  rewrite the semver policy against PartsLedger's public surface (the
  inventory-MD schema in [IDEA-004](idea-004-markdown-inventory-schema.md)
  is a public contract too, not just Python API).
- **CI + release workflows.** Add `.github/workflows/ci.yml` and
  `release.yml` matching CircuitSmith's. PartsLedger has no
  `.github/` directory at all today.
- **Shim convention for skills with code.** Document that any skill
  shipping `.py` files keeps them as thin shims — argument parsing
  plus a single call into `partsledger.*` — never module-deep logic
  living under `.claude/skills/<name>/`. CircuitSmith's
  [ADR-0012](../../../../../CircuitSmith/docs/developers/adr/0012-library-as-installable-package.md)
  is the model.
- **`portability_lint.py`** (or local equivalent). CircuitSmith
  enforces the no-host-project-imports invariant on `src/circuitsmith/`
  via [`scripts/portability_lint.py`](../../../../../CircuitSmith/scripts/portability_lint.py);
  the same lint applied to `src/partsledger/` would keep the package
  publishable as a standalone wheel.
- **`uv.lock`.** CircuitSmith pins dev deps via uv's lockfile;
  PartsLedger does not. Adopt for reproducible installs.

## What probably *doesn't* port

CircuitSmith ships a number of domain-specific scripts —
`check_circuit_schema.py`, `check_erc_reports.py`, `check_exporters.py`,
`check_gallery_regression.py`, `check_phase2b_trigger.py`,
`regenerate_circuit_artefacts.py`, `update_netgraph_golden.py` — that
are tied to its KiCad / netgraph / ERC pipeline and have no PartsLedger
analogue. They are listed here only so the audit doesn't accidentally
re-stage them.

The shared plumbing already in PartsLedger (`commit-pathspec.sh`,
`housekeep.py`, `release_burnup.py`, `release_snapshot.py`,
`security_review_changes.py`, `task_system_config.py`,
`update_idea_overview.py`, `update_task_overview.py`,
`update_scripts_readme.py`, `codeowner_hook.py`, `pre-commit`,
`install_git_hooks.sh`) needs a drift check rather than a port —
catch any improvements CircuitSmith made since they were last copied
across.

## Open questions

- **Cut-over timing.** Do the package + release move *now*, while the
  Python surface is still empty (cheapest moment, but the release
  pipeline ships nothing useful yet), or wait until the first camera-path
  module from [IDEA-006-008] is ready to land (forces the layout to
  exist on day one of real code, but means the first "real" module
  arrives mid-refactor)?
- ~~**Sub-package or sibling package for the resistor reader?**~~
  *Closed 2026-05-14.* Sub-package inside PartsLedger, shipped as the
  `partsledger[resistor-reader]` optional extra — *not* a separately
  named distribution. See
  [IDEA-011 § Open questions](idea-011-resistor-color-band-detector.md#open-questions-to-hone)
  for the full rationale. Phase 0b of this dossier must therefore
  configure the release pipeline to support PEP 517 extras (the
  `[project.optional-dependencies]` table in `pyproject.toml` plus a
  release workflow that publishes one distribution carrying all
  extras).
- **Public-surface definition for semver.** CircuitSmith's semver
  policy keys on `from circuitsmith import …` plus documented CLI
  entry points. PartsLedger has a *third* public surface: the
  [inventory-MD schema](idea-004-markdown-inventory-schema.md) that
  CircuitSmith reads via `--prefer-inventory`. Schema-breaking changes
  need to bump MAJOR even if the Python API is unchanged. Spell this
  out in the ported `RELEASING.md`.
- **Drift audit on shared scripts.** Diff the `scripts/` overlap
  between the two repos and decide per-script: pull CircuitSmith's
  newer version, keep PartsLedger's, or merge. Probably worth a
  sub-note (`idea-014.scripts-drift.md`) once the audit runs, rather
  than expanding this dossier.
- **ADR or just an idea conversion?** CircuitSmith captured the
  src-layout decision in
  [ADR-0012](../../../../../CircuitSmith/docs/developers/adr/0012-library-as-installable-package.md)
  because it was reversing an earlier ADR. PartsLedger has no
  prior ADR to supersede here, so the move can probably land via
  task conversion alone — but the cross-cutting nature (touches every
  future skill that ships code) might justify writing an ADR anyway
  so the rationale survives.
