#!/usr/bin/env python3
"""Unified RAG evaluation runner for the OS/DS/CO test sets.

Metrics:
- Recall@k: share of labeled relevant files found in the top-k results
- Precision@k: share of top-k results that match a labeled relevant file
- F1: harmonic mean of recall and precision
- Latency: mean retrieval time per question

Default mode is offline BM25 (SA_USE_VECTOR=false). Vector/hybrid retrieval is
opt-in via --use-vector so a machine without model caches or network can still
reproduce the 90-question baseline.

Usage:
    python tools/run_evaluation.py
    python tools/run_evaluation.py --courses os,ds -k 1,3,5
    python tools/run_evaluation.py --test-set tools/evaluations/os.json
    python tools/run_evaluation.py --report reports/eval.json
    python tools/run_evaluation.py --smoke
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
KNOWN_COURSES = ("os", "ds", "co")
DEFAULT_TOP_KS = "1,3,5"
DEFAULT_EVAL_DIR = REPO_ROOT / "tools" / "evaluations"

RecallFn = Callable[[str, int], tuple[list[Any], str]]


def parse_top_ks(raw: str) -> list[int]:
    """Parse a comma-separated top-k list into positive integers."""
    values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("top-ks must not be empty")
    if any(value <= 0 for value in values):
        raise ValueError("top-ks must be positive integers")
    return values


def parse_courses(raw: str | None) -> list[str]:
    """Parse a course filter. ``all`` or empty selects the three known courses."""
    if raw is None or raw.strip() == "" or raw.strip().lower() == "all":
        return list(KNOWN_COURSES)
    selected: list[str] = []
    seen: set[str] = set()
    for item in raw.split(","):
        course = item.strip().lower()
        if not course:
            continue
        if course not in KNOWN_COURSES:
            raise ValueError(f"unknown course: {course}")
        if course not in seen:
            selected.append(course)
            seen.add(course)
    if not selected:
        raise ValueError("courses must not be empty")
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RAG evaluation runner")
    parser.add_argument(
        "--test-set",
        default=None,
        help="Single evaluation JSON (question -> related files). Overrides --courses.",
    )
    parser.add_argument(
        "--courses",
        default="all",
        help="Comma-separated courses (os,ds,co) or 'all'. Default: all",
    )
    parser.add_argument(
        "--eval-dir",
        default=None,
        help="Directory of course evaluation JSON files. Default: tools/evaluations",
    )
    parser.add_argument(
        "-k",
        "--top-ks",
        default=DEFAULT_TOP_KS,
        help="Comma-separated top-k list. Default: 1,3,5",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional JSON report path. Keep reports untracked unless promoted.",
    )
    parser.add_argument(
        "--use-vector",
        action="store_true",
        help="Enable optional vector/hybrid retrieval. Default is offline BM25.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Evaluate a small labeled subset per dataset for offline CI.",
    )
    parser.add_argument(
        "--smoke-limit",
        type=int,
        default=2,
        help="Labeled questions kept per dataset in --smoke mode. Default: 2",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def requested_mode(use_vector: bool) -> str:
    return "hybrid" if use_vector else "keyword-only"


def apply_vector_setting(use_vector: bool) -> None:
    """Force the retrieval backend before (or after) app.config is imported."""
    os.environ["SA_USE_VECTOR"] = "true" if use_vector else "false"
    config_mod = sys.modules.get("app.config")
    if config_mod is not None:
        config_mod.USE_VECTOR = use_vector
        config_mod.VECTOR_ENABLED = use_vector


def display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def discover_evaluation_sets(
    repo_root: Path | None = None,
    courses: Iterable[str] | None = None,
    eval_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Find known course evaluation files. Missing files are skipped."""
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    directory = Path(eval_dir) if eval_dir is not None else root / "tools" / "evaluations"
    selected = list(courses) if courses is not None else list(KNOWN_COURSES)
    found: list[dict[str, Any]] = []
    for course in selected:
        path = directory / f"{course}.json"
        if path.is_file():
            found.append({"course": course, "path": path})
    return found


def load_test_set(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"evaluation set must be a JSON object: {path}")
    loaded: dict[str, list[str]] = {}
    for question, files in data.items():
        if not str(question).strip():
            raise ValueError(f"evaluation set contains an empty question: {path}")
        if files is None:
            related: list[str] = []
        elif isinstance(files, list):
            related = [str(item) for item in files]
        else:
            raise ValueError(f"related files must be an array: {path}")
        loaded[str(question)] = related
    return loaded


def limit_smoke_samples(test_set: dict[str, list[str]], limit: int) -> dict[str, list[str]]:
    """Keep the first N labeled questions for a fast smoke run."""
    if limit <= 0:
        raise ValueError("smoke-limit must be a positive integer")
    selected: dict[str, list[str]] = {}
    for question, files in test_set.items():
        if not files:
            continue
        selected[question] = files
        if len(selected) >= limit:
            break
    return selected


def resolve_datasets(
    args: argparse.Namespace,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    if args.test_set:
        path = Path(args.test_set)
        if not path.is_file():
            candidate = root / args.test_set
            if candidate.is_file():
                path = candidate
            else:
                raise FileNotFoundError(f"evaluation set not found: {args.test_set}")
        course = path.stem.lower()
        if course not in KNOWN_COURSES:
            course = "custom"
        return [{"course": course, "path": path}]

    courses = parse_courses(args.courses)
    eval_dir = Path(args.eval_dir) if args.eval_dir else root / "tools" / "evaluations"
    if args.eval_dir and not eval_dir.is_absolute() and not eval_dir.exists():
        candidate = root / args.eval_dir
        if candidate.exists():
            eval_dir = candidate
    found = discover_evaluation_sets(root, courses, eval_dir)
    if not found:
        raise FileNotFoundError(
            f"no evaluation sets found for courses {','.join(courses)} in {eval_dir}"
        )
    return found


def score_sample(
    result_files: list[str],
    relevant_files: list[str],
) -> dict[str, float] | None:
    """Score one labeled question. Unlabeled samples return None."""
    if not relevant_files:
        return None
    hit_files = set(result_files) & set(relevant_files)
    return {
        "recall": len(hit_files) / len(relevant_files),
        "precision": len(hit_files) / max(len(result_files), 1),
    }


def f1_score(recall: float, precision: float) -> float:
    if recall + precision == 0:
        return 0.0
    return 2 * recall * precision / (recall + precision)


def aggregate_metrics(samples: list[dict[str, float]]) -> dict[str, float]:
    if not samples:
        return {
            "recall": 0.0,
            "precision": 0.0,
            "f1": 0.0,
            "avg_latency_ms": 0.0,
            "labeled_questions": 0,
        }
    recall = sum(sample["recall"] for sample in samples) / len(samples)
    precision = sum(sample["precision"] for sample in samples) / len(samples)
    latency = sum(sample["latency_ms"] for sample in samples) / len(samples)
    return {
        "recall": recall,
        "precision": precision,
        "f1": f1_score(recall, precision),
        "avg_latency_ms": latency,
        "labeled_questions": len(samples),
    }


def round_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {
        "recall": round(float(metrics["recall"]), 6),
        "precision": round(float(metrics["precision"]), 6),
        "f1": round(float(metrics["f1"]), 6),
        "avg_latency_ms": round(float(metrics["avg_latency_ms"]), 3),
        "labeled_questions": int(metrics["labeled_questions"]),
    }


def evaluate_test_set(
    test_set: dict[str, list[str]],
    top_ks: list[int],
    recall_fn: RecallFn,
) -> dict[str, Any]:
    """Evaluate one test set. Retrieval runs once per question at max k."""
    max_k = max(top_ks)
    per_k_samples: dict[int, list[dict[str, float]]] = {k: [] for k in top_ks}
    labeled = 0
    observed_mode: str | None = None
    for question, relevant_files in test_set.items():
        started = perf_counter()
        results, mode = recall_fn(question, max_k)
        latency_ms = (perf_counter() - started) * 1000
        observed_mode = mode
        if not relevant_files:
            continue
        labeled += 1
        result_files = [getattr(item, "file") for item in results]
        for k in top_ks:
            sample = score_sample(result_files[:k], relevant_files)
            if sample is None:
                continue
            sample["latency_ms"] = latency_ms
            per_k_samples[k].append(sample)
    return {
        "questions": len(test_set),
        "labeled_questions": labeled,
        "mode": observed_mode,
        "metrics": {
            str(k): round_metrics(aggregate_metrics(per_k_samples[k])) for k in top_ks
        },
    }


def weighted_summary(
    datasets: list[dict[str, Any]],
    top_ks: list[int],
) -> dict[str, Any]:
    summary_metrics: dict[str, dict[str, float]] = {}
    for k in top_ks:
        key = str(k)
        weighted: list[dict[str, float]] = []
        for dataset in datasets:
            metrics = dataset["metrics"][key]
            count = int(metrics["labeled_questions"])
            weighted.extend(
                [
                    {
                        "recall": metrics["recall"],
                        "precision": metrics["precision"],
                        "latency_ms": metrics["avg_latency_ms"],
                    }
                ]
                * count
            )
        summary_metrics[key] = round_metrics(aggregate_metrics(weighted))
    return {
        "questions": sum(int(dataset["questions"]) for dataset in datasets),
        "labeled_questions": sum(int(dataset["labeled_questions"]) for dataset in datasets),
        "metrics": summary_metrics,
    }


def build_report(
    *,
    mode: str,
    use_vector: bool,
    top_ks: list[int],
    datasets: list[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    summary = weighted_summary(datasets, top_ks)
    courses: dict[str, Any] = {}
    for dataset in datasets:
        path = dataset["path"]
        courses[dataset["course"]] = {
            "path": display_path(Path(path), repo_root) if path else "",
            "questions": dataset["questions"],
            "labeled_questions": dataset["labeled_questions"],
            "metrics": dataset["metrics"],
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "use_vector": use_vector,
        "top_ks": list(top_ks),
        "total_questions": summary["questions"],
        "labeled_questions": summary["labeled_questions"],
        "courses": courses,
        "summary": summary,
    }


def format_console(report: dict[str, Any]) -> str:
    lines = [
        f"mode: {report['mode']}  (SA_USE_VECTOR={'true' if report['use_vector'] else 'false'})",
        f"courses: {', '.join(report['courses'].keys()) or '-'}",
        (
            f"questions: {report['total_questions']} "
            f"(labeled: {report['labeled_questions']})"
        ),
        f"topKs: {', '.join(str(k) for k in report['top_ks'])}",
    ]
    header = f"{'k':<3}{'Recall@k':<12}{'Precision@k':<13}{'F1':<8}{'AvgLatency(ms)':<14}"
    divider = "-" * 50
    for course, payload in report["courses"].items():
        lines.extend(
            [
                "",
                f"[{course}] {payload['path']}  ({payload['questions']} questions)",
                header,
                divider,
            ]
        )
        lines.extend(_metric_rows(payload["metrics"], report["top_ks"]))
    lines.extend(
        [
            "",
            (
                f"[summary] {report['summary']['questions']} questions "
                f"(labeled: {report['summary']['labeled_questions']})"
            ),
            header,
            divider,
        ]
    )
    lines.extend(_metric_rows(report["summary"]["metrics"], report["top_ks"]))
    return "\n".join(lines)


def _metric_rows(metrics: dict[str, dict[str, float]], top_ks: list[int]) -> list[str]:
    rows: list[str] = []
    for k in top_ks:
        item = metrics[str(k)]
        if item["labeled_questions"] == 0:
            rows.append(f"{k:<3}(no labeled samples)")
            continue
        rows.append(
            f"{k:<3}{item['recall']:<12.3f}{item['precision']:<13.3f}"
            f"{item['f1']:<8.3f}{item['avg_latency_ms']:<14.1f}"
        )
    return rows


def write_json_report(path: Path, report: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def create_recall_fn(use_vector: bool) -> RecallFn:
    apply_vector_setting(use_vector)
    platform_dir = str(REPO_ROOT / "platform")
    if platform_dir not in sys.path:
        sys.path.insert(0, platform_dir)
    from app.retrieval import MultiRecallService

    service = MultiRecallService()

    def _recall(question: str, top_k: int) -> tuple[list[Any], str]:
        return service.recall(question, top_k=top_k)

    return _recall


def run(
    args: argparse.Namespace,
    *,
    recall_fn: RecallFn | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    top_ks = parse_top_ks(args.top_ks)
    datasets_spec = resolve_datasets(args, root)
    active_recall = recall_fn or create_recall_fn(args.use_vector)
    evaluated: list[dict[str, Any]] = []
    observed_mode: str | None = None
    for spec in datasets_spec:
        test_set = load_test_set(Path(spec["path"]))
        if getattr(args, "smoke", False):
            test_set = limit_smoke_samples(test_set, args.smoke_limit)
        result = evaluate_test_set(test_set, top_ks, active_recall)
        if result["mode"]:
            observed_mode = result["mode"]
        evaluated.append({**spec, **result})
    mode = observed_mode or requested_mode(args.use_vector)
    return build_report(
        mode=mode,
        use_vector=args.use_vector,
        top_ks=top_ks,
        datasets=evaluated,
        repo_root=root,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(format_console(report))
    if args.report:
        report_path = Path(args.report)
        written = write_json_report(report_path, report)
        print(f"\nJSON report: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
