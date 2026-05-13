# Coding Standards

Style guide for PartsLedger's Python code. Short by design — when in
doubt, read [`pyproject.toml`](../../pyproject.toml)'s `[tool.ruff.lint]`
section, which is the authoritative ruleset.

## Tooling

- **Linter / formatter:** [ruff](https://docs.astral.sh/ruff/). Run
  `ruff check .` and `ruff format .` from repo root. The active ruleset
  is deliberately minimal (`E4`, `E7`, `E9`, `F`); expansions are
  deliberate and tracked in commits.
- **Markdown linter:** `markdownlint-cli2`. The pre-commit hook fails
  if it is missing — installed in
  [`DEVELOPMENT_SETUP.md`](DEVELOPMENT_SETUP.md) Step 3.

## Naming conventions

| Element | Convention | Example |
|---|---|---|
| Modules | `snake_case.py` | `inventory.py`, `vision_pipeline.py` |
| Packages | `snake_case/` | `embedding_cache/` |
| Classes | `PascalCase` | `InventoryEntry`, `EmbeddingIndex` |
| Functions / methods | `snake_case` | `identify_part`, `is_known_component` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_EMBED_DIM` |
| Test files | `test_*.py` | `test_inventory.py` |
| Test functions | `test_*` (pytest) | `def test_minimal_construction(): …` |
| Fixture files | `*.md` (a real part-MD entry) | `tests/fixtures/lm358n.md` |
| Private helpers | leading underscore | `_normalize_pin_name` |

Branch naming matches the CLAUDE.md convention: `release/epic-NNN-<slug>`
for epic branches, `chore/<scope>`, `fix/<scope>`, `refactor/<scope>` for
the others. Topic-named, hyphenated, lowercase.

## Formatting

Ruff handles formatting (`ruff format` is the canonical invocation).
Don't hand-format; let the tool win arguments about line length,
trailing commas, and quote style.

## Comment policy

**Default to writing no comments.** A comment earns its place only
when the *why* is non-obvious: a hidden constraint, a workaround for
a specific bug, behaviour that would surprise a careful reader.

Don't explain *what* the code does — well-named identifiers already do
that. Don't reference the current task ("added for TASK-038") or
caller ("used by the renderer") — those belong in the commit message
and rot as the codebase evolves.

```python
# Bad — narrates the obvious
# Loop over each entry and add it to the index.
for entry in entries:
    index.add(entry)

# Bad — task / caller reference
# Added for TASK-038; called from the markdown rewrite path.
def normalize_label(s: str) -> str: ...

# Good — captures the non-obvious WHY
# DINOv2 returns L2-unnormalised embeddings; sqlite-vec's cosine
# distance assumes unit norm — normalise on insert, not on query.
embedding = embedding / np.linalg.norm(embedding)
```

If you cannot write the WHY in one short line, file an ADR under
[`docs/developers/adr/`](adr/) and reference it from a comment.

## Type hints

Type hints are **required on public functions** — anything that lives
at module scope and a caller from another module might import. Type
hints on local helpers are optional but encouraged.

```python
# Public — type hints required
def identify_part(image_path: Path) -> InventoryEntry: ...

# Local helper — type hints optional
def _flip_y(y):
    return -y
```

There is no `mypy --strict` gate yet — type hints are documentation
and review aid, not a runtime contract. A future task will revisit
this when the product code is large enough to justify the gate.

## Commit subjects and branch lifecycle

The full rationale (pathspec mechanics, squash-merge policy,
CHANGELOG rhythm) lives in
[`COMMIT_POLICY.md`](COMMIT_POLICY.md). The minimum to remember:

- One feature / fix per commit. Files named explicitly via `/commit`.
- Commit subject: `<type>(<scope>): <imperative summary>` —
  `fix(pipeline): clamp embedding norm before sqlite insert`,
  `chore(EPIC-001): align with CircuitSmith framework`.
- Topic branches squash-merge to `main`. CHANGELOG `[Unreleased]` is
  updated as part of the same squash.

## When the standards don't cover your case

Pick the most defensible default and continue. If the choice is
non-obvious and likely to repeat, file an ADR
([`adr/0000-template.md`](adr/0000-template.md)) and link it from
this doc.
