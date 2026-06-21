"""Camera-path async enrichment dispatch — TASK-049 (IDEA-008 Stage 5).

Fire-and-forget background enrichment so the capture loop never blocks on
network I/O — IDEA-007's silent-qty++ promise stays intact. Built on a
single-worker ``ThreadPoolExecutor`` (``max_workers=1``): one worker is
enough at hobbyist cadence and rules out concurrent Nexar requests (no
rate-limit failure mode).

Every outcome — success, unknown-MPN, offline, network error, rate-limit —
writes one line to ``inventory/.embeddings/enrichment.log``. The log is the
receipt; there is no viewfinder verdict and no retry storm. Background
exceptions are caught, logged, and dropped — they never reach the
viewfinder thread.

When enrichment lands (``Enriched``) the dispatcher queues the page-gen job
on the same worker (TASK-050 camera-path chain) via the injected
``page_gen`` callable.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import Enriched, NoEnrichment, enrich

__all__ = ["Dispatcher", "default_log_path"]


def default_log_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent / "inventory" / ".embeddings" / "enrichment.log"
    return Path("inventory") / ".embeddings" / "enrichment.log"


def _describe(result: Any) -> str:
    if isinstance(result, Enriched):
        return "enriched"
    if isinstance(result, NoEnrichment):
        return f"skipped: {result.reason}"
    return f"unknown result: {result!r}"


class Dispatcher:
    """Single-worker background enrichment dispatcher.

    Inject ``enrich_fn`` / ``page_gen`` / ``log_path`` for tests. The
    dispatcher owns one thread; call :meth:`shutdown` to drain it.
    """

    def __init__(
        self,
        *,
        enrich_fn: Callable[..., Any] | None = None,
        page_gen: Callable[[str], Any] | None = None,
        log_path: Path | str | None = None,
        max_workers: int = 1,
    ) -> None:
        self._enrich = enrich_fn or enrich
        self._page_gen = page_gen
        self._log_path = Path(log_path) if log_path is not None else default_log_path()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pl-enrich")

    def dispatch_async(self, part_id: str, *, source: str = "camera") -> Future:
        """Submit ``enrich(part_id)`` to the worker and return immediately.

        Returns the :class:`~concurrent.futures.Future` (mainly for tests to
        await deterministically); the camera path ignores it.
        """
        return self._executor.submit(self._run, part_id, source)

    def _run(self, part_id: str, source: str) -> Any:
        try:
            result = self._enrich(part_id, source=source)
        except Exception as exc:  # noqa: BLE001 — must never reach viewfinder
            self._log(part_id, f"error: {type(exc).__name__}: {exc}")
            return None
        self._log(part_id, _describe(result))
        if self._page_gen is not None and isinstance(result, Enriched):
            try:
                self._page_gen(part_id)
                self._log(part_id, "page-gen queued")
            except Exception as exc:  # noqa: BLE001
                self._log(part_id, f"page-gen error: {type(exc).__name__}: {exc}")
        return result

    def _log(self, part_id: str, message: str) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp}\t{part_id}\t{message}\n")

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)

    def __enter__(self) -> "Dispatcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.shutdown()
