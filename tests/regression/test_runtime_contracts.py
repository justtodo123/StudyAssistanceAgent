"""Regression tests for source gates, error codes, and latency percentiles."""

from __future__ import annotations

from app.errors import ErrorCode, error_body, http_error
from app.observability import metrics
from app.source_policy import (
    SourceIngestDenied,
    assert_crawler_output_allowed,
    is_indexable_frontmatter,
    is_indexable_relative_path,
)


class TestErrorCodes:
    def test_catalog_covers_current_api_failures(self):
        assert ErrorCode.SESSION_NOT_FOUND.value == "SESSION_NOT_FOUND"
        assert ErrorCode.ILLEGAL_SESSION_STATE.value == "ILLEGAL_SESSION_STATE"
        body = error_body(ErrorCode.SESSION_NOT_FOUND, "missing")
        assert body["code"] == "SESSION_NOT_FOUND"
        assert body["retryable"] is False

    def test_http_error_keeps_status_and_code(self):
        exc = http_error(ErrorCode.ILLEGAL_SESSION_STATE, "already completed")
        assert exc.status_code == 409
        assert exc.detail["code"] == "ILLEGAL_SESSION_STATE"

    def test_session_not_found_returns_stable_code(self, test_client):
        resp = test_client.get("/api/v1/study-sessions/missing")
        assert resp.status_code == 404
        data = resp.json()["detail"]
        assert data["code"] == "SESSION_NOT_FOUND"
        assert data["retryable"] is False


class TestLatencyPercentiles:
    def test_snapshot_exposes_percentiles(self):
        metrics.reset()
        for value in (10.0, 20.0, 30.0, 40.0, 100.0):
            metrics.record("search", value, 1)
        snapshot = metrics.snapshot()
        assert snapshot["avg_latency_ms"] == 40.0
        assert snapshot["p50_latency_ms"] == 30.0
        assert snapshot["p95_latency_ms"] == 100.0
        assert snapshot["p99_latency_ms"] == 100.0
        assert snapshot["sample_count"] == 5

    def test_health_includes_percentiles(self, test_client):
        data = test_client.get("/health").json()
        for key in ("avg_latency_ms", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "sample_count"):
            assert key in data
            assert data[key] >= 0


class TestGenerationLayer:
    def test_qa_note_summary_layer(self, test_client):
        resp = test_client.post(
            "/api/v1/qa",
            json={"question": "什么是死锁", "course": "os", "use_llm": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["generation_layer"] in {"note_summary", "no_hit"}
        if data["sources"]:
            assert data["generation_layer"] == "note_summary"


class TestSourceIngestGate:
    def test_default_notes_remain_indexable(self):
        assert is_indexable_relative_path("os/deadlock.md")
        assert is_indexable_frontmatter({})

    def test_inbox_and_candidates_are_not_indexable(self):
        assert not is_indexable_relative_path("_inbox/raw.md")
        assert not is_indexable_relative_path("_templates/entry-template.md")
        assert not is_indexable_frontmatter(
            {"source_type": "web_candidate", "ingest_status": "candidate"}
        )
        assert not is_indexable_frontmatter({"source_type": "ai_draft"})
        assert is_indexable_frontmatter(
            {"source_type": "web_reviewed", "ingest_status": "approved"}
        )

    def test_crawler_cannot_write_default_knowledge(self):
        from app import config

        blocked = config.KNOWLEDGE_ROOT / "os"
        try:
            assert_crawler_output_allowed(blocked)
            raise AssertionError("expected SourceIngestDenied")
        except SourceIngestDenied:
            pass
        allowed = config.REPO_ROOT / "platform" / ".cache" / "crawler-candidates" / "os"
        assert_crawler_output_allowed(allowed)
        assert_crawler_output_allowed(
            config.KNOWLEDGE_ROOT / "os",
            allow_knowledge_write=True,
        )
