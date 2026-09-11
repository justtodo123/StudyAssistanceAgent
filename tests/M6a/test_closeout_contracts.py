"""M6a-4 API/OpenAPI and documentation closeout contracts."""

from __future__ import annotations

from pathlib import Path

from tests.utils.markdown_links import assert_local_markdown_references

import pytest

pytestmark = pytest.mark.m6a

PUBLIC_API_PATHS = {
    "/health",
    "/api/v1/search",
    "/api/v1/qa",
    "/api/v1/qa/stream",
    "/api/v1/quiz",
    "/api/v1/review-log",
    "/api/v1/review-due",
    "/api/v1/review-plan",
    "/api/v1/study-sessions",
    "/api/v1/study-sessions/{session_id}",
    "/api/v1/study-sessions/{session_id}/answers",
}

DOCUMENTED_ROUTE_FILES = (
    "README.md",
    "platform/README.md",
)

LINK_DOCUMENTS = (
    "README.md",
    "platform/README.md",
    "docs/PLAN.md",
    "docs/README.md",
    "docs/plans/README.md",
    "docs/plans/m6a-harness-skeleton-plan.md",
    "docs/standards/runtime-contracts.md",
    "docs/standards/stage-admission-gates.md",
    "tests/TEST_PLAN.md",
)

FORBIDDEN_API_PREFIXES = (
    "/api/v1/agent-preview",
    "/api/v1/sources",
    "/api/v1/autonomous-runs",
)



def test_openapi_public_paths_remain_exact(test_client) -> None:
    document = test_client.get("/openapi.json").json()
    paths = set(document["paths"])
    assert PUBLIC_API_PATHS <= paths
    unexpected = [
        path
        for path in paths
        if path.startswith("/api/") or path == "/health"
        if path not in PUBLIC_API_PATHS
    ]
    assert unexpected == []
    assert not any(
        path.startswith(prefix)
        for path in paths
        for prefix in FORBIDDEN_API_PREFIXES
    )


def test_documented_routes_match_openapi_contract(repo_root: Path) -> None:
    for relative in DOCUMENTED_ROUTE_FILES:
        text = (repo_root / relative).read_text(encoding="utf-8")
        for route in (
            "/api/v1/search",
            "/api/v1/qa",
            "/api/v1/qa/stream",
            "/api/v1/review-plan",
            "/api/v1/quiz",
            "/api/v1/review-log",
            "/api/v1/review-due",
            "/api/v1/study-sessions",
        ):
            assert route in text, f"{relative} missing {route}"


def test_closeout_documents_have_resolvable_links(repo_root: Path) -> None:
    for relative in LINK_DOCUMENTS:
        document = repo_root / relative
        assert_local_markdown_references(document, repo_root)


def test_workbench_and_health_remain_available(test_client) -> None:
    workbench = test_client.get("/")
    health = test_client.get("/health")
    assert workbench.status_code == 200
    assert "text/html" in workbench.headers.get("content-type", "")
    assert health.status_code == 200
    payload = health.json()
    assert payload["status"] == "UP"
    assert payload["knowledge_root"] == "knowledge-pack"
