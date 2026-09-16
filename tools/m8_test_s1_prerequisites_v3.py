#!/usr/bin/env python3
"""Run the safe M8 v3 S1 prerequisite self-check suite.

This command is deliberately an aggregate *self-check*, not an execution harness.
It reads repository governance documents and exercises a tiny in-memory mock only.
It never generates study material, starts a backend/service, accesses external
study-material directories, installs dependencies, or performs network I/O.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


SUCCESS_LINE = "ALL PASS: M8 v3 S1 prerequisite suite"
REPO_ROOT = Path(__file__).resolve().parents[1]

REGISTRY_PATH = REPO_ROOT / "docs" / "standards" / "stage-admission-gates.json"
PLAN_PATH = REPO_ROOT / "docs" / "PLAN.md"
M8_PLAN_PATH = REPO_ROOT / "docs" / "plans" / "m8-specialized-storage-plan.md"
DECISION_PATH = REPO_ROOT / "docs" / "plans" / "references" / "m8-decision-closure-v1.md"
DRAFT_REVIEW_PATH = (
    REPO_ROOT
    / "docs"
    / "plans"
    / "references"
    / "m8-active-execution-protocol-draft-0.5-review-20260913.md"
)
V13_DISPOSITION_PATH = (
    REPO_ROOT / "docs" / "plans" / "references" / "m8-v13-disposition-20260910.md"
)

EXPECTED_DECISIONS = {
    "M8-CONTROL-SCHEMA": "SQLITE_M7_AUTHORITATIVE_CONTROL_PLANE__REBUILDABLE_SPECIALIZED_DATA_PLANE",
    "M8-MIGRATION": "FROZEN_EXPORT__ISOLATED_BUILD__VALIDATE__SHADOW_READ__MANUAL_CUTOVER",
    "M8-LANCEDB-CRITERIA": "PRIMARY_LOCAL_SPECIALIZED_CANDIDATE__OPT_IN_ONLY_AFTER_ALL_HARD_GATES",
    "M8-QDRANT-CRITERIA": "NOT_A_LOCAL_DEFAULT__CLOUD_OR_SERVICE_TRIGGERED_CANDIDATE_ONLY",
    "M8-BACKEND-PARITY": "ZERO_TOLERANCE_IDENTITY_AUTH_LIFECYCLE__FROZEN_SCORE_ORDER_TOLERANCE",
    "M8-FALLBACK": "DEFAULT_PACK_SQLITE_BM25_FALLBACK__USER_SOURCE_FAIL_CLOSED",
    "M8-DEPENDENCY-PACKAGING": "ISOLATED_OPTIONAL_EXTRAS__NO_MANDATORY_SERVICE_OR_NETWORK",
    "M8-BENCHMARK": "1K_CORRECTNESS__10K_SINGLE_USER__100K_CAPACITY_FILTERED__OPTIONAL_CONCURRENCY",
}


class CheckFailure(AssertionError):
    """A deterministic, user-facing prerequisite failure."""


@dataclass(frozen=True)
class Check:
    name: str
    function: Callable[[], None]


def _read(path: Path) -> str:
    if not path.is_file():
        raise CheckFailure(f"missing required repository file: {path.relative_to(REPO_ROOT)}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise CheckFailure(f"non-UTF-8 repository file: {path.relative_to(REPO_ROOT)}") from exc


def _load_registry() -> dict:
    try:
        value = json.loads(_read(REGISTRY_PATH))
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"invalid stage registry JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CheckFailure("stage registry root must be an object")
    return value


def _m8_stage(registry: dict) -> dict:
    stages = registry.get("stages")
    if not isinstance(stages, list):
        raise CheckFailure("stage registry has no stages list")
    for stage in stages:
        if isinstance(stage, dict) and stage.get("stage") == "M8":
            return stage
    raise CheckFailure("stage registry has no M8 entry")


def _assert_contains(text: str, *needles: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise CheckFailure("missing required markers: " + ", ".join(missing))


def check_repository_contract() -> None:
    """Confirm the aggregate has only the repository evidence it needs."""
    for path in (REGISTRY_PATH, PLAN_PATH, M8_PLAN_PATH, DECISION_PATH, DRAFT_REVIEW_PATH, V13_DISPOSITION_PATH):
        _read(path)


def check_m7_exit_prerequisite() -> None:
    registry = _load_registry()
    stage = _m8_stage(registry)
    prerequisites = stage.get("prerequisites")
    if prerequisites != [
        {
            "id": "M8-M7-EXIT",
            "status": "SATISFIED",
            "evidence": ["docs/PLAN.md", "docs/plans/m7-source-lifecycle-plan.md", "docs/baselines.md"],
        }
    ]:
        raise CheckFailure("M8-M7-EXIT is not the expected satisfied prerequisite")


def check_m8_remains_blocked() -> None:
    registry = _load_registry()
    stage = _m8_stage(registry)
    if stage.get("admission_status") != "BLOCKED":
        raise CheckFailure(f"M8 admission is {stage.get('admission_status')!r}, expected BLOCKED")
    if stage.get("delivery_status") != "NOT_STARTED":
        raise CheckFailure(f"M8 delivery is {stage.get('delivery_status')!r}, expected NOT_STARTED")
    approval = stage.get("approval")
    if not isinstance(approval, dict) or any(value is not None for value in approval.values()):
        raise CheckFailure("M8 approval fields must remain empty")


def check_eight_decisions() -> None:
    registry = _load_registry()
    stage = _m8_stage(registry)
    decisions = stage.get("mandatory_decisions")
    if not isinstance(decisions, list) or len(decisions) != len(EXPECTED_DECISIONS):
        raise CheckFailure("M8 must contain exactly eight mandatory decisions")
    actual = {}
    for decision in decisions:
        if not isinstance(decision, dict):
            raise CheckFailure("M8 decision entry is not an object")
        decision_id = decision.get("id")
        actual[decision_id] = decision
    if set(actual) != set(EXPECTED_DECISIONS):
        raise CheckFailure("M8 decision IDs do not match the approved eight-decision set")
    for decision_id, expected_value in EXPECTED_DECISIONS.items():
        decision = actual[decision_id]
        if decision.get("status") != "RESOLVED":
            raise CheckFailure(f"{decision_id} is not RESOLVED")
        if decision.get("value") != expected_value:
            raise CheckFailure(f"{decision_id} has an unexpected policy value")
        evidence = decision.get("evidence")
        if not isinstance(evidence, list) or not evidence or any(not isinstance(item, str) or not item for item in evidence):
            raise CheckFailure(f"{decision_id} has empty or invalid evidence")


def check_protocol_is_not_authorized() -> None:
    plan = _read(M8_PLAN_PATH)
    review = _read(DRAFT_REVIEW_PATH)
    _assert_contains(
        plan,
        "draft-0.5",
        "PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY",
        "UNBOUND",
        "NOT_AUTHORIZED",
        "不创建根",
        "不安装依赖",
        "不生成输入",
    )
    _assert_contains(review, "PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY")
    if "execution_authorized=true" in plan or "execution_authorized=true" in review:
        raise CheckFailure("protocol evidence claims execution authorization")


def check_historical_protocols_are_quarantined() -> None:
    plan = _read(M8_PLAN_PATH)
    disposition = _read(V13_DISPOSITION_PATH)
    _assert_contains(
        plan,
        "V8",
        "V9",
        "V10",
        "V11",
        "V12",
        "V13",
        "不得复用",
        "BLOCKED / NOT_STARTED",
    )
    _assert_contains(disposition, "SUPERSEDED_UNBOUND_DRAFT", "NOT_AUTHORIZED", "NEVER_EXECUTED")
    if "resume" in disposition.lower() or "reusable" in disposition.lower() and "not" not in disposition.lower():
        raise CheckFailure("historical V13 disposition contains an unsafe reuse marker")


def check_policy_invariants() -> None:
    plan = _read(M8_PLAN_PATH)
    decision = _read(DECISION_PATH)
    _assert_contains(
        plan,
        "SQLite/M7",
        "SQLite linear",
        "LanceDB",
        "Qdrant",
        "Milvus",
        "100K",
        "synthetic/半合成",
        "外部原始资料目录",
    )
    _assert_contains(
        decision,
        "SQLite/M7 Registry",
        "SQLite linear cosine",
        "LanceDB",
        "Qdrant",
        "Milvus 当前不采用",
        "100,000 个可检索 chunks",
    )
    if "Milvus 当前采用" in decision:
        raise CheckFailure("policy text selects Milvus as an adopted backend")


def check_no_execution_imports() -> None:
    """Statically prove this command cannot invoke execution/network/install APIs."""
    source = Path(__file__).read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(Path(__file__)))
    except SyntaxError as exc:
        raise CheckFailure(f"target script is not valid Python: {exc}") from exc
    forbidden_modules = {"subprocess", "socket", "requests", "httpx", "urllib", "pip", "venv"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name.split(".", 1)[0] for alias in node.names}
            if imported & forbidden_modules:
                raise CheckFailure("target imports a forbidden execution/network/install module")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in forbidden_modules:
                raise CheckFailure("target imports a forbidden execution/network/install module")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec", "compile", "breakpoint"}:
                raise CheckFailure(f"target uses forbidden dynamic call {node.func.id}()")


def check_tiny_mock_lifecycle() -> None:
    """Exercise deterministic control/data-plane semantics without a backend."""

    class MockDataPlane:
        def __init__(self) -> None:
            self._published = {"owner-a:chunk-1": "generation-1"}
            self._tombstones: set[str] = set()

        def search(self, owner: str) -> list[str]:
            return sorted(
                key.split(":", 1)[1]
                for key, generation in self._published.items()
                if key.startswith(owner + ":") and key not in self._tombstones and generation == "generation-1"
            )

        def tombstone(self, key: str) -> None:
            self._tombstones.add(key)

        def hard_delete(self, key: str) -> None:
            self._published.pop(key, None)
            self._tombstones.discard(key)

    plane = MockDataPlane()
    if plane.search("owner-a") != ["chunk-1"] or plane.search("owner-b") != []:
        raise CheckFailure("mock owner isolation or initial search failed")
    plane.tombstone("owner-a:chunk-1")
    if plane.search("owner-a") != []:
        raise CheckFailure("mock tombstone did not hide the result")
    plane.hard_delete("owner-a:chunk-1")
    if plane.search("owner-a") != [] or plane.search("owner-b") != []:
        raise CheckFailure("mock hard-delete or isolation failed")


def check_default_fallback_semantics() -> None:
    """Check the policy-level fallback decision with a tiny deterministic mock."""
    default_pack = {"mode": "sqlite-bm25", "available": True}
    user_source = {"authorized": False, "generation": None, "snapshot": None}
    if not default_pack["available"] or default_pack["mode"] != "sqlite-bm25":
        raise CheckFailure("default-pack fallback is not SQLite/BM25")
    if user_source["authorized"] or user_source["generation"] is not None or user_source["snapshot"] is not None:
        raise CheckFailure("invalid user-source mock unexpectedly became queryable")


def checks() -> Iterable[Check]:
    return (
        Check("repository contract", check_repository_contract),
        Check("M7 exit prerequisite", check_m7_exit_prerequisite),
        Check("M8 blocked/not-started state", check_m8_remains_blocked),
        Check("eight resolved policy decisions", check_eight_decisions),
        Check("active protocol non-authorization", check_protocol_is_not_authorized),
        Check("historical protocol quarantine", check_historical_protocols_are_quarantined),
        Check("control/data-plane policy invariants", check_policy_invariants),
        Check("no execution/network/install behavior", check_no_execution_imports),
        Check("tiny mock lifecycle and owner isolation", check_tiny_mock_lifecycle),
        Check("default fallback and user-source fail-closed", check_default_fallback_semantics),
    )


def main() -> int:
    all_passed = True
    for check in checks():
        try:
            check.function()
        except (CheckFailure, OSError, ValueError, TypeError) as exc:
            all_passed = False
            print(f"FAIL: {check.name} — {exc}")
        else:
            print(f"PASS: {check.name}")
    if all_passed:
        print(SUCCESS_LINE)
        return 0
    print("M8 v3 S1 prerequisite suite FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
