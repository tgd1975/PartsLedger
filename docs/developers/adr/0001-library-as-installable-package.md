---
id: ADR-0001
title: PartsLedger ships as an installable Python package (`partsledger`)
status: Accepted
date: 2026-05-14
dossier-section: ../ideas/archived/idea-014-project-setup-review-vs-circuitsmith.md
---

## Context

PartsLedger needs a canonical home for Python code. The two options
considered:

1. **Skill folder is the library** — Python sits under
   `.claude/skills/*/` directly; the wheel is a no-op.
2. **`src/partsledger/` layout** — code lives in a real Python
   package; `scripts/*.py` and `.claude/skills/*/*.py` files are
   thin shims that import from the package.

CircuitSmith made the same choice in
[ADR-0012](../../../../CircuitSmith/docs/developers/adr/0012-library-as-installable-package.md)
because it was reversing an earlier "skill folder is the library"
ADR. PartsLedger has no prior ADR to supersede; this ADR is the
founding decision, captured in writing because the cross-cutting
nature (every future Python module in EPICs 005-008 depends on the
layout) justifies the record even without a prior decision to
overturn.

## Decision

PartsLedger ships as an **installable Python package** named
`partsledger`. The on-disk layout is `src/partsledger/<module>/`
(declared via `[tool.setuptools.packages.find] where = ["src"]` in
`pyproject.toml`). Module-deep logic lives inside the package; files
under `scripts/*.py` and `.claude/skills/*/*.py` are thin shims
(argparse + one call into `partsledger.*`). The shim convention is
documented in [`CLAUDE.md` § Shim convention](../../../CLAUDE.md#shim-convention)
and enforced for the no-host-imports half by
[`scripts/portability_lint.py`](../../../scripts/portability_lint.py)
on every commit.

The package's public surface is defined and versioned in
[`RELEASING.md`](../../../RELEASING.md) over three axes (Python API,
CLI, inventory-MD schema). Private helpers live under
`partsledger._dev.*` and are exempt from the public-surface contract.

## Consequences

**Easier:**

- Each module gets one canonical implementation point, one canonical
  test surface (`tests/unit/test_<module>.py`), and one canonical
  import path. Code reviews don't have to relitigate
  scripts-vs-package per task.
- The published wheel contains the same code the agent's skill
  shims call into — no "works in the dev tree, missing from the
  wheel" drift.
- CircuitSmith's `--prefer-inventory` adapter can import
  `partsledger.inventory.lint` / `partsledger.inventory.writer`
  directly from the wheel rather than scraping the host repo.
- `partsledger[resistor-reader]` and future extras hang off
  `[project.optional-dependencies]` without forcing the runtime
  install to carry them.

**Harder:**

- Every shim author has to remember the convention. The
  portability lint catches active violations
  (`from scripts.<...>`, escaped paths, hardcoded repo paths)
  but the *shim-thinness* half is code-review only.
- Tests have to be runnable both against the in-tree
  `src/partsledger/` (via `sys.path` insertion or editable
  install) and the built wheel (via `tests/unit/test_extras.py`
  patterns). Two install profiles to keep green.
- A schema-breaking inventory-MD change forces a MAJOR semver bump
  on the whole package, even when the Python API is byte-identical.
  This is by design — downstream CircuitSmith consumers need the
  signal — but it raises the cost of casual schema iteration.

The decision is load-bearing for **EPICs 005 (USB camera capture),
006 (visual recognition), 007 (metadata enrichment), and 008
(resistor color-band reader)** — none of those epics' modules are
importable as `partsledger.*` until the layout exists. EPIC-004 is
the cross-cutting Phase 0b that lands the layout + the surrounding
contract.

## See also

- [`CLAUDE.md` § Shim convention](../../../CLAUDE.md#shim-convention) — the project-wide policy this ADR records.
- [`RELEASING.md`](../../../RELEASING.md) — the public-surface definitions this layout makes addressable.
- [`docs/developers/ideas/archived/idea-014-project-setup-review-vs-circuitsmith.md`](../ideas/archived/idea-014-project-setup-review-vs-circuitsmith.md) — the dossier that surfaced the layout question.
- CircuitSmith [ADR-0012](../../../../CircuitSmith/docs/developers/adr/0012-library-as-installable-package.md) — the sibling-project analogue (which reverses CircuitSmith's earlier ADR-0007; PartsLedger has no equivalent prior decision).
- [`scripts/portability_lint.py`](../../../scripts/portability_lint.py) → [`src/partsledger/_dev/portability_lint.py`](../../../src/partsledger/_dev/portability_lint.py) — the lint that enforces the no-host-imports invariant.
