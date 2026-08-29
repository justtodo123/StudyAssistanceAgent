"""Blocking M6b offline latency and deterministic-replay benchmark."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import platform as runtime_platform
import re
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from app import config
from app.combined_snapshot import CombinedSnapshotBuilder
from app.llm_client import ModelTurn, ModelUsage, ToolCall, ToolExecutionResult
from app.preview_service import PreviewRequest, PreviewResponse, PreviewService
from app.protocols import JsonObject, SourceType
from app.quiz import QuizService
from app.retrieval import MultiRecallService
from app.review_scheduler import ReviewSchedulerService
from app.snapshot_publisher import CombinedSnapshotPublisher
from app.source_config import SourceLimits, StaticSourceConfig
from app.tool_registry import ToolRegistry
from app.tools.quiz import QuizTool
from app.tools.retrieve import RetrieveTool
from app.tools.review_due import ReviewDueTool


pytestmark = [pytest.mark.m6b, pytest.mark.slow, pytest.mark.m6b_benchmark]
_TOKEN = "preview-token-that-is-at-least-thirty-two-bytes"
_WARM_UP_REQUESTS = 20
_MEASURED_REQUESTS = 200
_CONCURRENCY = 2
_P95_LIMIT_MS = 1_000.0
_EVIDENCE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_WORKLOAD = (
    ("final-only", None, {}),
    (
        "retrieve",
        "retrieve",
        {"question": "Semaphore-extra-benchmark-canary", "course": "os", "top_k": 5},
    ),
    ("quiz-preview", "quiz_preview", {"course": "os", "count": 1}),
    ("review-due", "review_due", {"course": "os"}),
)


@dataclass
class _Conversation:
    workload: str
    tool_name: str | None
    arguments: dict[str, Any]
    results: list[ToolExecutionResult]


class _ScriptedClient:
    """Request-local fake provider that exercises the native tool loop."""

    def __init__(self, request_number: int) -> None:
        self._request_number = request_number
        self._turn = 0

    def new_conversation(self, prompt: str) -> _Conversation:
        workload, tool_name, arguments = _decode_prompt(prompt)
        return _Conversation(workload, tool_name, arguments, [])

    async def count_tokens(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> int:
        del tools, timeout
        return 64 + len(conversation.results) * 16

    async def create_turn(
        self,
        conversation: _Conversation,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        del tools, max_tokens, timeout
        self._turn += 1
        if conversation.tool_name is not None and self._turn == 1:
            return ModelTurn(
                text="",
                tool_calls=(
                    ToolCall(
                        call_id=f"provider-call-{self._request_number}",
                        name=conversation.tool_name,
                        arguments=conversation.arguments,
                    ),
                ),
                stop_reason="tool_use",
                usage=ModelUsage(input_tokens=64, output_tokens=16),
                latency_ms=0.25,
            )
        return ModelTurn(
            text=f"offline benchmark answer: {conversation.workload}",
            tool_calls=(),
            stop_reason="end_turn",
            usage=ModelUsage(
                input_tokens=80 if conversation.tool_name is not None else 64,
                output_tokens=16,
            ),
            latency_ms=0.25,
        )

    def append_tool_result(
        self,
        conversation: _Conversation,
        result: ToolExecutionResult,
    ) -> None:
        conversation.results.append(result)

    async def close(self) -> None:
        return None


class _ReadOnlyReviewRepository:
    def __init__(self) -> None:
        self._entries: dict[str, JsonObject] = {
            "knowledge/os/process.md": {
                "file": "knowledge/os/process.md",
                "course": "os",
                "review_count": 2,
                "last_reviewed": "2020-01-01T00:00:00",
                "next_review": "2020-01-02T00:00:00",
                "interval_days": 1,
                "source_session_id": "benchmark-seed",
            }
        }

    def get(self, file_key: str) -> JsonObject | None:
        value = self._entries.get(file_key)
        return dict(value) if value is not None else None

    def save(self, file_key: str, entry: JsonObject) -> JsonObject:
        del file_key, entry
        raise AssertionError("benchmark preview attempted a review write")

    def all(self) -> dict[str, JsonObject]:
        return {key: dict(value) for key, value in self._entries.items()}

    def find_by_source_session(self, session_id: str) -> JsonObject | None:
        for value in self._entries.values():
            if value.get("source_session_id") == session_id:
                return dict(value)
        return None


def _write_default(root: Path) -> None:
    path = root / "os" / "process.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "tags: [process, isolation]\n"
        "course: os\n"
        "difficulty: basic\n"
        "updated: 2026-08-28\n"
        "---\n\n"
        "# Process\n\n"
        "## Process isolation\n\n"
        "A process owns an independent virtual address space.\n\n"
        "## 经典例题\n\n"
        "**题目：** What does process isolation protect?\n\n"
        "**解答：** It protects one process from another process's address space.\n",
        encoding="utf-8",
    )


def _write_extra(root: Path) -> None:
    path = root / "week-01.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "source_type: human_markdown\n"
        "ingest_status: approved\n"
        "course: os\n"
        "tags: [semaphore]\n"
        "difficulty: basic\n"
        "updated: 2026-08-28\n"
        "---\n\n"
        "## Semaphore extra benchmark\n\n"
        "Semaphore-extra-benchmark-canary coordinates concurrent workers.\n",
        encoding="utf-8",
    )


def _decode_prompt(prompt: str) -> tuple[str, str | None, dict[str, Any]]:
    prefix = "m6b-benchmark:"
    if not prompt.startswith(prefix):
        raise AssertionError("benchmark prompt is not canonical")
    workload = prompt.removeprefix(prefix)
    for name, tool_name, arguments in _WORKLOAD:
        if workload == name:
            return name, tool_name, dict(arguments)
    raise AssertionError("benchmark workload is unknown")


def _workload_digest() -> str:
    encoded = json.dumps(
        _WORKLOAD,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _evidence_id() -> str:
    value = os.getenv("M6B_BENCHMARK_EVIDENCE_ID")
    if value is None:
        return "local-unrecorded"
    if _EVIDENCE_ID_PATTERN.fullmatch(value) is None:
        raise AssertionError("M6B benchmark evidence ID is invalid")
    return value


def _write_report(report: Mapping[str, Any], evidence_id: str) -> None:
    report_path = os.getenv("M6B_BENCHMARK_REPORT")
    if report_path is None:
        return
    if os.getenv("M6B_BENCHMARK_EVIDENCE_ID") is None:
        raise AssertionError("recorded M6B benchmark evidence requires an explicit ID")
    destination = Path(report_path)
    if evidence_id not in destination.name:
        raise AssertionError("M6B benchmark report name must contain its evidence ID")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def test_benchmark_evidence_id_rejects_unsafe_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("M6B_BENCHMARK_EVIDENCE_ID", "unsafe/path")

    with pytest.raises(AssertionError, match="evidence ID is invalid"):
        _evidence_id()


def test_benchmark_report_is_exclusive_and_identity_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_id = "exclusive-create-test"
    destination = tmp_path / f"m6b-offline-preview-benchmark-{evidence_id}.json"
    monkeypatch.setenv("M6B_BENCHMARK_EVIDENCE_ID", evidence_id)
    monkeypatch.setenv("M6B_BENCHMARK_REPORT", str(destination))
    report = {"evidence_id": evidence_id, "schema_version": "test"}

    _write_report(report, _evidence_id())

    assert json.loads(destination.read_text(encoding="utf-8")) == report
    with pytest.raises(FileExistsError):
        _write_report(report, evidence_id)


def _percentile(samples: Sequence[float], percentile: float) -> float:
    ordered = sorted(samples)
    rank = math.ceil(percentile * len(ordered))
    return ordered[max(0, rank - 1)]


def _normalize(response: PreviewResponse) -> dict[str, Any]:
    body = response.model_dump(mode="json")
    normalized_trace: list[dict[str, Any]] = []
    for raw in body["agent_trace"]:
        item = dict(raw)
        item.pop("latency_ms", None)
        item.pop("request_id_hmac", None)
        normalized_trace.append(item)
    body["agent_trace"] = normalized_trace
    return body


def _registry(recall: MultiRecallService) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(RetrieveTool(recall))
    registry.register(QuizTool(QuizService()))
    registry.register(ReviewDueTool(ReviewSchedulerService(_ReadOnlyReviewRepository())))
    return registry


async def _run_requests(
    service: PreviewService,
    *,
    count: int,
    start_number: int,
) -> list[tuple[str, float, PreviewResponse]]:
    queue = asyncio.Queue[tuple[int, tuple[str, str | None, Mapping[str, Any]]]]()
    for offset in range(count):
        await queue.put((start_number + offset, _WORKLOAD[offset % len(_WORKLOAD)]))

    results: list[tuple[str, float, PreviewResponse] | None] = [None] * count

    async def worker() -> None:
        while True:
            try:
                request_number, workload = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            name = workload[0]
            started = time.perf_counter()
            response = await service.run(
                PreviewRequest(prompt=f"m6b-benchmark:{name}", learner_id="benchmark"),
                f"Bearer {_TOKEN}",
            )
            elapsed_ms = (time.perf_counter() - started) * 1_000
            results[request_number - start_number] = (name, elapsed_ms, response)
            queue.task_done()

    await asyncio.gather(*(worker() for _ in range(_CONCURRENCY)))
    assert all(item is not None for item in results)
    return [item for item in results if item is not None]


def test_offline_preview_p95_and_replay_are_blocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "USE_VECTOR", False)
    monkeypatch.setattr(config, "VECTOR_ENABLED", False)
    default_root = tmp_path / "default"
    extra_root = tmp_path / "extra"
    _write_default(default_root)
    _write_extra(extra_root)
    monkeypatch.setattr(config, "KNOWLEDGE_ROOT", default_root)

    source = StaticSourceConfig(
        "benchmark-notes",
        extra_root.resolve(),
        SourceType.HUMAN_MARKDOWN,
    )
    builder = CombinedSnapshotBuilder(
        default_root,
        (source,),
        SourceLimits(),
        strict=True,
    )
    publisher = CombinedSnapshotPublisher(
        tmp_path / "snapshots",
        builder=builder.build,
    )
    snapshot = publisher.publish()
    recall = MultiRecallService(snapshot_provider=publisher.view)

    created = 0

    def client_factory(key: str) -> _ScriptedClient:
        nonlocal created
        assert key == "offline-provider-key"
        created += 1
        return _ScriptedClient(created)

    service = PreviewService(
        token=_TOKEN,
        provider_key="offline-provider-key",
        registry=_registry(recall),
        client_factory=client_factory,
        hmac_key=b"h" * 32,
    )

    async def scenario() -> tuple[
        list[tuple[str, float, PreviewResponse]],
        list[tuple[str, float, PreviewResponse]],
    ]:
        warm = await _run_requests(service, count=_WARM_UP_REQUESTS, start_number=0)
        measured = await _run_requests(
            service,
            count=_MEASURED_REQUESTS,
            start_number=_WARM_UP_REQUESTS,
        )
        return warm, measured

    warm, measured = asyncio.run(scenario())
    assert config.USE_VECTOR is False
    assert config.VECTOR_ENABLED is False
    latencies = [latency for _, latency, _ in measured]
    termination_histogram = Counter(
        response.termination_reason for _, _, response in measured
    )
    by_workload: dict[str, set[str]] = {name: set() for name, _, _ in _WORKLOAD}
    for name, _, response in measured:
        by_workload[name].add(
            json.dumps(
                _normalize(response),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    evidence_id = _evidence_id()
    report = {
        "schema_version": "m6b-offline-preview-benchmark-v2",
        "evidence_id": evidence_id,
        "warm_up_requests": len(warm),
        "measured_requests": len(measured),
        "concurrency": _CONCURRENCY,
        "snapshot_generation": snapshot.generation,
        "workload_digest": _workload_digest(),
        "environment": {
            "os": runtime_platform.platform(),
            "python": runtime_platform.python_version(),
            "processor": runtime_platform.processor() or "unknown",
            "vector_enabled": bool(config.USE_VECTOR or config.VECTOR_ENABLED),
        },
        "latency_ms": {
            "p50": round(_percentile(latencies, 0.50), 3),
            "p95": round(_percentile(latencies, 0.95), 3),
            "p99": round(_percentile(latencies, 0.99), 3),
            "max": round(max(latencies), 3),
        },
        "termination_histogram": dict(sorted(termination_histogram.items())),
        "unexpected_terminations": sum(
            count
            for reason, count in termination_histogram.items()
            if reason != "completed"
        ),
        "deterministic_replay_consistency": all(
            len(values) == 1 for values in by_workload.values()
        ),
    }
    report_digest = hashlib.sha256(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    report["report_digest"] = report_digest
    _write_report(report, evidence_id)

    assert created == _WARM_UP_REQUESTS + _MEASURED_REQUESTS
    assert len(warm) == _WARM_UP_REQUESTS
    assert len(measured) == _MEASURED_REQUESTS
    assert termination_histogram == {"completed": _MEASURED_REQUESTS}
    assert report["unexpected_terminations"] == 0
    assert report["deterministic_replay_consistency"] is True
    assert all(len(values) == 1 for values in by_workload.values())
    assert report["latency_ms"]["p95"] <= _P95_LIMIT_MS
    assert len(snapshot.generation) == 64
    assert len(report["workload_digest"]) == 64
    assert len(report_digest) == 64
