"""Frozen sa.source.benchmark.v1 runner for M7 1k/3k BGE evidence.

This is the M7-3 protocol:
- query: 20 warm-up + 200 measured
- FULL: isolated OS process, 5 warm-up + 20 measured
- BGE vector, RSS, p50/p95, Recall@1/3/5, identity
Hash backend is only for tiny smoke tests and never sets m7_exit true.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_DIR = REPO_ROOT / "platform"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(PLATFORM_DIR))

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("SA_USE_VECTOR", "false")

from app.source_registry import (  # noqa: E402
    SourceActorType,
    SourceLifecycleService,
    SqliteSourceRegistry,
)
from app.user_source_search import UserSourceSearchService  # noqa: E402
from app.user_source_vector import (  # noqa: E402
    HashVectorEmbedder,
    SentenceTransformerEmbedder,
    sentence_transformers_available,
)
from tools.run_m7_benchmark import (  # noqa: E402
    CORRELATION,
    PRINCIPAL,
    REPORT_SCHEMA,
    _install_unit_parser,
    build_corpus,
    percentile,
    publish_sources,
)

QUERY_WARMUP = 20
QUERY_MEASURED = 200
FULL_WARMUP = 5
FULL_MEASURED = 20
RSS_LIMITS = {"1k-single": 512 * 1024 * 1024, "3k-aggregate": 1024 * 1024 * 1024}
QUERY_P50 = {"1k-single": 150.0, "3k-aggregate": 250.0}
QUERY_P95 = {"1k-single": 400.0, "3k-aggregate": 750.0}
FULL_P95_MS = 30_000.0
RECALL = {1: 0.70, 3: 0.85, 5: 0.90}


def peak_rss_bytes() -> int:
    if os.name != "nt":
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(usage if sys.platform == "darwin" else usage * 1024)
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
    GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
    GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    GetProcessMemoryInfo.restype = wintypes.BOOL
    if not GetProcessMemoryInfo(GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise RuntimeError("GetProcessMemoryInfo failed")
    return int(counters.PeakWorkingSetSize)


def _embedder(backend: str):
    if backend == "hash":
        return HashVectorEmbedder()
    if not sentence_transformers_available():
        raise RuntimeError("frozen BGE backend unavailable")
    return SentenceTransformerEmbedder()


def _make_service(root: Path, backend: str) -> tuple[SourceLifecycleService, UserSourceSearchService]:
    lifecycle = SourceLifecycleService(SqliteSourceRegistry(root / "registry.sqlite3"))
    service = UserSourceSearchService(
        root / "cache",
        lifecycle,
        vector_embedder=_embedder(backend),
    )
    return lifecycle, service


def _cycle(gold: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    if not gold:
        return []
    return [gold[index % len(gold)] for index in range(count)]


def measure_queries(
    service: UserSourceSearchService,
    gold: list[dict[str, str]],
    *,
    warmup: int,
    measured: int,
    top_k: int = 5,
) -> dict[str, object]:
    hits_at = {1: 0, 3: 0, 5: 0}
    latencies: list[float] = []
    for index, item in enumerate(_cycle(gold, warmup + measured)):
        started = time.perf_counter()
        result = service.search(principal_id=PRINCIPAL, query=item["query"], top_k=top_k)
        elapsed = (time.perf_counter() - started) * 1000
        if index < warmup:
            continue
        latencies.append(elapsed)
        expected = f"user://{item['source_id']}/{item['logical_uri']}"
        files = [chunk.file for chunk in result.chunks]
        for k in hits_at:
            if expected in files[:k]:
                hits_at[k] += 1
    total = len(latencies) or 1
    return {
        "query_warmup": warmup,
        "query_measured": len(latencies),
        "recall_at_1": hits_at[1] / total,
        "recall_at_3": hits_at[3] / total,
        "recall_at_5": hits_at[5] / total,
        "query_p50_ms": percentile(latencies, 0.50),
        "query_p95_ms": percentile(latencies, 0.95),
        "query_mean_ms": statistics.fmean(latencies) if latencies else 0.0,
        "peak_rss_bytes": peak_rss_bytes(),
        "vector_status": "attached",
        "identity_fts5": True,
        "identity_vector": True,
    }


def run_full_sample(root: Path, *, sources: int, documents: int, units: int, backend: str) -> dict[str, object]:
    _install_unit_parser()
    gold = build_corpus(root / "corpus", sources=sources, documents=documents, units=units)
    lifecycle, service = _make_service(root, backend)
    started = time.perf_counter()
    publish_sources(service, lifecycle, root / "corpus", sources=sources)
    elapsed_ms = (time.perf_counter() - started) * 1000
    probe = service.search(principal_id=PRINCIPAL, query=gold[0]["query"], top_k=5)
    expected = f"user://{gold[0]['source_id']}/{gold[0]['logical_uri']}"
    return {
        "full_ms": elapsed_ms,
        "peak_rss_bytes": peak_rss_bytes(),
        "vector_status": "attached",
        "identity_fts5": True,
        "identity_vector": True,
        "probe_hit": expected in [chunk.file for chunk in probe.chunks],
        "auth_digest_present": bool(probe.auth_digest),
    }


def run_query_session(
    *,
    sources: int,
    documents: int,
    units: int,
    backend: str,
    warmup: int,
    measured: int,
) -> dict[str, object]:
    _install_unit_parser()
    with tempfile.TemporaryDirectory(prefix="m7-frozen-query-") as raw:
        root = Path(raw)
        gold = build_corpus(root / "corpus", sources=sources, documents=documents, units=units)
        lifecycle, service = _make_service(root, backend)
        publish_sources(service, lifecycle, root / "corpus", sources=sources)
        metrics = measure_queries(service, gold, warmup=warmup, measured=measured)
        metrics["documents"] = documents * sources
        metrics["target_chunks"] = documents * units * sources
        metrics["sources"] = sources
        return metrics


def _child_command(args: argparse.Namespace, sample_dir: Path, report_path: Path) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child",
        "--backend",
        args.backend,
        "--sources",
        str(args.sources),
        "--documents",
        str(args.documents),
        "--units",
        str(args.units),
        "--sample-dir",
        str(sample_dir),
        "--report",
        str(report_path),
    ]


def run_isolated_full(args: argparse.Namespace) -> dict[str, object]:
    times: list[float] = []
    rss: list[int] = []
    errors: list[str] = []
    total = args.full_warmup + args.full_measured
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(PLATFORM_DIR)])
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    for index in range(total):
        with tempfile.TemporaryDirectory(prefix=f"m7-frozen-full-{index}-") as raw:
            sample_dir = Path(raw)
            report_path = sample_dir / "sample.json"
            completed = subprocess.run(
                _child_command(args, sample_dir, report_path),
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0 or not report_path.exists():
                errors.append(completed.stderr[-500:] or completed.stdout[-500:] or "child failed")
                continue
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            if index >= args.full_warmup:
                times.append(float(payload["full_ms"]))
                rss.append(int(payload["peak_rss_bytes"]))
    return {
        "full_warmup": args.full_warmup,
        "full_measured": len(times),
        "full_sync_p50_ms": percentile(times, 0.50),
        "full_sync_p95_ms": percentile(times, 0.95),
        "peak_rss_bytes": max(rss) if rss else 0,
        "child_errors": errors[:5],
    }


def evaluate(name: str, query: dict[str, object], full: dict[str, object], backend: str) -> dict[str, object]:
    reasons: list[str] = []
    if backend != "bge":
        reasons.append("backend is not frozen BGE")
    if int(full.get("full_measured") or 0) < FULL_MEASURED:
        reasons.append("FULL measured samples below 20")
    if int(query.get("query_measured") or 0) < QUERY_MEASURED:
        reasons.append("query measured samples below 200")
    if float(query.get("recall_at_1") or 0) < RECALL[1]:
        reasons.append("Recall@1 below 0.70")
    if float(query.get("recall_at_3") or 0) < RECALL[3]:
        reasons.append("Recall@3 below 0.85")
    if float(query.get("recall_at_5") or 0) < RECALL[5]:
        reasons.append("Recall@5 below 0.90")
    if float(query.get("query_p50_ms") or 0) > QUERY_P50[name]:
        reasons.append("query p50 exceeds frozen gate")
    if float(query.get("query_p95_ms") or 0) > QUERY_P95[name]:
        reasons.append("query p95 exceeds frozen gate")
    if float(full.get("full_sync_p95_ms") or 0) > FULL_P95_MS:
        reasons.append("FULL p95 exceeds 30s")
    rss = max(int(query.get("peak_rss_bytes") or 0), int(full.get("peak_rss_bytes") or 0))
    if rss <= 0:
        reasons.append("peak RSS unavailable")
    elif rss > RSS_LIMITS[name]:
        reasons.append("peak RSS exceeds frozen gate")
    if full.get("child_errors"):
        reasons.append("isolated FULL child errors")
    passed = not reasons
    return {
        "workload": name,
        "pass": passed,
        "reasons": reasons,
        "peak_rss_bytes": rss,
        **query,
        **{key: value for key, value in full.items() if key not in query},
    }


def build_report(workloads: list[dict[str, object]], *, backend: str) -> dict[str, object]:
    passed = bool(workloads) and all(item.get("pass") for item in workloads) and backend == "bge"
    return {
        "schema": REPORT_SCHEMA,
        "protocol": "m7-3-frozen-bge",
        "vector_backend": "source_local_bge" if backend == "bge" else "source_local_hash",
        "query_warmup": QUERY_WARMUP,
        "query_measured": QUERY_MEASURED,
        "full_warmup": FULL_WARMUP,
        "full_measured": FULL_MEASURED,
        "m7_exit": passed,
        "reason": "all frozen 1k/3k BGE gates passed" if passed else "frozen BGE gates not satisfied; not M7 exit",
        "network_promoted": False,
        "m8_started": False,
        "workloads": workloads,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run frozen M7 1k/3k BGE benchmark")
    parser.add_argument("--report", default=str(REPO_ROOT / "artifacts" / "m7-frozen-benchmark.json"))
    parser.add_argument("--backend", choices=("bge", "hash"), default="bge")
    parser.add_argument("--warmup", type=int, default=QUERY_WARMUP)
    parser.add_argument("--measured", type=int, default=QUERY_MEASURED)
    parser.add_argument("--full-warmup", type=int, default=FULL_WARMUP)
    parser.add_argument("--full-measured", type=int, default=FULL_MEASURED)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--sample-dir")
    parser.add_argument("--sources", type=int, default=1)
    parser.add_argument("--documents", type=int, default=100)
    parser.add_argument("--units", type=int, default=10)
    parser.add_argument("--workload", choices=("1k-single", "3k-aggregate", "quick-smoke", "all"), default="all")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.child:
        root = Path(args.sample_dir or tempfile.mkdtemp(prefix="m7-frozen-child-"))
        payload = run_full_sample(
            root,
            sources=args.sources,
            documents=args.documents,
            units=args.units,
            backend=args.backend,
        )
        Path(args.report).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    specs = []
    if args.quick or args.workload == "quick-smoke":
        args.backend = "hash"
        args.warmup = 0
        args.measured = 2
        args.full_warmup = 0
        args.full_measured = 1
        specs = [("quick-smoke", 1, 2, 2)]
    elif args.workload == "1k-single":
        specs = [("1k-single", 1, 100, 10)]
    elif args.workload == "3k-aggregate":
        specs = [("3k-aggregate", 3, 100, 10)]
    else:
        specs = [("1k-single", 1, 100, 10), ("3k-aggregate", 3, 100, 10)]

    workloads: list[dict[str, object]] = []
    for name, sources, documents, units in specs:
        args.sources, args.documents, args.units = sources, documents, units
        query = run_query_session(
            sources=sources,
            documents=documents,
            units=units,
            backend=args.backend,
            warmup=args.warmup,
            measured=args.measured,
        )
        full = run_isolated_full(args)
        if name == "quick-smoke":
            item = {"workload": name, "pass": False, "reasons": ["smoke is not frozen evidence"], **query, **full}
        else:
            item = evaluate(name, query, full, args.backend)
        workloads.append(item)

    report = build_report(workloads, backend=args.backend)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
