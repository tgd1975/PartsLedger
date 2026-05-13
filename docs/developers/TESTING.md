# Testing

How PartsLedger's tests are organised, what each layer is for, and
how to add a new one.

## Test layers

PartsLedger uses three conceptual test layers, each with a distinct
scope and failure signal:

| Layer | Scope | Failure means |
|---|---|---|
| **Unit** | Pure helpers — no I/O, no fixtures. Frontmatter parsers, pin-aliasing rules, embedding-norm helpers against synthetic inputs. | A helper's contract is wrong. Fast (<1s); runs on every push. |
| **Integration** | The pipeline end-to-end against committed sample images + reference MD entries: camera-capture stub → embedding → vision-id → MD-author. | A stage's contract with adjacent stages is broken. |
| **Contract / golden** | Inventory-MD schema-validation (frontmatter shape against IDEA-027 vocabulary), embedding-vector dimensionality, codeowner-hook registry parse, security-review static-rule golden output. | A cross-cutting invariant the codebase makes a commitment to. |

Layer is a **concept**, not a directory enforcement: tests can live
flat under `tests/test_*.py` while the suite is small, and split into
`tests/unit/`, `tests/integration/`, `tests/contract/`
subdirectories once the file count makes flat browsing painful. The
acceptance gate is the same either way: the test file is collected by
`pytest` and asserts the right thing.

A second test root, `scripts/tests/`, exists for **task-system tooling
tests** (housekeep, code-owner hook, security-review static rules,
etc.). These are not product-code tests.

## `pyproject.toml` configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests", "scripts/tests"]
```

Two test roots, one configuration. `pytest` from the repo root picks
up both. Missing directories are silently skipped — `tests/` does not
yet exist at concept stage; the first product-code test creates it.

## Framework choice — pytest

Pytest is the framework for **new** tests, written as plain functions
with parametrize and fixtures.

```python
# tests/unit/test_inventory.py
import pytest
from partsledger.inventory import InventoryEntry

def test_minimal_construction():
    entry = InventoryEntry(part="LM358N", quantity=1)
    assert entry.part == "LM358N"

@pytest.mark.parametrize("field", ["part", "manufacturer", "package"])
def test_required_frontmatter_fields_are_enforced(field):
    ...
```

### Coexistence with existing `unittest.TestCase` files

`scripts/tests/` predates this decision and uses `unittest.TestCase`.
Pytest collects `TestCase` subclasses natively, so those files
**coexist as-is** — no rewrite. New tests under `scripts/tests/` may
be written either way; new tests under `tests/` are pytest-functions
only.

## Fixture layout

Fixtures live next to the layer they support, never at repo root:

- **Pipeline integration fixtures** — `tests/fixtures/*.md` (sample
  inventory entries) plus `tests/fixtures/images/*.jpg` (captured
  camera frames). Committed source files, parametrize-loaded by the
  integration tests. A new fixture is one file pair; no Python wiring
  needed beyond the `pytest.fixture` loader.
- **Golden artefacts** — `tests/fixtures/*.json` (or `.txt`, per the
  contract). Generated artefacts captured under version control; the
  test re-renders and compares.
- **Unit-test fixtures** — inline in the test file as small Python
  literals. Don't reach for a fixture file for three lines of data.

Shared fixtures across layers go in a `conftest.py` at the lowest
common ancestor — typically `tests/conftest.py`.

## Writing a new test

### Pure-unit example

```python
# tests/test_frontmatter.py
from partsledger.frontmatter import is_known_category

def test_known_category_recognised():
    assert is_known_category("opamp")

def test_unknown_category_rejected():
    assert not is_known_category("totally-fake-category")
```

Run with `pytest tests/test_frontmatter.py`.

### Pipeline-integration example

```python
# tests/test_full_pipeline.py
from pathlib import Path
import pytest
from partsledger.pipeline import identify

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "images"

@pytest.mark.parametrize("image_path", sorted(FIXTURE_DIR.glob("*.jpg")))
def test_fixture_image_identifies(image_path):
    result = identify(image_path)
    assert result.part is not None
    assert result.confidence >= 0.0
```

Drop a new image fixture in `tests/fixtures/images/` (with a matching
MD entry in `tests/fixtures/`) and it is picked up automatically.

### Updating a golden hash

When an algorithmic change legitimately shifts a golden value:

1. Run the test, observe the new hash in the assertion failure.
2. Convince yourself the new hash is correct (the diff is an
   intentional behavioural change, not an accidental one).
3. Update the corresponding `tests/fixtures/*.json` with the new
   value. Commit the update **in the same commit** as the algorithmic
   change so reviewers can correlate cause and effect.

Never update the golden file without re-reading the assertion
context — that is how regressions land.

## Coverage tracking

Coverage tooling (`pytest-cov`) is **deferred**. Rationale:

- At concept stage there is no product code to measure; coverage of
  scaffolding scripts is not informative.
- A premature coverage gate forces contributors to write low-value
  tests to clear a threshold, which trains the wrong habit.

Coverage will be revisited when the pipeline modules land and we have
enough surface to measure meaningfully. That decision will be a
separate task with its own ADR.

## Running the tests

```bash
pytest                            # whole suite
pytest tests/                     # one root
pytest tests/test_foo.py          # one file
pytest tests/test_foo.py::test_bar  # one test
pytest -k "schema"                # name match across the suite
pytest -x                         # stop on first failure
```

The CI workflow at [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
runs the equivalent of `pytest` on every push and PR.

## When tests fail in CI but not locally

The usual suspects, in order of likelihood:

1. **Different Python version.** Local is 3.11, CI tests on 3.11.
   Reproduce locally with `pyenv` or `uv venv --python 3.11`.
2. **Path assumptions.** A test wrote `tests/fixtures/foo.json` (relative
   path) but CI runs from a different cwd. Use `Path(__file__).parent`
   instead of relative strings.
3. **Stale virtualenv.** Local `.venv` has a dep that requirements-dev.txt
   no longer pins. Recreate the venv (`uv venv && uv pip install -r requirements-dev.txt`).
4. **Golden artefact drift.** Platform-specific line endings or
   floating-point rounding can shift hashes. Pin the inputs explicitly;
   never rely on system locale.
