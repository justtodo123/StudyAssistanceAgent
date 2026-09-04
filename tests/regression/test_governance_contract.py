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

STAGE_PRODUCTION_SURFACES = {
    "M6a": {
        "paths": (
            "platform/app/protocols.py",
            "platform/app/tools",
            "platform/app/runners",
            "tests/M6a",
        ),
        "identifiers": ("SourceRegistry",),
        "api_paths": (),
        "requirements": (),
    },
    "M6b": {
        "paths": (
            "platform/app/tool_registry.py",
            "platform/app/llm_client.py",
            "platform/app/preview_agent.py",
            "platform/app/preview_service.py",
            "tests/M6b",
        ),
        "identifiers": (
            "SA_AGENT_PREVIEW_ENABLED",
            "SA_PREVIEW_MAX_TURNS",
            "SA_PREVIEW_DEADLINE_SECONDS",
            "SA_PREVIEW_TOOL_RESULT_LIMIT",
        ),
        "api_paths": ("/api/v1/agent-preview",),
        "requirements": ("anthropic",),
    },
    "M7": {
        "paths": (
            "platform/app/source_registry.py",
            "tests/M7",
        ),
        "identifiers": ("SourceRegistry",),
        "api_paths": (),
        "requirements": (),
    },
    "M8": {
        "paths": ("tests/M8",),
        "identifiers": (),
        "api_paths": (),
        "requirements": (
            "lancedb",
            "milvus",
            "milvus-lite",
            "pymilvus",
            "qdrant-client",
        ),
    },
    "M9": {
        "paths": ("tests/M9",),
        "identifiers": (),
        "api_paths": (),
        "requirements": (),
    },
    "M10": {
        "paths": ("tests/M10",),
        "identifiers": (
            "SA_RUNNER=react",
            "EffectLedger",
            "ReActRunner",
        ),
        "api_paths": ("/api/v1/autonomous-runs",),
        "requirements": ("openai",),
    },
}

# HTTP surfaces that remain future until a later increment maps them.
UNRELEASED_API_PATHS = ("/api/v1/sources",)


def _load_registry(repo_root: Path) -> dict:
    path = repo_root / "docs" / "standards" / "stage-admission-gates.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _local_markdown_links(text: str):
    for raw_link in re.findall(r"\[[^]]*\]\(([^)]+)\)", text):
        link = raw_link.strip().split(maxsplit=1)[0].strip("<>\"")
        if not link or link.startswith(("#", "http://", "https://", "mailto:")):
            continue
        yield unquote(link.split("#", 1)[0])



def _production_started(stage: dict) -> bool:
    start_gate = stage.get("implementation_start")
    delivery_status = stage["delivery_status"]
    legacy_complete = delivery_status == "COMPLETE" and start_gate is None
    explicitly_authorized = (
        start_gate is not None
        and start_gate.get("status") == "AUTHORIZED"
    )
    return (
        stage["admission_status"] == "ADMITTED"
        and delivery_status in {"IN_PROGRESS", "COMPLETE"}
        and (legacy_complete or explicitly_authorized)
    )


def test_production_start_requires_explicit_authorization_for_active_delivery():
    active = {
        "admission_status": "ADMITTED",
        "delivery_status": "IN_PROGRESS",
    }
    assert not _production_started(active)
    assert not _production_started(
        {
            **active,
            "implementation_start": {"status": "NOT_AUTHORIZED"},
        }
    )
    assert _production_started(
        {
            **active,
            "implementation_start": {"status": "AUTHORIZED"},
        }
    )
    assert _production_started(
        {
            "admission_status": "ADMITTED",
            "delivery_status": "COMPLETE",
        }
    )

class TestGovernanceNavigation:
    def test_navigation_links_resolve(self, repo_root):
        for relative_path in NAVIGATION_DOCS:
            document = repo_root / relative_path
            text = document.read_text(encoding="utf-8")
            for link in _local_markdown_links(text):
                target = (document.parent / link).resolve()
                assert target.exists(), f"{relative_path}: broken link {link}"


class TestBlockedStageProductionTree:
    def test_unstarted_stages_do_not_add_future_production_surfaces(self, repo_root):
        stages = {
            stage["stage"]: stage
            for stage in _load_registry(repo_root)["stages"]
        }

        allowed_paths: set[str] = set()
        allowed_identifiers: set[str] = set()
        allowed_api_paths: set[str] = set()
        allowed_requirements: set[str] = set()
        gated_paths: set[str] = set()
        gated_identifiers: set[str] = set()
        gated_api_paths: set[str] = set(UNRELEASED_API_PATHS)
        gated_requirements: set[str] = set()

        for stage_name, surfaces in STAGE_PRODUCTION_SURFACES.items():
            gated_paths.update(surfaces["paths"])
            gated_identifiers.update(surfaces["identifiers"])
            gated_api_paths.update(surfaces["api_paths"])
            gated_requirements.update(surfaces["requirements"])
            if _production_started(stages[stage_name]):
                allowed_paths.update(surfaces["paths"])
                allowed_identifiers.update(surfaces["identifiers"])
                allowed_api_paths.update(surfaces["api_paths"])
                allowed_requirements.update(surfaces["requirements"])

        unexpected_paths = [
            relative_path
            for relative_path in sorted(gated_paths - allowed_paths)
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
        for identifier in gated_identifiers:
            if identifier not in allowed_identifiers:
                assert identifier not in production_text

        for api_path in gated_api_paths:
            if api_path not in allowed_api_paths:
                assert api_path not in production_text

        requirements = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (repo_root / "platform").glob("requirements*.txt")
        )
        for package in gated_requirements:
            if package not in allowed_requirements:
                assert not re.search(
                    rf"(?m)^\s*{re.escape(package)}(?:\[|\s|[=<>!~])",
                    requirements,
                )
