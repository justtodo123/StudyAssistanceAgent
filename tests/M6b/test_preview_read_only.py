"""M6b invariants for production read-only tools and retrieval scope."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import pytest

from app.combined_snapshot import CombinedSnapshotBuilder
from app.learning_store import ReviewHistoryRepositoryAdapter, SqliteLearningStore
from app.llm_client import ModelTurn, ModelUsage, ToolCall, ToolExecutionResult
from app.models import StudySessionCreateRequest
from app.preview_service import PreviewRequest, PreviewService
from app.protocols import SourceType
from app.qa import QaService
from app.quiz import QuizService
from app.retrieval import MultiRecallService, RetrievalScope
from app.review_scheduler import ReviewSchedulerService
from app.source_config import SourceLimits, StaticSourceConfig
from app.study_session import StudySessionService
from app.tool_registry import ToolRegistry
from app.tools.quiz import QuizTool
from app.tools.retrieve import RetrieveTool
from app.tools.review_due import ReviewDueTool
from tests.M5b.helpers import FakeQuizService, FakeReviewScheduler


pytestmark = pytest.mark.m6b
_TOKEN = "preview-token-that-is-at-least-thirty-two-bytes"
_TABLES = ("answer_attempts", "review_history", "study_sessions")


@dataclass(frozen=True)
class _DatabaseState:
    dump: str
    digest: str
    counts: dict[str, int]
    data_version: int
    observer_total_changes: int


@dataclass
class _Conversation:
    results: list[ToolExecutionResult]


class _ToolClient:
    def __init__(self, tool_name: str, arguments: Mapping[str, Any]) -> None:
        self._tool_name = tool_name
        self._arguments = dict(arguments)
        self._turn = 0
        self.conversation: _Conversation | None = None

    def new_conversation(self, prompt: str) -> _Conversation:
        del prompt
        self.conversation = _Conversation([])
        return self.conversation

    async def count_tokens(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> int:
        del conversation, tools, timeout
        return 1

    async def create_turn(
        self,
        conversation: Any,
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        timeout: float,
    ) -> ModelTurn:
        del conversation, tools, max_tokens, timeout
        self._turn += 1
        if self._turn == 1:
            return ModelTurn(
                text="",
                tool_calls=(
                    ToolCall("provider-call-canary", self._tool_name, self._arguments),
                ),
                stop_reason="tool_use",
                usage=ModelUsage(input_tokens=1, output_tokens=1),
                latency_ms=1.0,
            )
        return ModelTurn(
            text="safe final answer",
            tool_calls=(),
            stop_reason="end_turn",
            usage=ModelUsage(input_tokens=1, output_tokens=1),
            latency_ms=1.0,
        )

    def append_tool_result(
        self,
        conversation: _Conversation,
        result: ToolExecutionResult,
    ) -> None:
        conversation.results.append(result)

    async def close(self) -> None:
        return None


def _write_default(root: Path) -> None:
    path = root / "os" / "process.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "tags: [process]\n"
        "course: os\n"
        "difficulty: basic\n"
        "updated: 2026-08-28\n"
        "---\n\n"
        "# Process\n\n"
        "## Process isolation\n\n"
        "A process owns an independent virtual address space.\n",
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
        "## Semaphore extra canary\n\n"
        "Semaphore-extra-scope-canary coordinates concurrent workers.\n",
        encoding="utf-8",
    )


def _recall(tmp_path: Path, seen_scopes: list[RetrievalScope] | None = None) -> MultiRecallService:
    default_root = tmp_path / "default"
    extra_root = tmp_path / "extra"
    _write_default(default_root)
    _write_extra(extra_root)
    source = StaticSourceConfig(
        "notes-1",
        extra_root.resolve(),
        SourceType.HUMAN_MARKDOWN,
    )
    snapshot = CombinedSnapshotBuilder(
        default_root,
        (source,),
        SourceLimits(),
        strict=True,
    ).build()

    def provider(scope: RetrievalScope):
        if seen_scopes is not None:
            seen_scopes.append(scope)
        return snapshot.view(scope)

    return MultiRecallService(snapshot_provider=provider)


def _seed(store: SqliteLearningStore) -> None:
    store.save(
        {
            "session_id": "seed-session",
            "course": "os",
            "topic": "process",
            "state": "awaiting_answer",
            "score": None,
            "created_at": "2026-08-28T08:00:00",
            "updated_at": "2026-08-28T08:01:00",
            "answer_records": [
                {
                    "question_id": "q1",
                    "attempt_count": 1,
                    "answer_normalized": "seed-answer",
                    "correct": False,
                    "feedback": "seed-feedback",
                    "created_at": "2026-08-28T08:01:00",
                }
            ],
        }
    )
    store.save_review(
        "knowledge/os/process.md",
        {
            "file": "knowledge/os/process.md",
            "course": "os",
            "review_count": 2,
            "last_reviewed": "2020-01-01T00:00:00",
            "next_review": "2020-01-02T00:00:00",
            "interval_days": 1,
            "source_session_id": "seed-session",
        },
    )


def _database_state(observer: sqlite3.Connection) -> _DatabaseState:
    dump = "\n".join(observer.iterdump())
    counts = {
        table: int(observer.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in _TABLES
    }
    data_version = int(observer.execute("PRAGMA data_version").fetchone()[0])
    return _DatabaseState(
        dump=dump,
        digest=hashlib.sha256(dump.encode("utf-8")).hexdigest(),
        counts=counts,
        data_version=data_version,
        observer_total_changes=observer.total_changes,
    )


def _registry(
    recall: MultiRecallService,
    quiz: QuizService,
    scheduler: ReviewSchedulerService,
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(RetrieveTool(recall))
    registry.register(QuizTool(quiz))
    registry.register(ReviewDueTool(scheduler))
    return registry


def _run_preview(
    registry: ToolRegistry,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> tuple[Any, _ToolClient]:
    client = _ToolClient(tool_name, arguments)
    service = PreviewService(
        token=_TOKEN,
        provider_key="offline-provider-key",
        registry=registry,
        client_factory=lambda key: client,
        hmac_key=b"h" * 32,
    )
    result = asyncio.run(
        service.run(
            PreviewRequest(prompt="private prompt canary", learner_id="learner"),
            f"Bearer {_TOKEN}",
        )
    )
    return result, client


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        pytest.param(
            "retrieve",
            {"question": "Semaphore-extra-scope-canary", "course": "os"},
            id="retrieve",
        ),
        pytest.param("quiz_preview", {"course": "os", "count": 1}, id="quiz-preview"),
        pytest.param("review_due", {"course": "os"}, id="review-due"),
    ],
)
def test_production_preview_tool_preserves_seeded_learning_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> None:
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    _seed(store)
    observer = sqlite3.connect(str(store.db_path))
    observer.execute("PRAGMA query_only=ON")
    before = _database_state(observer)
    connection_deltas: list[int] = []
    original_connect = store._connect

    @contextmanager
    def audited_connect() -> Iterator[sqlite3.Connection]:
        with original_connect() as connection:
            started = connection.total_changes
            yield connection
            connection_deltas.append(connection.total_changes - started)

    monkeypatch.setattr(store, "_connect", audited_connect)
    monkeypatch.setattr(
        SqliteLearningStore,
        "save",
        lambda *args, **kwargs: pytest.fail("preview attempted a session write"),
    )
    monkeypatch.setattr(
        SqliteLearningStore,
        "save_review",
        lambda *args, **kwargs: pytest.fail("preview attempted a review write"),
    )
    monkeypatch.setattr(
        SqliteLearningStore,
        "migrate_review_history",
        lambda *args, **kwargs: pytest.fail("preview attempted a migration write"),
    )

    recall = _recall(tmp_path)
    quiz = QuizService()
    scheduler = ReviewSchedulerService(ReviewHistoryRepositoryAdapter(store))
    result, client = _run_preview(_registry(recall, quiz, scheduler), tool_name, arguments)
    after = _database_state(observer)
    observer.close()

    assert result.status == "completed"
    assert result.termination_reason == "completed"
    assert client.conversation is not None
    assert len(client.conversation.results) == 1
    assert client.conversation.results[0].is_error is False
    assert client.conversation.results[0].content
    assert before.dump == after.dump
    assert before.digest == after.digest
    assert before.counts == after.counts == {
        "answer_attempts": 1,
        "review_history": 1,
        "study_sessions": 1,
    }
    assert before.data_version == after.data_version
    assert before.observer_total_changes == after.observer_total_changes == 0
    assert all(delta == 0 for delta in connection_deltas)


def test_preview_failure_path_preserves_seeded_learning_store(tmp_path: Path) -> None:
    store = SqliteLearningStore(tmp_path / "learning.sqlite3")
    _seed(store)
    observer = sqlite3.connect(str(store.db_path))
    observer.execute("PRAGMA query_only=ON")
    before = _database_state(observer)
    recall = _recall(tmp_path)
    scheduler = ReviewSchedulerService(ReviewHistoryRepositoryAdapter(store))

    result, client = _run_preview(
        _registry(recall, QuizService(), scheduler),
        "retrieve",
        {"unexpected": "invalid-arguments-canary"},
    )
    after = _database_state(observer)
    observer.close()

    assert result.status == "terminated"
    assert result.termination_reason == "invalid_tool_arguments"
    assert client.conversation is not None
    assert client.conversation.results == []
    assert before == after


def test_preview_sees_extras_but_formal_session_remains_default_only(
    tmp_path: Path,
) -> None:
    seen_scopes: list[RetrievalScope] = []
    recall = _recall(tmp_path, seen_scopes)
    preview_registry = ToolRegistry()
    preview_registry.register(RetrieveTool(recall))

    preview, client = _run_preview(
        preview_registry,
        "retrieve",
        {"question": "Semaphore-extra-scope-canary", "course": "os", "top_k": 5},
    )
    formal = StudySessionService(
        qa_service=QaService(recall, scope=RetrievalScope.DEFAULT_ONLY),
        quiz_service=FakeQuizService(),
        review_scheduler=FakeReviewScheduler(),
    ).create(
        StudySessionCreateRequest(
            topic="Semaphore-extra-scope-canary",
            course="os",
            question_count=1,
            use_llm=False,
        )
    )

    assert preview.status == "completed"
    assert client.conversation is not None
    replay = json.loads(client.conversation.results[0].content)
    assert any(
        item["source"]["logical_uri"] == "week-01.md"
        for item in replay["data"]["results"]
    )
    assert not any(source.file.startswith("extra://") for source in formal.sources)
    assert all(source.file.startswith("knowledge/") for source in formal.sources)
    assert seen_scopes == [
        RetrievalScope.DEFAULT_PLUS_EXTRAS,
        RetrievalScope.DEFAULT_ONLY,
    ]
