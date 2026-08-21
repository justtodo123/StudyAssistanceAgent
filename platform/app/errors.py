"""Stable application error codes.

HTTP status is transport. Clients and tests should match `code`.
See docs/standards/runtime-contracts.md.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import HTTPException


class ErrorCode(StrEnum):
    WORKBENCH_UNAVAILABLE = "WORKBENCH_UNAVAILABLE"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    ILLEGAL_SESSION_STATE = "ILLEGAL_SESSION_STATE"
    SOURCE_INGEST_DENIED = "SOURCE_INGEST_DENIED"
    VECTOR_DIMENSION_MISMATCH = "VECTOR_DIMENSION_MISMATCH"
    LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"
    LLM_GENERATION_FAILED = "LLM_GENERATION_FAILED"
    TOOL_PERMISSION_DENIED = "TOOL_PERMISSION_DENIED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.WORKBENCH_UNAVAILABLE: 404,
    ErrorCode.SESSION_NOT_FOUND: 404,
    ErrorCode.ILLEGAL_SESSION_STATE: 409,
    ErrorCode.SOURCE_INGEST_DENIED: 403,
    ErrorCode.VECTOR_DIMENSION_MISMATCH: 500,
    ErrorCode.LLM_NOT_CONFIGURED: 503,
    ErrorCode.LLM_GENERATION_FAILED: 503,
    ErrorCode.TOOL_PERMISSION_DENIED: 403,
    ErrorCode.BUDGET_EXCEEDED: 429,
}

RETRYABLE = {
    ErrorCode.LLM_GENERATION_FAILED,
    ErrorCode.BUDGET_EXCEEDED,
}


def error_body(code: ErrorCode, message: str) -> dict[str, Any]:
    return {
        "code": code.value,
        "message": message,
        "retryable": code in RETRYABLE,
    }


def http_error(code: ErrorCode, message: str, *, status_code: int | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code or HTTP_STATUS[code],
        detail=error_body(code, message),
    )
