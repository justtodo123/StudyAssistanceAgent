"""Authenticated, capacity-bounded HTTP surface for the M6b Agent Preview."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, replace
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from .llm_client import AnthropicLLMClient, LLMClient
from .preview_agent import (
    PreviewAgent,
    PreviewLimits,
    PreviewResult,
    PreviewUsage,
    ToolWorkLimiter,
)
from .protocols import ToolContext
from .tool_registry import ToolRegistry

PREVIEW_PATH = "/api/v1/agent-preview"


class PreviewRequest(BaseModel):
    """One bounded preview prompt."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    prompt: str = Field(min_length=1, max_length=8192)
    learner_id: str | None = Field(default=None, max_length=128)


class PreviewUsageResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    estimated_cost_usd: float


class PreviewSourceResponse(BaseModel):
    source_id: str
    logical_uri: str
    document_id: str


class PreviewResponse(BaseModel):
    status: Literal["completed", "terminated"]
    termination_reason: str
    answer: str | None
    sources: list[PreviewSourceResponse]
    agent_trace: list[dict[str, Any]]
    usage: PreviewUsageResponse
    model_turn_count: int
    tool_call_count: int


class PreviewErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool


class PreviewErrorEnvelope(BaseModel):
    error: PreviewErrorDetail


class PreviewHttpError(BaseModel):
    detail: PreviewErrorEnvelope


def _error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "retryable": status_code >= 429}},
    )


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token or " " in token:
        return None
    return token


class PreviewService:
    """Own preview authentication, concurrency, deadlines, and request-local traces."""

    def __init__(
        self,
        *,
        token: str,
        provider_key: str,
        registry: ToolRegistry,
        client_factory: Callable[[str], LLMClient] = AnthropicLLMClient,
        limits: PreviewLimits = PreviewLimits(),
        capacity: int = 2,
        semaphore_wait_seconds: float = 0.25,
        hmac_key: bytes | None = None,
    ) -> None:
        if len(token.encode("utf-8")) < 32:
            raise ValueError("preview token must contain at least 32 UTF-8 bytes")
        if capacity != 2:
            raise ValueError("preview capacity is frozen at two")
        if not 0 < semaphore_wait_seconds <= 0.25:
            raise ValueError("preview semaphore wait must be within the hard limit")
        self._token = token
        self._provider_key = provider_key
        self._registry = registry
        self._client_factory = client_factory
        self._limits = limits
        self._semaphore = asyncio.Semaphore(capacity)
        self._tool_work_limiter = ToolWorkLimiter(capacity)
        self._semaphore_wait_seconds = semaphore_wait_seconds
        self._hmac_key = hmac_key or secrets.token_bytes(32)

    def authenticate(self, authorization: str | None) -> None:
        supplied = _bearer_token(authorization)
        candidate = supplied if supplied is not None else ""
        valid = hmac.compare_digest(candidate.encode("utf-8"), self._token.encode("utf-8"))
        if not valid:
            raise _error("PREVIEW_UNAUTHORIZED", "preview authorization failed", status.HTTP_401_UNAUTHORIZED)

    async def run(self, request: PreviewRequest, authorization: str | None) -> PreviewResponse:
        started = time.monotonic()
        self.authenticate(authorization)
        if not self._provider_key:
            raise _error(
                "PREVIEW_PROVIDER_NOT_CONFIGURED",
                "preview provider is not configured",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        request_id = secrets.token_hex(16)
        correlation_id = self._digest_identifier(request_id)
        remaining = self._limits.deadline_seconds - (time.monotonic() - started)
        if remaining <= 0:
            return self._response(_deadline_result(), correlation_id, started)
        wait_seconds = min(self._semaphore_wait_seconds, remaining)
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=wait_seconds,
            )
        except TimeoutError:
            # asyncio.wait_for may wake slightly before the exact deadline.  When
            # the total deadline bounded the semaphore wait, preserve deadline
            # semantics rather than exposing a scheduler-dependent overload.
            if (
                wait_seconds >= remaining
                or time.monotonic() - started >= self._limits.deadline_seconds
            ):
                return self._response(_deadline_result(), correlation_id, started)
            error = _error(
                "PREVIEW_OVERLOADED",
                "preview capacity is full",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
            error.headers = {"Retry-After": "1"}
            raise error from None

        client: LLMClient | None = None
        try:
            remaining = self._limits.deadline_seconds - (time.monotonic() - started)
            if remaining <= 0:
                return self._response(_deadline_result(), correlation_id, started)
            client = self._client_factory(self._provider_key)
            context = ToolContext(
                learner_id=request.learner_id,
                source_scope="DEFAULT_PLUS_EXTRAS",
                correlation_id=correlation_id,
                permissions=frozenset({"read"}),
            )
            limits = replace(self._limits, deadline_seconds=remaining)
            agent = PreviewAgent(
                client,
                self._registry,
                limits=limits,
                monotonic=time.monotonic,
                tool_work_limiter=self._tool_work_limiter,
            )
            result = await agent.run(request.prompt, context)
            return self._response(result, correlation_id, started)
        except asyncio.CancelledError:
            raise
        finally:
            try:
                if client is not None:
                    try:
                        await client.close()
                    except Exception:
                        # Cleanup is best-effort and must not replace a sanitized result
                        # with a provider-specific exception. Cancellation still propagates.
                        pass
            finally:
                self._semaphore.release()

    def _digest_identifier(self, value: str) -> str:
        return hmac.new(self._hmac_key, value.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _response(result: PreviewResult, correlation_id: str, started: float) -> PreviewResponse:
        trace = [dict(item) for item in result.agent_trace]
        trace.append(
            {
                "schema_version": "m6b-agent-trace-v1",
                "request_id_hmac": correlation_id,
                "termination_reason": result.termination_reason,
                "latency_ms": round(max(0.0, (time.monotonic() - started) * 1000), 3),
            }
        )
        return PreviewResponse(
            status=result.status,
            termination_reason=result.termination_reason,
            answer=result.answer,
            sources=[asdict(source) for source in result.sources],
            agent_trace=trace,
            usage=PreviewUsageResponse(**asdict(result.usage)),
            model_turn_count=result.model_turn_count,
            tool_call_count=result.tool_call_count,
        )


def _deadline_result() -> PreviewResult:
    return PreviewResult(
        status="terminated",
        termination_reason="deadline_exceeded",
        answer=None,
        sources=(),
        agent_trace=(),
        usage=PreviewUsage(),
        model_turn_count=0,
        tool_call_count=0,
    )


def _validation_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": {
                "error": {
                    "code": "PREVIEW_REQUEST_INVALID",
                    "message": "preview request is invalid",
                    "retryable": False,
                }
            }
        },
    )


class _SanitizedValidationRoute(APIRoute):
    """Replace FastAPI's input-echoing validation body at the preview boundary."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        original = super().get_route_handler()

        async def sanitized(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError:
                return _validation_error_response()

        return sanitized


def build_preview_router(service: PreviewService) -> APIRouter:
    """Build an isolated router without touching a singleton app or OpenAPI cache."""
    router = APIRouter(route_class=_SanitizedValidationRoute)

    @router.post(
        PREVIEW_PATH,
        response_model=PreviewResponse,
        responses={
            401: {"model": PreviewHttpError},
            422: {"model": PreviewHttpError},
            429: {"model": PreviewHttpError},
            503: {"model": PreviewHttpError},
        },
    )
    async def agent_preview(
        request: PreviewRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> PreviewResponse:
        return await service.run(request, authorization)

    return router


__all__ = [
    "PREVIEW_PATH",
    "PreviewRequest",
    "PreviewResponse",
    "PreviewService",
    "build_preview_router",
]
