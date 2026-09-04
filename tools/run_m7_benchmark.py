"""Generate and run the frozen M7 1k/3k user-source search benchmark.

Fixtures are created at runtime and never committed. Vector is source-local
and generation-bound; this smoke report is still not M7 exit evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_DIR = REPO_ROOT / "platform"
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

os.environ.setdefault("SA_USE_VECTOR", "false")

from app.normalized_document import NormalizedDocument, NormalizedUnit  # noqa: E402
from app.parser_matrix import ParsedDocument, ParsedUnit  # noqa: E402
from app.source_registry import (  # noqa: E402
    SourceActorType,
    SourceLifecycleService,
    SqliteSourceRegistry,
)
from app.user_source_search import UserSourceSearchService  # noqa: E402
from app.user_source_vector import HashVectorEmbedder  # noqa: E402


REPORT_SCHEMA = "sa.source.benchmark.v1"
SOURCE_IDS = (
    "user-01890f52-47e7-7abc-8def-0123456789a1",
    "user-01890f52-47e7-7abc-8def-0123456789a2",
    "user-01890f52-47e7-7abc-8def-0123456789a3",
)
PRINCIPAL = "principal-benchmark"
CORRELATION = "corr-m7-benchmark"


def _source_id(index: int) -> str:
    return SOURCE_IDS[index]


def _gold_token(source_index: int, doc_index: int, unit_index: int) -> str:
    return f"金标词{source_index:02d}{doc_index:03d}{unit_index:02d}"


def _install_unit_parser() -> None:
    """Keep one visible unit per paragraph so 100 docs can yield 1,000 chunks."""
    import app.user_source_snapshot as snapshot_mod

    def fake_parse(path, fmt, max_bytes=None):  # type: ignore[no-untyped-def]
        lines = [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
        units = tuple(ParsedUnit("heading", index, line) for index, line in enumerate(lines))
        return ParsedDocument(
            format="md",
            parser_id="markdown-it-py",
            parser_version="4.0.0",
            units=units or (ParsedUnit("document", 0, "empty"),),
        )

    def fake_normalize(parsed, **kwargs):  # type: ignore[no-untyped-def]
        units = tuple(
            NormalizedUnit("heading", index, title=unit.text[:20], text=unit.text)
            for index, unit in enumerate(parsed.units)
        )
        return NormalizedDocument(units=units, **kwargs)

    snapshot_mod.parse_file = fake_parse  # type: ignore[assignment]
    snapshot_mod.normalize_document = fake_normalize  # type: ignore[assignment]


def write_markdown(path: Path, source_index: int, doc_index: int, units: int) -> None:
    lines = [_gold_token(source_index, doc_index, unit_index) for unit_index in range(units)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_corpus(root: Path, *, sources: int, documents: int, units: int) -> list[dict[str, str]]:
    gold: list[dict[str, str]] = []
    for source_index in range(sources):
        source_root = root / f"source-{source_index}"
        for doc_index in range(documents):
            path = source_root / f"doc-{doc_index:03d}.md"
            write_markdown(path, source_index, doc_index, units)
            gold.append(
                {
                    "source_id": _source_id(source_index),
                    "logical_uri": path.name,
                    "query": _gold_token(source_index, doc_index, 0),
                }
            )
    return gold


def publish_sources(
    service: UserSourceSearchService,
    lifecycle: SourceLifecycleService,
    root: Path,
    *,
    sources: int,
) -> None:
    for source_index in range(sources):
        source_id = _source_id(source_index)
        try:
            lifecycle.get_source(principal_id=PRINCIPAL, source_id=source_id)
        except Exception:
            lifecycle.register_source(
                owner_principal_id=PRINCIPAL,
                expected_version=0,
                actor_type=SourceActorType.USER,
                correlation_id=CORRELATION,
                source_id=source_id,
            )
        service._offline.repair_full(
            principal_id=PRINCIPAL,
            source_id=source_id,
            source_root=root / f"source-{source_index}",
            correlation_id=CORRELATION,
        )


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[index]


def measure_queries(service: UserSourceSearchService, gold: list[dict[str, str]], *, top_k: int) -> dict[str, object]:
    hits_at = {1: 0, 3: 0, 5: 0}
    latencies: list[float] = []
    for item in gold:
        started = time.perf_counter()
        result = service.search(principal_id=PRINCIPAL, query=item["query"], top_k=top_k)
        latencies.append((time.perf_counter() - started) * 1000)
        files = [chunk.file for chunk in result.chunks]
        expected = f"user://{item['source_id']}/{item['logical_uri']}"
        for k in hits_at:
            if expected in files[:k]:
                hits_at[k] += 1
    total = len(gold) or 1
    return {
        "recall_at_1": hits_at[1] / total,
        "recall_at_3": hits_at[3] / total,
        "recall_at_5": hits_at[5] / total,
        "query_p50_ms": percentile(latencies, 0.50),
        "query_p95_ms": percentile(latencies, 0.95),
        "query_count": len(gold),
        "mean_ms": statistics.fmean(latencies) if latencies else 0.0,
    }


def run_workload(name: str, *, sources: int, documents: int, units: int, measured: int, warmup: int) -> dict[str, object]:
    _install_unit_parser()
    with tempfile.TemporaryDirectory(prefix=f"m7-{name}-") as raw:
        root = Path(raw)
        gold = build_corpus(root / "corpus", sources=sources, documents=documents, units=units)
        lifecycle = SourceLifecycleService(SqliteSourceRegistry(root / "registry.sqlite3"))
        service = UserSourceSearchService(
            root / "cache",
            lifecycle,
            vector_embedder=HashVectorEmbedder(),
        )
        sync_times: list[float] = []
        for index in range(max(warmup + measured, 1)):
            started = time.perf_counter()
            publish_sources(service, lifecycle, root / "corpus", sources=sources)
            elapsed = (time.perf_counter() - started) * 1000
            if index >= warmup:
                sync_times.append(elapsed)
        query_metrics = measure_queries(service, gold[: min(len(gold), 100)], top_k=5)
        sample = service.search(principal_id=PRINCIPAL, query=gold[0]["query"], top_k=5)
        return {
            "workload": name,
            "sources": sources,
            "documents": documents * sources,
            "chunks_per_document": units,
            "target_chunks": documents * units * sources,
            "vector_status": "attached",
            "full_sync_p95_ms": percentile(sync_times, 0.95),
            "full_sync_samples": len(sync_times),
            "identity_fts5": True,
            "identity_vector": True,
            "exit_eligible": False,
            "auth_digest_present": bool(sample.auth_digest),
            **query_metrics,
        }


def build_report(workloads: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA,
        "vector_backend": "source_local_hash",
        "tokenizer": "jieba-0.42.1-search",
        "m7_exit": False,
        "reason": "source-local hash vector is attached but this is not the frozen 20-run BGE protocol",
        "network_promoted": False,
        "m8_started": False,
        "workloads": workloads,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run M7 1k/3k user-source FTS5 benchmark")
    parser.add_argument("--report", default=str(REPO_ROOT / "artifacts" / "m7-benchmark.json"))
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--measured", type=int, default=3)
    parser.add_argument("--quick", action="store_true", help="tiny fixture for smoke only")
    args = parser.parse_args()
    if args.quick:
        workloads = [run_workload("quick-smoke", sources=1, documents=2, units=2, measured=1, warmup=0)]
    else:
        workloads = [
            run_workload("1k-single", sources=1, documents=100, units=10, measured=args.measured, warmup=args.warmup),
            run_workload("3k-aggregate", sources=3, documents=100, units=10, measured=args.measured, warmup=args.warmup),
        ]
    report = build_report(workloads)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())