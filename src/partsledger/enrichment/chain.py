"""Skill-path sync enrichment + page-gen chain — TASK-050 (IDEA-008 Stage 6).

Two enrichment cadences share the same ``enrich()`` core:

- **Skill path (sync)** — after ``/inventory-add`` writes a *new* row, the
  maker is already interactive, so :func:`enrich_and_page` runs
  ``enrich(part_id)`` synchronously and then chains ``/inventory-page``
  synchronously (page-gen mechanics owned by TASK-020). A qty-bump against
  an existing row skips both — the enrichment and page already landed on
  first sighting; the skill simply does not call this.

- **Camera path (async)** — the same page-gen chaining happens on the
  background worker, owned by :class:`partsledger.enrichment.dispatch.Dispatcher`.

Page-gen is idempotent: it is skipped when ``inventory/parts/<part-id>.md``
already exists. The actual ``/inventory-page`` invocation is injected
(``page_gen``) so this glue is testable without the skill runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import Enriched, enrich

__all__ = ["ChainResult", "enrich_and_page", "default_part_page_exists"]


@dataclass(frozen=True)
class ChainResult:
    enrichment: Any
    page_generated: bool


def default_part_page_exists(part_id: str) -> bool:
    """True when ``inventory/parts/<part-id>.md`` already exists."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return (parent / "inventory" / "parts" / f"{part_id.lower()}.md").is_file()
    return False


def enrich_and_page(
    part_id: str,
    *,
    source: str = "manual",
    enrich_fn: Callable[..., Any] | None = None,
    page_gen: Callable[[str], Any] | None = None,
    page_exists: Callable[[str], bool] | None = None,
) -> ChainResult:
    """Run enrichment, then chain page-gen unless the page already exists.

    Page-gen runs only when enrichment succeeded (:class:`Enriched`) **and**
    the part page does not yet exist — the idempotent chain from the
    TASK-050 acceptance criteria.
    """
    run_enrich = enrich_fn or enrich
    exists = page_exists or default_part_page_exists

    result = run_enrich(part_id, source=source)

    page_generated = False
    if isinstance(result, Enriched) and page_gen is not None and not exists(part_id):
        page_gen(part_id)
        page_generated = True
    return ChainResult(enrichment=result, page_generated=page_generated)
