# Scripts drift audit — PartsLedger ↔ CircuitSmith

TASK-028 audit comparing every shared `scripts/` file against its
CircuitSmith counterpart at `../CircuitSmith/scripts/<same-name>`.
Snapshot date: **2026-05-14**.

Format: one row per file. `Decision` is one of:

- **pull-from-upstream** — replace PartsLedger's copy with
  CircuitSmith's; PL was strictly older with no local divergence.
- **keep-local** — PartsLedger has diverged for a project-specific
  reason; the rationale is recorded so future audits don't re-litigate
  it.
- **merge** — both repos have diverged in interesting ways and
  PL needs hand-picked changes from CS.

| File | Drift | Decision | Rationale |
|------|-------|----------|-----------|
| `commit-pathspec.sh` | 4 lines | **keep-local** | `cs-commit-token` → `pl-commit-token` substitution. Cross-project token names must not collide. |
| `codeowner_hook.py` | 2 lines | **keep-local** | Docstring drops a CS-specific TASK-055 reference. Same code path otherwise. |
| `install_git_hooks.sh` | 2 lines | **keep-local** | `CS_SKIP_SECURITY_REVIEW` → `PL_SKIP_SECURITY_REVIEW` substitution in the user-facing hint. |
| `release_burnup.py` | 4 lines | **keep-local** | Whitespace / quoting style only; behaviour identical. |
| `task_system_config.py` | 13 lines | **keep-local** | CS migrated from `pyyaml` to `ruamel.yaml`; PL still uses `pyyaml`. Both are functionally equivalent for safe-load; pyyaml is the lighter dep and is already in PL's pyproject. Switching would require a `pyproject.toml` dep bump for marginal benefit. |
| `housekeep.py` | 73 lines | **keep-local** | Divergent evolution: PL still references `sync_task_system.py` in the sibling-script audit docstring (closed via TASK-001); CS deleted that bullet. Lock-holder PID storage differs (PL: in-lockfile; CS: sidecar `.pid` file to work around Windows `msvcrt.locking` byte-range read blocks). Output messages use `tasks/OVERVIEW.md` qualified paths (PL) vs bare `OVERVIEW.md` (CS). VERSION lookup in PL falls back to upstream `awesome-task-system/VERSION`; CS only checks the local one. Behaviour is equivalent on both sides; a true merge would be churn. Re-audit if Windows lock contention shows up in practice (the CS sidecar fix would be the answer). |
| `release_snapshot.py` | 136 lines | **keep-local** | CS implements a Phase 2b release gate around its AI-placer chain (`PHASE2B_TASK_IDS`, `CS_PHASE2B_BYPASS`, `check_phase2b_gate`). PartsLedger has no equivalent gate — the camera-path pipeline doesn't have a comparable release-blocking signal. Pulling the gate scaffold without the corresponding task chain would leave dead code. |
| `security_review_changes.py` | 243 lines | **keep-local (candidate for future pull)** | CS gained a personal-data leak detector (TASK-074) that walks every changed text-bearing file against patterns loaded from a `.gitignore`d `scripts/git-hooks/personal_data_patterns.yml`. Useful safety net, but porting requires (a) a new template + gitignore entry, (b) `ruamel.yaml` dep (which conflicts with the PL `pyyaml` choice in `task_system_config.py`), and (c) a separate test surface. Out of EPIC-004's scope; file a follow-up task if a maintainer pastes PII into a diff and wants automated coverage. |
| `pre-commit` | 156 lines | **keep-local** | PartsLedger has added three stanzas CS doesn't have: inventory schema lint (TASK-017), hedge-language lint (TASK-019), and portability lint (TASK-026). The base commit-provenance + markdownlint + ruff blocks match CS structurally. |
| `update_idea_overview.py` | _identical_ | _no decision_ | Byte-for-byte match. |
| `update_task_overview.py` | _identical_ | _no decision_ | Byte-for-byte match. |
| `update_scripts_readme.py` | _identical_ | _no decision_ | Byte-for-byte match. |

## Resolution

All 9 drifted files resolve to **keep-local**. No file is pulled
from upstream in this audit; one (`security_review_changes.py`) is
flagged as a follow-up candidate when a maintainer's threat model
expands to PII scanning. The three byte-identical files need no
action.

## Out-of-scope

CircuitSmith's domain-specific scripts (`check_circuit_schema.py`,
`check_erc_reports.py`, `check_exporters.py`,
`check_gallery_regression.py`, `check_phase2b_trigger.py`,
`regenerate_circuit_artefacts.py`) are explicitly **not** in scope
per IDEA-014 § What probably doesn't port. They cover schematic /
ERC / catalog concerns that have no PartsLedger analogue.

## Re-audit triggers

- A new CS release ships and PartsLedger contributors notice that
  their copy of `housekeep.py` / `pre-commit` is meaningfully older.
- A maintainer pastes PII into a PartsLedger diff and wants the
  PII detector ported (the `security_review_changes.py` follow-up).
- The Windows lock contention scenario described in `housekeep.py`'s
  row materialises and PL needs the CS sidecar-PID fix.
