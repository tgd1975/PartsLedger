"""Tests for partsledger.enrichment.dispatch — TASK-049."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from partsledger.enrichment import Enriched, NoEnrichment  # noqa: E402
from partsledger.enrichment.dispatch import Dispatcher  # noqa: E402


def _dispatcher(tmp_path, enrich_fn, **kw):
    return Dispatcher(enrich_fn=enrich_fn, log_path=tmp_path / "enrichment.log", **kw)


def _read_log(tmp_path):
    p = tmp_path / "enrichment.log"
    return p.read_text() if p.is_file() else ""


# ---------------------------------------------------------------------------
# logs one line per outcome


def test_logs_enriched(tmp_path):
    d = _dispatcher(tmp_path, lambda pid, source="camera": Enriched({"mpn": pid}))
    d.dispatch_async("LM358N").result()
    d.shutdown()
    log = _read_log(tmp_path)
    assert "LM358N" in log
    assert "enriched" in log


def test_logs_each_no_enrichment_reason(tmp_path):
    for reason in ("offline", "network_unreachable", "unknown_mpn", "fallback_missed"):
        d = _dispatcher(tmp_path, lambda pid, source="camera", r=reason: NoEnrichment(r))
        d.dispatch_async("X").result()
        d.shutdown()
    log = _read_log(tmp_path)
    for reason in ("offline", "network_unreachable", "unknown_mpn", "fallback_missed"):
        assert reason in log


# ---------------------------------------------------------------------------
# background exceptions never propagate


def test_exception_is_swallowed_and_logged(tmp_path):
    def boom(pid, source="camera"):
        raise RuntimeError("kaboom")

    d = _dispatcher(tmp_path, boom)
    fut = d.dispatch_async("X")
    assert fut.result() is None  # no exception surfaced to the caller
    d.shutdown()
    assert "error" in _read_log(tmp_path)


# ---------------------------------------------------------------------------
# latency: returns immediately


def test_dispatch_returns_fast(tmp_path):
    def slow(pid, source="camera"):
        time.sleep(0.5)
        return Enriched({"mpn": pid})

    d = _dispatcher(tmp_path, slow)
    start = time.monotonic()
    fut = d.dispatch_async("X")
    elapsed = time.monotonic() - start
    assert elapsed < 0.05  # < 50 ms
    fut.result()
    d.shutdown()


# ---------------------------------------------------------------------------
# single worker → serial execution


def test_single_worker_serialises(tmp_path):
    active = {"n": 0, "max": 0}
    lock = threading.Lock()

    def tracked(pid, source="camera"):
        with lock:
            active["n"] += 1
            active["max"] = max(active["max"], active["n"])
        time.sleep(0.02)
        with lock:
            active["n"] -= 1
        return Enriched({"mpn": pid})

    d = _dispatcher(tmp_path, tracked, max_workers=1)
    futs = [d.dispatch_async(f"P{i}") for i in range(5)]
    for f in futs:
        f.result()
    d.shutdown()
    assert active["max"] == 1  # never two at once


# ---------------------------------------------------------------------------
# page-gen chaining + log append/persist


def test_page_gen_queued_on_enriched(tmp_path):
    pages = []
    d = Dispatcher(
        enrich_fn=lambda pid, source="camera": Enriched({"mpn": pid}),
        page_gen=lambda pid: pages.append(pid),
        log_path=tmp_path / "enrichment.log",
    )
    d.dispatch_async("LM358N").result()
    d.shutdown()
    assert pages == ["LM358N"]
    assert "page-gen queued" in _read_log(tmp_path)


def test_log_appends_across_dispatchers(tmp_path):
    d1 = _dispatcher(tmp_path, lambda pid, source="camera": Enriched({"mpn": pid}))
    d1.dispatch_async("A").result()
    d1.shutdown()
    d2 = _dispatcher(tmp_path, lambda pid, source="camera": Enriched({"mpn": pid}))
    d2.dispatch_async("B").result()
    d2.shutdown()
    log = _read_log(tmp_path)
    assert "A" in log and "B" in log
