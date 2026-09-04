"""Profile M7 3k-aggregate search stages without changing the frozen protocol.

This is a diagnostic helper. Results are not M7 exit evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_DIR = REPO_ROOT / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

os.environ.setdefault("SA_USE_VECTOR", "false")

from app.source_registry import SourceLifecycleService, SqliteSourceRegistry  # noqa: E402
from app.user_source_search import UserSourceSearchService  # noqa: E402
from app.user_source_vector import HashVectorEmbedder  # noqa: E402
from run_m7_benchmark import (  # noqa: E402
    PRINCIPAL,
    _install_unit_parser,
    build_corpus,
    percentile,
    publish_sources,
)


STAGES = (
    "isolation",
    "cache_lookup",
    "fts5",
    "vector",
    "auth_filter",
    "hydrate",
    "rrf",
)


def _wrap(target: object, name: str, stage: str, sink: dict[str, list[float]]) -> None:
    original = getattr(target, name)

    def wrapped(*args, **kwargs):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            sink[stage].append((time.perf_counter() - started) * 1000)

    setattr(target, name, wrapped)


def _instrument(service: UserSourceSearchService, sink: dict[str, list[float]]) -> None:
    _wrap(service._isolation, "capture_snapshot", "isolation", sink)
    _wrap(service._isolation, "filter_hits", "auth_filter", sink)
    _wrap(service._offline._fts5, "search", "fts5", sink)
    _wrap(service._offline._vector, "search", "vector", sink)
    _wrap(service, "_hydrate", "hydrate", sink)
    import app.user_source_search as search_mod

    original_rrf = search_mod._rrf_fuse

    def wrapped_rrf(*args, **kwargs):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        try:
            return original_rrf(*args, **kwargs)
        finally:
            sink["rrf"].append((time.perf_counter() - started) * 1000)

    search_mod._rrf_fuse = wrapped_rrf  # type: ignore[assignment]


def _summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}
    return {
        "count": len(values),
        "mean_ms": round(statistics.fmean(values), 3),
        "p50_ms": round(percentile(values, 0.50), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
    }


def profile_3k(*, warmup: int, measured: int, query_count: int) -> dict[str, object]:
    _install_unit_parser()
    with tempfile.TemporaryDirectory(prefix="m7-profile-3k-") as raw:
        root = Path(raw)
        gold = build_corpus(root / "corpus", sources=3, documents=100, units=10)
        lifecycle = SourceLifecycleService(SqliteSourceRegistry(root / "registry.sqlite3"))
        service = UserSourceSearchService(
            root / "cache",
            lifecycle,
            vector_embedder=HashVectorEmbedder(),
        )
        started = time.perf_counter()
        publish_sources(service, lifecycle, root / "corpus", sources=3)
        build_ms = (time.perf_counter() - started) * 1000
        needed = warmup + measured
        queries = gold[: min(len(gold), max(query_count, needed))]
        for item in queries[:warmup]:
            service.search(principal_id=PRINCIPAL, query=item["query"], top_k=5)
        sink: dict[str, list[float]] = defaultdict(list)
        _instrument(service, sink)
        latencies: list[float] = []
        for item in queries[warmup:warmup + measured]:
            started = time.perf_counter()
            result = service.search(principal_id=PRINCIPAL, query=item["query"], top_k=5)
            latencies.append((time.perf_counter() - started) * 1000)
            if not result.chunks:
                raise SystemExit("profile query returned no chunks")
        return {
            "workload": "3k-aggregate-profile",
            "vector_backend": "source_local_hash",
            "m7_exit": False,
            "build_ms": round(build_ms, 3),
            "warmup": warmup,
            "measured": len(latencies),
            "query": _summarize(latencies),
            "stages": {stage: _summarize(sink[stage]) for stage in STAGES},
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile M7 3k search stages")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--measured", type=int, default=20)
    parser.add_argument("--query-count", type=int, default=40)
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "artifacts" / "m7-search-profile.json"),
    )
    args = parser.parse_args()
    report = profile_3k(warmup=args.warmup, measured=args.measured, query_count=args.query_count)
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())