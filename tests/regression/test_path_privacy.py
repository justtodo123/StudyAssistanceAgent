"""跨阶段 API 路径隐私与 OpenAPI 契约。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9+.-])[A-Za-z]:[\\/]")
_TEMP_HOST_PATH = re.compile(
    r"C:[\\/]Users[\\/][^\\/\s`]+[\\/]AppData[\\/]Local[\\/]Temp[\\/]",
    re.IGNORECASE,
)
_EXTERNAL_SOURCE_ROOT = re.compile(
    r"D:[\\/]+111_Others_Subjects",
    re.IGNORECASE,
)
_EXTERNAL_POLICY_WORDS = (
    "外部",
    "原始资料",
    "只读",
    "映射",
    "没有",
    "禁止",
    "严禁",
    "不得",
    "不读取",
    "不复制",
    "不扫描",
    "默认扫描",
    "列出",
    "--root",
)


def _contains_host_path(value: Any, roots: tuple[Path, ...]) -> bool:
    """Return whether serialized data contains a host-path or traversal form."""
    if isinstance(value, dict):
        return any(_contains_host_path(item, roots) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_host_path(item, roots) for item in value)
    if not isinstance(value, str):
        return False

    normalized = value.replace("\\", "/")
    root_strings = {
        str(root).replace("\\", "/").rstrip("/").lower() for root in roots
    }
    lowered = normalized.lower()
    if any(root and root in lowered for root in root_strings):
        return True
    if normalized.startswith("/") or normalized.startswith("//"):
        return True
    if normalized.startswith("../") or normalized == "..":
        return True
    return bool(_WINDOWS_PATH.search(value) or value.startswith("\\\\"))


def _assert_no_host_paths(payload: Any, repo_root: Path, knowledge_root: Path) -> None:
    roots = (repo_root.resolve(), knowledge_root.resolve())
    if _contains_host_path(payload, roots):
        offending: list[str] = []

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                for item in value.values():
                    collect(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    collect(item)
            elif isinstance(value, str) and _contains_host_path(value, roots):
                offending.append(value)

        collect(payload)
        assert not offending, f"host path forms found: {offending[:3]!r}"


def _data_events(body: str) -> list[str]:
    events: list[str] = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        data_lines = [line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")]
        if data_lines:
            events.append("\n".join(data_lines))
    return events


def test_governance_documents_reject_host_temp_paths_and_limit_external_root(
    repo_root,
):
    documents = [repo_root / "README.md", repo_root / "docs" / "PLAN.md"]
    documents.extend((repo_root / "docs").rglob("*.md"))
    violations: list[str] = []

    for document in documents:
        text = document.read_text(encoding="utf-8")
        if _TEMP_HOST_PATH.search(text):
            violations.append(f"{document.relative_to(repo_root)}: host temp path")
        lines = text.splitlines()
        for line_number, line in enumerate(lines, start=1):
            context = " ".join(
                lines[max(0, line_number - 2):min(len(lines), line_number + 1)]
            )
            for match in _WINDOWS_PATH.finditer(line):
                candidate = line[match.start():]
                if _EXTERNAL_SOURCE_ROOT.match(candidate):
                    if not any(word in context for word in _EXTERNAL_POLICY_WORDS):
                        violations.append(
                            f"{document.relative_to(repo_root)}:{line_number}: "
                            "external root outside policy context"
                        )
                    continue
                violations.append(
                    f"{document.relative_to(repo_root)}:{line_number}: "
                    "host absolute path"
                )

    assert violations == []


def test_redacted_m8_records_preserve_experiment_root_basename(repo_root):
    expected = {
        "docs/plans/references/m8-v11-authorization-20260909.md": (
            "<system-temp>/sa-m8-v11-679fc578a7d84e51ffc1fa0210a2be94"
        ),
        "docs/plans/references/m8-v12-authorization-20260909.md": (
            "<system-temp>/sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c"
        ),
        "docs/plans/references/m8-v12-independent-static-audit-20260909.md": (
            "<system-temp>/sa-m8-v12-9fd8842953bd49b6924428a8461a5b1c"
        ),
    }
    for relative_path, redacted_root in expected.items():
        text = (repo_root / relative_path).read_text(encoding="utf-8")
        assert redacted_root in text
        assert not _TEMP_HOST_PATH.search(text)


class TestPathPrivacy:
    def test_health_exposes_logical_source_identity_only(self, test_client, repo_root, knowledge_root):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["knowledge_root"], str)
        assert data["knowledge_root"] == "knowledge-pack"
        _assert_no_host_paths(data, repo_root, knowledge_root)

    def test_search_and_qa_keep_logical_sources(self, test_client, repo_root, knowledge_root):
        search = test_client.post(
            "/api/v1/search",
            json={"question": "进程调度", "top_k": 3, "use_vector": False},
        )
        assert search.status_code == 200
        search_data = search.json()
        assert search_data["results"]
        for result in search_data["results"]:
            assert result["file"].startswith("knowledge/")
            assert not _contains_host_path(result["file"], (repo_root, knowledge_root))
        _assert_no_host_paths(search_data, repo_root, knowledge_root)

        qa = test_client.post(
            "/api/v1/qa",
            json={"question": "什么是死锁", "course": "os", "use_vector": False, "use_llm": False},
        )
        assert qa.status_code == 200
        qa_data = qa.json()
        assert qa_data["sources"]
        _assert_no_host_paths(qa_data, repo_root, knowledge_root)

    def test_qa_sse_preserves_frames_and_safe_sources(self, test_client, repo_root, knowledge_root):
        response = test_client.post(
            "/api/v1/qa/stream",
            json={"question": "什么是死锁", "course": "os", "use_vector": False, "use_llm": False},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _data_events(response.text)
        assert len(events) >= 2
        assert events.count("[DONE]") == 1
        assert events[-1] == "[DONE]"

        metadata = json.loads(events[0])
        assert metadata["sources"]
        _assert_no_host_paths(metadata, repo_root, knowledge_root)
        for source in metadata["sources"]:
            assert source["file"].startswith("knowledge/")
            assert source["file"].endswith(".md")
            assert ".." not in source["file"].replace("\\", "/").split("/")

        for event in events[1:-1]:
            delta = json.loads(event)
            assert set(delta) == {"delta"}
            _assert_no_host_paths(delta, repo_root, knowledge_root)

    def test_openapi_keeps_public_routes_without_host_paths(
        self, test_client, repo_root, knowledge_root
    ):
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        document = response.json()
        expected_paths = {
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
        assert expected_paths <= set(document["paths"])
        assert not any(path.startswith("/api/v1/agent-preview") for path in document["paths"])
        assert not any(path.startswith("/api/v1/sources") for path in document["paths"])
        _assert_no_host_paths(document, repo_root, knowledge_root)

    def test_search_and_qa_logs_exclude_host_paths(
        self, test_client, repo_root, knowledge_root, caplog
    ):
        import logging

        with caplog.at_level(logging.INFO, logger="app"):
            test_client.post(
                "/api/v1/search",
                json={"question": "测试查询", "top_k": 1, "use_vector": False},
            )
            test_client.post(
                "/api/v1/qa",
                json={"question": "测试查询", "use_vector": False, "use_llm": False},
            )
        for record in caplog.records:
            if record.name == "app":
                _assert_no_host_paths(record.getMessage(), repo_root, knowledge_root)


def test_qa_llm_fallback_does_not_expose_exception_paths(monkeypatch, test_client, repo_root, knowledge_root):
    from app import config
    from app.main import _qa

    leaked_path = repo_root / "private" / "provider.log"
    monkeypatch.setattr(config, "LLM_API_KEY", "configured-for-test")

    def fail_generation(*_args, **_kwargs):
        raise OSError(f"provider failure at {leaked_path}")

    monkeypatch.setattr(_qa, "_generate", fail_generation)
    response = test_client.post(
        "/api/v1/qa",
        json={"question": "什么是死锁", "course": "os", "use_vector": False, "use_llm": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert "LLM generation failed; used local summary." in data["answer"]
    _assert_no_host_paths(data, repo_root, knowledge_root)
