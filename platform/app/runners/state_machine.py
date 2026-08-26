"""Thin runner adapter for the persisted study-session state machine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from ..models import StudySessionAnswerRequest, StudySessionCreateRequest, StudySessionResponse
from ..protocols import (
    RunnerContext,
    RunnerEvent,
    RunnerEventType,
    RunnerResult,
    RunnerSnapshot,
    RunnerStatus,
    ToolError,
)
from ..study_session import (
    IllegalSessionStateError,
    SessionNotFoundError,
    StudySessionService,
)


class StateMachineRunner:
    """Expose StudySessionService through the provider-neutral Runner protocol."""

    def __init__(self, service: StudySessionService | None = None) -> None:
        self._service = service or StudySessionService()

    def start(self, context: RunnerContext) -> RunnerResult:
        if context.cancelled:
            return self._unstarted_error("RUN_CONTROL_UNSUPPORTED", "runner cancellation is unsupported")
        if set(context.input) - {"topic", "course", "question_count", "use_llm"}:
            return self._unstarted_error("RUN_INPUT_INVALID", "runner input is invalid")
        try:
            request = StudySessionCreateRequest(**dict(context.input))
        except (TypeError, ValidationError):
            return self._unstarted_error("RUN_INPUT_INVALID", "runner input is invalid")
        try:
            response = self._service.create(request)
        except Exception:
            return self._unstarted_error("RUN_EXECUTION_FAILED", "study session could not be created", retryable=True)
        return self._result(response)

    def get(self, context: RunnerContext, run_id: str) -> RunnerResult:
        return self._load(context, run_id)

    def resume(self, context: RunnerContext, run_id: str) -> RunnerResult:
        return self._load(context, run_id)

    def step(self, context: RunnerContext, run_id: str, event: RunnerEvent) -> RunnerResult:
        current = self._load(context, run_id)
        if not current.ok:
            return current
        if context.cancelled or event.type in {RunnerEventType.CANCEL, RunnerEventType.FAIL}:
            return RunnerResult(
                snapshot=current.snapshot,
                output=current.output,
                error=ToolError("RUN_CONTROL_UNSUPPORTED", "runner control event is unsupported"),
            )
        response = current.output
        if event.type is RunnerEventType.COMPLETE:
            if response.state != "completed":
                return RunnerResult(
                    snapshot=current.snapshot,
                    output=response,
                    error=ToolError("RUN_EVENT_INVALID", "study session is not completed"),
                )
            return current
        if event.type is not RunnerEventType.CONTINUE:
            return RunnerResult(
                snapshot=current.snapshot,
                output=response,
                error=ToolError("RUN_EVENT_INVALID", "runner event is invalid"),
            )
        if set(event.payload) != {"question_id", "answer"}:
            return RunnerResult(
                snapshot=current.snapshot,
                output=response,
                error=ToolError("RUN_EVENT_INVALID", "continue payload is invalid"),
            )
        try:
            request = StudySessionAnswerRequest(**dict(event.payload))
        except (TypeError, ValidationError):
            return RunnerResult(
                snapshot=current.snapshot,
                output=response,
                error=ToolError("RUN_EVENT_INVALID", "continue payload is invalid"),
            )
        try:
            updated = self._service.submit_answer(run_id, request)
        except SessionNotFoundError:
            return self._not_found(run_id)
        except IllegalSessionStateError:
            return RunnerResult(
                snapshot=current.snapshot,
                output=response,
                error=ToolError("RUN_EVENT_INVALID", "study session does not accept answers"),
            )
        except Exception:
            return RunnerResult(
                snapshot=current.snapshot,
                output=response,
                error=ToolError("RUN_EXECUTION_FAILED", "study session step failed", retryable=True),
            )
        return self._result(updated)

    def _load(self, context: RunnerContext, run_id: str) -> RunnerResult:
        if not isinstance(run_id, str) or not run_id:
            return self._not_found("unknown")
        try:
            response = self._service.get(run_id)
        except SessionNotFoundError:
            return self._not_found(run_id)
        except Exception:
            return RunnerResult(
                snapshot=self._placeholder(run_id),
                error=ToolError("RUN_EXECUTION_FAILED", "study session could not be loaded", retryable=True),
            )
        if context.cancelled:
            return RunnerResult(
                snapshot=self._snapshot(response),
                output=response,
                error=ToolError("RUN_CONTROL_UNSUPPORTED", "runner cancellation is unsupported"),
            )
        return self._result(response)

    def _result(self, response: StudySessionResponse) -> RunnerResult:
        return RunnerResult(snapshot=self._snapshot(response), output=response)

    @staticmethod
    def _snapshot(response: StudySessionResponse) -> RunnerSnapshot:
        status = RunnerStatus.COMPLETED if response.state == "completed" else RunnerStatus.RUNNING
        if response.state == "awaiting_answer":
            status = RunnerStatus.WAITING
        # The persisted trace is the domain-owned monotonic event history. It avoids
        # counting future quiz questions and remains stable across reloads/idempotent steps.
        revision = len(response.tool_trace)
        state: Mapping[str, Any] = {
            "session_id": response.session_id,
            "course": response.course,
            "topic": response.topic,
            "current_question_id": response.current_question_id,
        }
        return RunnerSnapshot(
            run_id=response.session_id,
            status=status,
            revision=revision,
            waiting_for=response.current_question_id,
            state=state,
        )

    @staticmethod
    def _placeholder(run_id: str) -> RunnerSnapshot:
        return RunnerSnapshot(run_id=run_id or "unknown", status=RunnerStatus.CREATED)

    def _not_found(self, run_id: str) -> RunnerResult:
        return RunnerResult(
            snapshot=self._placeholder(run_id),
            error=ToolError("RUN_NOT_FOUND", "study session was not found"),
        )

    def _unstarted_error(self, code: str, message: str, *, retryable: bool = False) -> RunnerResult:
        return RunnerResult(
            snapshot=self._placeholder("unstarted"),
            error=ToolError(code, message, retryable=retryable),
        )


__all__ = ["StateMachineRunner"]
