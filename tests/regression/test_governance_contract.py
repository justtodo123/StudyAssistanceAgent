"""阻断期生产树与文档导航的治理契约。"""

from __future__ import annotations

import json
import re

from pathlib import Path

import pytest

from tests.utils.markdown_links import (
    assert_local_markdown_references,
    assert_local_markdown_target,
)


NAVIGATION_DOCS = (
    "docs/README.md",
    "docs/plans/README.md",
    "docs/plans/references/README.md",
    "docs/prds/README.md",
    "docs/standards/stage-admission-gates.md",
)

LEGACY_COMPLETE_STAGES = {"M6a", "M6b"}

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
        # 外部 AI 路径的 opt-in 开关：登记后该 env 面受 M9 门禁管辖——若 M9 哪天不再是
        # production-started，这个标识符出现在生产树里就会被判红。M9 现为 AUTHORIZED，故不触发。
        "identifiers": ("SA_PLAN_AI_ENABLED",),
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
    "M11": {
        "paths": (
            "platform/app/corpus_pipeline.py",
            "platform/app/data_scaling.py",
            "tests/M11",
        ),
        "identifiers": ("SA_DATA_SCALING_ENABLED", "ApprovedCorpusPipeline"),
        "api_paths": ("/api/v1/corpus-publications",),
        "requirements": ("scrapy", "trafilatura"),
    },
    "M12": {
        "paths": (
            "platform/app/cloud_profile.py",
            "platform/app/ingestion_worker.py",
            "tests/M12",
        ),
        "identifiers": ("SA_CLOUD_PROFILE", "CloudDeploymentProfile"),
        "api_paths": ("/api/v1/cloud-profile",),
        "requirements": ("boto3", "celery", "psycopg", "redis"),
    },
}

# HTTP surfaces that remain future until a later increment maps them.
UNRELEASED_API_PATHS = ("/api/v1/sources",)


def _load_registry(repo_root: Path) -> dict:
    path = repo_root / "docs" / "standards" / "stage-admission-gates.json"
    return json.loads(path.read_text(encoding="utf-8"))


_CANDIDATE_DIGEST = re.compile(r"candidate-evidence-digest:[0-9a-f]{64}")
_EVALUATION_DIGEST = re.compile(r"evaluation-report-sha256:[0-9a-f]{64}")


def _assert_registry_reference(reference: str, repo_root: Path) -> None:
    """Validate the closed allowlist for machine-registry references."""
    assert isinstance(reference, str) and reference.strip() == reference
    if _CANDIDATE_DIGEST.fullmatch(reference):
        return
    if _EVALUATION_DIGEST.fullmatch(reference):
        return
    if reference.startswith("User instruction:"):
        assert reference.removeprefix("User instruction:").strip()
        return
    assert_local_markdown_target(reference, repo_root, repo_root)


def _registry_references(registry: dict):
    for stage in registry["stages"]:
        for prerequisite in stage["prerequisites"]:
            yield from prerequisite.get("evidence", [])
        for decision in stage["mandatory_decisions"]:
            yield from decision.get("evidence", [])
        approval_reference = stage["approval"].get("approval_reference")
        if approval_reference is not None:
            yield approval_reference
        implementation_start = stage.get("implementation_start")
        if implementation_start is not None:
            reference = implementation_start.get("authorization_reference")
            if reference is not None:
                yield reference
        completion = stage.get("completion_approval")
        if completion is not None:
            yield from completion.get("evidence", [])
            yield completion["approval_reference"]
        # §7 requires every admission-history reference to be a portable repo path, but this
        # field was previously unenumerated, so that requirement rested on human discipline
        # alone. Fold it into the same allowlist rather than validating it separately.
        for record in stage.get("admission_history", []):
            reference = record.get("reference")
            if reference is not None:
                yield reference


def test_registry_references_use_closed_portable_allowlist(repo_root):
    for reference in _registry_references(_load_registry(repo_root)):
        _assert_registry_reference(reference, repo_root)


@pytest.mark.parametrize(
    "reference",
    (
        r"C:\Users\student\evidence.md",
        "/tmp/evidence.md",
        "../outside.md",
        "docs/does-not-exist.md",
        "docs/PLAN.md#missing-anchor",
        "tests/M6a#anchor-on-directory",
        "candidate-evidence-digest:not-a-sha256",
        "evaluation-report-sha256:ABCDEF",
        "User instruction:   ",
        "unknown-evidence-format:abc",
    ),
)
def test_registry_reference_allowlist_rejects_invalid_forms(repo_root, reference):
    with pytest.raises(AssertionError):
        _assert_registry_reference(reference, repo_root)


ADMISSION_STATUSES = {"BLOCKED", "ADMITTED", "REVOKED"}


def test_admission_history_records_are_well_formed(repo_root):
    """§7 规定每条准入过渡留痕恰好是 from / to / at / reason / reference 五键。

    这同时是上面那条 allowlist 用例的**非空性护栏**：`admission_history` 目前只有 M9 登记，
    若哪天被清空，`_registry_references` 里新增的那段就变成空转，而那条用例仍会全绿。
    """
    records = [
        record
        for stage in _load_registry(repo_root)["stages"]
        for record in stage.get("admission_history", [])
    ]

    assert records, "no admission_history is registered; the allowlist coverage is vacuous"
    for record in records:
        assert set(record) == {"from", "to", "at", "reason", "reference"}, record
        assert record["from"] in ADMISSION_STATUSES, record
        assert record["to"] in ADMISSION_STATUSES, record
        assert record["from"] != record["to"], record




def _production_started(stage: dict) -> bool:
    start_gate = stage.get("implementation_start")
    delivery_status = stage["delivery_status"]
    legacy_complete = (
        stage.get("stage") in LEGACY_COMPLETE_STAGES
        and delivery_status == "COMPLETE"
        and start_gate is None
    )
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
            "stage": "M6a",
            "admission_status": "ADMITTED",
            "delivery_status": "COMPLETE",
        }
    )
    assert not _production_started(
        {
            "stage": "M7",
            "admission_status": "ADMITTED",
            "delivery_status": "COMPLETE",
        }
    )


def test_complete_active_stage_requires_scoped_completion_approval(repo_root):
    stages = {
        stage["stage"]: stage
        for stage in _load_registry(repo_root)["stages"]
    }

    m7 = stages["M7"]
    completion = m7["completion_approval"]
    assert m7["delivery_status"] == "COMPLETE"
    assert completion == {
        "approved_by": "justtodo123",
        "approved_at": "2026-09-06",
        "approval_reference": "User instruction: 批准 M7 COMPLETE",
        "approval_scope": "m7-infrastructure-only-v1",
        "evidence": [
            "docs/PLAN.md",
            "docs/plans/m7-source-lifecycle-plan.md",
            "docs/baselines.md",
            "tests/M7/README.md",
            "tests/TEST_PLAN.md",
        ],
    }
    assert completion["approval_scope"] == m7["approval_scope"]["scope_id"]
    assert set(m7["approval_scope"]["excluded"]) == {
        "network.document-promotion",
        "network.corpus-governance-closure",
        "corpus.automatic-approval",
        "m8.specialized-storage",
        "milvus.backend-selection",
    }

    for stage in stages.values():
        if stage["delivery_status"] != "COMPLETE":
            continue
        if stage["stage"] in LEGACY_COMPLETE_STAGES:
            continue
        approval = stage.get("completion_approval")
        assert approval is not None
        assert approval["approved_by"]
        assert approval["approved_at"]
        assert approval["approval_reference"]
        assert approval["evidence"]
        scope = stage.get("approval_scope")
        if scope is not None:
            assert approval["approval_scope"] == scope["scope_id"]

class TestGovernanceNavigation:
    def test_navigation_links_resolve(self, repo_root):
        for relative_path in NAVIGATION_DOCS:
            document = repo_root / relative_path
            assert_local_markdown_references(document, repo_root)


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
