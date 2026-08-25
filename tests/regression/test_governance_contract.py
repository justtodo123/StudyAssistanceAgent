"""阻断期生产树与文档导航的治理契约。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote


NAVIGATION_DOCS = (
    "docs/README.md",
    "docs/plans/README.md",
    "docs/prds/README.md",
    "docs/standards/stage-admission-gates.md",
)

FUTURE_STAGE_PATHS = (
    "platform/app/protocols.py",
    "platform/app/tool_registry.py",
    "platform/app/llm_client.py",
    "platform/app/preview_agent.py",
    "platform/app/preview_service.py",
    "platform/app/tools",
    "platform/app/runners",
    "tests/M6a",
    "tests/M6b",
    "tests/M7",
    "tests/M8",
    "tests/M9",
    "tests/M10",
)

FUTURE_RUNTIME_IDENTIFIERS = (
    "SA_AGENT_PREVIEW_ENABLED",
    "SA_PREVIEW_MAX_TURNS",
    "SA_PREVIEW_DEADLINE_SECONDS",
    "SA_PREVIEW_TOOL_RESULT_LIMIT",
    "SA_RUNNER=react",
    "SourceRegistry",
    "EffectLedger",
    "ReActRunner",
)

FUTURE_API_PATHS = (
    "/api/v1/agent-preview",
    "/api/v1/sources",
    "/api/v1/autonomous-runs",
)

FUTURE_REQUIREMENTS = (
    "anthropic",
    "lancedb",
    "openai",
    "qdrant-client",
)


def _load_registry(repo_root: Path) -> dict:
    path = repo_root / "docs" / "standards" / "stage-admission-gates.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _local_markdown_links(text: str):
    for raw_link in re.findall(r"\[[^]]*\]\(([^)]+)\)", text):
        link = raw_link.strip().split(maxsplit=1)[0].strip("<>\"")
        if not link or link.startswith(("#", "http://", "https://", "mailto:")):
            continue
        yield unquote(link.split("#", 1)[0])


class TestGovernanceNavigation:
    def test_navigation_links_resolve(self, repo_root):
        for relative_path in NAVIGATION_DOCS:
            document = repo_root / relative_path
            text = document.read_text(encoding="utf-8")
            for link in _local_markdown_links(text):
                target = (document.parent / link).resolve()
                assert target.exists(), f"{relative_path}: broken link {link}"


class TestBlockedStageProductionTree:
    def test_unadmitted_stages_do_not_add_future_production_surfaces(self, repo_root):
        stages = _load_registry(repo_root)["stages"]
        if not all(stage["admission_status"] != "ADMITTED" for stage in stages):
            return

        unexpected_paths = [
            relative_path
            for relative_path in FUTURE_STAGE_PATHS
            if (repo_root / relative_path).exists()
        ]
        assert unexpected_paths == []

        production_files = [
            path
            for path in (repo_root / "platform" / "app").rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]
        production_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in production_files
            if path.suffix in {".py", ".js", ".html"}
        )
        for identifier in FUTURE_RUNTIME_IDENTIFIERS:
            assert identifier not in production_text
        for api_path in FUTURE_API_PATHS:
            assert api_path not in production_text

        requirements = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (repo_root / "platform").glob("requirements*.txt")
        )
        for package in FUTURE_REQUIREMENTS:
            assert not re.search(rf"(?m)^\s*{re.escape(package)}(?:\[|\s|[=<>!~])", requirements)
