"""M6a contract tests for the harness protocol layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.models import StudySessionAnswerRequest, StudySessionCreateRequest
from app.protocols import (
    LearningStateRepository,
    ProtocolValidationError,
    RetrievalIndex,
    RetrievalSnapshot,
    RetrievalSnapshotWriter,
    ReviewRepository,
    Runner,
    RunnerContext,
    RunnerEvent,
    RunnerEventType,
    RunnerResult,
    RunnerSnapshot,
    RunnerStatus,
    SideEffect,
    Source,
    SourceChunk,
    SourceDescriptor,
    SourceIdentity,
    SourceType,
    ToolCapability,
    ToolContext,
    ToolError,
    ToolResult,
    ToolSpec,
    logical_chunk_id,
    logical_document_id,
    normalize_logical_uri,
    validate_source_id,
    validate_source_snapshot,
)
from app.learning_store import ReviewHistoryRepositoryAdapter, SqliteLearningStore
from tests.M5b.helpers import make_service


@dataclass
class _MemorySource:
    descriptor: SourceDescriptor
    chunks: tuple[SourceChunk, ...]

    def describe(self) -> SourceDescriptor:
        return self.descriptor

    def iter_chunks(self):
        return iter(self.chunks)


class _MemoryIndex:
    def __init__(self, chunks: list[SourceChunk]) -> None:
        self.chunks = chunks
        self._generation = "g1"

    @property
    def generation(self) -> str:
        return self._generation

    def search(self, query: str, top_k: int = 5) -> list[SourceChunk]:
        return [chunk for chunk in self.chunks if query in chunk.content][:top_k]


class _MemoryRunner:
    def __init__(self) -> None:
        self._snapshots: dict[str, RunnerSnapshot] = {}

    def start(self, context: RunnerContext) -> RunnerResult:
        run_id = f"run-{len(self._snapshots) + 1}"
        status = RunnerStatus.CANCELLED if context.cancelled else RunnerStatus.WAITING
        snapshot = RunnerSnapshot(run_id=run_id, status=status)
        self._snapshots[run_id] = snapshot
        return RunnerResult(snapshot=snapshot)

    def get(self, context: RunnerContext, run_id: str) -> RunnerResult:
        return RunnerResult(snapshot=self._snapshots[run_id])

    def resume(self, context: RunnerContext, run_id: str) -> RunnerResult:
        snapshot = self._snapshots[run_id]
        if context.cancelled:
            cancelled = RunnerSnapshot(
                run_id=run_id,
                status=RunnerStatus.CANCELLED,
                revision=snapshot.revision + 1,
            )
            self._snapshots[run_id] = cancelled
            return RunnerResult(snapshot=cancelled)
        if snapshot.status in {RunnerStatus.COMPLETED, RunnerStatus.FAILED, RunnerStatus.CANCELLED}:
            return RunnerResult(
                snapshot=snapshot,
                error=ToolError("RUN_TERMINAL", "The run is already terminal."),
            )
        resumed = RunnerSnapshot(
            run_id=run_id,
            status=RunnerStatus.RUNNING,
            revision=snapshot.revision + 1,
        )
        self._snapshots[run_id] = resumed
        return RunnerResult(snapshot=resumed)

    def step(self, context: RunnerContext, run_id: str, event: RunnerEvent) -> RunnerResult:
        snapshot = self._snapshots[run_id]
        if snapshot.status in {RunnerStatus.COMPLETED, RunnerStatus.FAILED, RunnerStatus.CANCELLED}:
            return RunnerResult(
                snapshot=snapshot,
                error=ToolError("RUN_TERMINAL", "The run is already terminal."),
            )
        if context.cancelled or event.type is RunnerEventType.CANCEL:
            status = RunnerStatus.CANCELLED
        elif event.type is RunnerEventType.FAIL:
            status = RunnerStatus.FAILED
        elif event.type is RunnerEventType.COMPLETE:
            status = RunnerStatus.COMPLETED
        else:
            status = RunnerStatus.WAITING
        next_snapshot = RunnerSnapshot(
            run_id=run_id,
            status=status,
            revision=snapshot.revision + 1,
            state={"last_event": event.type.value},
        )
        self._snapshots[run_id] = next_snapshot
        error = ToolError("RUN_FAILED", "The run failed.") if status is RunnerStatus.FAILED else None
        return RunnerResult(snapshot=next_snapshot, output=event.payload, error=error)


@pytest.mark.m6a
class TestSourceIdentityContract:
    def test_document_identity_is_stable_across_logical_separators(self):
        first = SourceIdentity("reference-pack", "os/deadlock.md")
        second = SourceIdentity("reference-pack", "os\\deadlock.md")

        assert first.logical_uri == "os/deadlock.md"
        assert first.document_id == second.document_id
        assert first.document_id == logical_document_id("reference-pack", "os/deadlock.md")
        assert len(first.document_id) == 32

    def test_default_pack_is_an_allowed_logical_identity(self):
        identity = SourceIdentity("knowledge-pack", "os/deadlock.md")

        assert identity.document_id == logical_document_id("knowledge-pack", "os/deadlock.md")
        assert validate_source_id("knowledge-pack", allow_default=True) == "knowledge-pack"

    @pytest.mark.parametrize(
        "logical_uri",
        [
            "C:/private/deadlock.md",
            "C:\\private\\deadlock.md",
            "\\\\server\\share\\deadlock.md",
            "/private/deadlock.md",
            "../os/deadlock.md",
            "os/../deadlock.md",
            "os/deadlock.txt",
        ],
    )
    def test_logical_uri_rejects_host_and_traversal_paths(self, logical_uri):
        with pytest.raises(ProtocolValidationError):
            normalize_logical_uri(logical_uri)

    @pytest.mark.parametrize("source_id", ["knowledge-pack", "crawler-candidates", "user-notes"])
    def test_reserved_source_namespace_requires_explicit_default_allowance(self, source_id):
        with pytest.raises(ProtocolValidationError):
            validate_source_id(source_id)

    def test_chunk_identity_changes_only_with_its_declared_inputs(self):
        identity = SourceIdentity("reference-pack", "os/deadlock.md")
        first = SourceChunk(identity=identity, chunk_key="conditions", content="content")
        equivalent = SourceChunk(identity=identity, chunk_key="conditions", content="updated content")
        changed_schema = SourceChunk(
            identity=identity,
            chunk_key="conditions",
            content="content",
            chunk_schema="sa.chunk.markdown-h2.v2",
        )

        assert first.chunk_id == equivalent.chunk_id
        assert first.chunk_id != changed_schema.chunk_id
        assert first.chunk_id == logical_chunk_id(identity.document_id, "conditions")

    def test_source_protocol_exposes_only_complete_snapshot_metadata(self):
        identity = SourceIdentity("reference-pack", "os/deadlock.md")
        source = _MemorySource(
            descriptor=SourceDescriptor(
                source_id="reference-pack",
                source_type=SourceType.HUMAN_MARKDOWN,
                revision="r1",
                fingerprint="f1",
                generation="g1",
            ),
            chunks=(SourceChunk(identity=identity, chunk_key="root", content="deadlock"),),
        )

        assert isinstance(source, Source)
        assert validate_source_snapshot(source).source_id == "reference-pack"
        assert [chunk.identity.logical_uri for chunk in source.iter_chunks()] == ["os/deadlock.md"]

    def test_source_snapshot_rejects_chunks_in_a_different_namespace(self):
        source = _MemorySource(
            descriptor=SourceDescriptor(
                source_id="reference-pack",
                source_type=SourceType.HUMAN_MARKDOWN,
                revision="r1",
                fingerprint="f1",
                generation="g1",
            ),
            chunks=(
                SourceChunk(
                    identity=SourceIdentity("another-pack", "os/deadlock.md"),
                    chunk_key="root",
                    content="deadlock",
                ),
            ),
        )

        with pytest.raises(ProtocolValidationError, match="namespace"):
            validate_source_snapshot(source)


@pytest.mark.m6a
class TestResponsibilityContracts:
    def test_existing_sqlite_store_satisfies_learning_state_contract(self, tmp_path):
        store = SqliteLearningStore(tmp_path / "learning.sqlite3")

        assert isinstance(store, LearningStateRepository)
        store.save({"session_id": "session-1", "state": "created"})
        assert store.get("session-1") == {"session_id": "session-1", "state": "created"}

    def test_existing_review_adapter_satisfies_review_contract(self, tmp_path):
        repository = ReviewHistoryRepositoryAdapter(SqliteLearningStore(tmp_path / "learning.sqlite3"))

        assert isinstance(repository, ReviewRepository)
        saved = repository.save("knowledge/os/deadlock.md", {"review_count": 1})
        assert saved["review_count"] == 1
        assert repository.get("knowledge/os/deadlock.md") is not None

    def test_retrieval_contract_is_separate_from_learning_state(self):
        chunk = SourceChunk(
            identity=SourceIdentity("reference-pack", "os/deadlock.md"),
            chunk_key="root",
            content="deadlock conditions",
        )
        index = _MemoryIndex([chunk])

        assert isinstance(index, RetrievalIndex)
        assert index.search("deadlock") == [chunk]
        snapshot = RetrievalSnapshot(generation="g2", chunks=())
        assert snapshot.generation == "g2"
        assert index.search("deadlock") == [chunk]

    def test_snapshot_writer_is_an_explicit_adapter_boundary(self):
        snapshot = RetrievalSnapshot(generation="g2", chunks=())

        class _Writer:
            def replace_all(self, value: RetrievalSnapshot) -> None:
                assert value is snapshot

        writer = _Writer()
        assert isinstance(writer, RetrievalSnapshotWriter)
        writer.replace_all(snapshot)


@pytest.mark.m6a
class TestToolContract:
    def test_read_tool_cannot_declare_a_domain_side_effect(self):
        with pytest.raises(ProtocolValidationError, match="read tools"):
            ToolSpec(
                name="retrieve",
                description="retrieve notes",
                input_schema={"type": "object"},
                capability=ToolCapability.READ,
                side_effect=SideEffect.DOMAIN_WRITE,
            )

    def test_write_tool_must_declare_its_side_effect(self):
        with pytest.raises(ProtocolValidationError, match="write tools"):
            ToolSpec(
                name="review_log",
                description="record review",
                input_schema={"type": "object"},
                capability=ToolCapability.WRITE,
            )

    def test_context_authorizes_capabilities_without_executing_domain_writes(self):
        read_spec = ToolSpec("retrieve", "retrieve notes", {"type": "object"})
        write_spec = ToolSpec(
            "review_log",
            "record review",
            {"type": "object"},
            capability=ToolCapability.WRITE,
            side_effect=SideEffect.DOMAIN_WRITE,
        )
        context = ToolContext(
            learner_id="learner-1",
            source_scope="DEFAULT_ONLY",
            correlation_id="c1",
            permissions=frozenset({"read"}),
        )

        assert context.allows(read_spec)
        assert not context.allows(write_spec)

    def test_cancelled_context_authorizes_no_tool(self):
        context = ToolContext(
            learner_id="learner-1",
            source_scope="DEFAULT_ONLY",
            correlation_id="c1",
            permissions=frozenset({"read", "write"}),
            cancelled=True,
        )

        assert not context.allows(ToolSpec("retrieve", "retrieve notes", {"type": "object"}))

    @pytest.mark.parametrize(
        "schema",
        [
            {"type": "string"},
            {"type": "object", "example": object()},
        ],
    )
    def test_tool_schema_must_be_json_safe_object_schema(self, schema):
        with pytest.raises(ProtocolValidationError, match="input_schema"):
            ToolSpec("retrieve", "retrieve notes", schema)

    def test_tool_result_preserves_structured_safe_error(self):
        result = ToolResult(
            error=ToolError("TOOL_UNAVAILABLE", "The tool is unavailable.", retryable=True),
            correlation_id="c1",
        )

        assert result.ok is False
        assert result.error is not None
        assert result.error.code == "TOOL_UNAVAILABLE"


@pytest.mark.m6a
class TestRunnerLifecycleContract:
    def test_runner_declares_cross_request_start_get_resume_step_lifecycle(self):
        runner = _MemoryRunner()
        context = RunnerContext(learner_id="learner-1", correlation_id="run-1")

        assert isinstance(runner, Runner)
        started = runner.start(context)
        fetched = runner.get(context, "run-1")
        resumed = runner.resume(context, "run-1")
        completed = runner.step(context, "run-1", RunnerEvent(RunnerEventType.COMPLETE, {"answer": "ignored"}))

        assert started.snapshot.status is RunnerStatus.WAITING
        assert fetched.snapshot.revision == 0
        assert resumed.snapshot.status is RunnerStatus.RUNNING
        assert completed.snapshot.status is RunnerStatus.COMPLETED
        assert completed.snapshot.state == {"last_event": "complete"}

    def test_runner_ids_are_durable_and_correlation_is_not_identity(self):
        runner = _MemoryRunner()
        context = RunnerContext(learner_id="learner-1", correlation_id="same-request")

        first = runner.start(context)
        second = runner.start(context)

        assert first.snapshot.run_id != second.snapshot.run_id
        assert runner.get(context, first.snapshot.run_id).snapshot.revision == 0

    def test_runner_cancellation_and_terminal_failure_are_structured(self):
        runner = _MemoryRunner()
        context = RunnerContext(learner_id="learner-1", correlation_id="run-cancel")
        started = runner.start(context)
        cancelled = runner.step(
            context,
            started.snapshot.run_id,
            RunnerEvent(RunnerEventType.CANCEL),
        )
        assert cancelled.snapshot.status is RunnerStatus.CANCELLED
        terminal = runner.step(
            context,
            started.snapshot.run_id,
            RunnerEvent(RunnerEventType.COMPLETE),
        )
        assert terminal.ok is False
        assert terminal.error is not None
        assert terminal.error.code == "RUN_TERMINAL"

    def test_existing_state_machine_remains_the_domain_authority(self):
        service, _qa, _quiz, scheduler = make_service()

        session = service.create(StudySessionCreateRequest(topic="死锁", course="os"))
        completed = service.submit_answer(
            session.session_id,
            StudySessionAnswerRequest(answer="互斥、占有并等待、不可剥夺、循环等待"),
        )

        assert session.state == "awaiting_answer"
        assert completed.state == "completed"
        assert completed.last_evaluation is not None
        assert completed.last_evaluation.correct is True
        assert completed.review is not None
        assert scheduler.logged[0].source_session_id == session.session_id
        assert service.get(session.session_id).session_id == session.session_id
