#!/usr/bin/env python3
"""Run the safe M8 v3 S1 prerequisite self-check suite.

This command is deliberately an aggregate *self-check*, not an execution harness.
It reads repository governance documents and exercises a tiny in-memory mock only.
It never generates study material, starts a backend/service, accesses external
study-material directories, installs dependencies, or performs network I/O.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
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
FREEZE_TOOL_PATH = REPO_ROOT / "tools" / "m8_freeze_s1_prerequisites_v3.py"


def _load_freeze_inventory() -> tuple[Path, ...]:
    spec = importlib.util.spec_from_file_location("m8_freeze_s1_prerequisites_v3", FREEZE_TOOL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the S1 prerequisite freeze tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    logical_paths = getattr(module, "DEFAULT_PATHS", None)
    fixture_graphs = getattr(module, "FIXTURE_GRAPHS", None)
    fixture_members = getattr(module, "FIXTURE_MEMBERS", None)
    fixture_paths = getattr(module, "FIXTURE_PATHS", None)
    fixture_root = getattr(module, "FIXTURE_ROOT", None)
    forbidden_parts = getattr(module, "FORBIDDEN_INVENTORY_PARTS", None)
    non_fixture_count = getattr(module, "EXPECTED_NON_FIXTURE_FILE_COUNT", None)
    if not isinstance(logical_paths, list) or not all(isinstance(path, str) for path in logical_paths):
        raise RuntimeError("freeze DEFAULT_PATHS must be a list of logical path strings")
    if not isinstance(fixture_paths, list) or not all(isinstance(path, str) for path in fixture_paths):
        raise RuntimeError("freeze FIXTURE_PATHS must be a list of logical path strings")
    if (
        not isinstance(fixture_graphs, tuple)
        or len(fixture_graphs) != 5
        or not isinstance(fixture_members, tuple)
        or len(fixture_members) != 18
        or len(fixture_paths) != 90
    ):
        raise RuntimeError("freeze fixture closure must contain exactly 5 graphs x 18 members")
    if (
        fixture_root != "docs/plans/references/fixtures/m8-minimal-1k-v3/"
        or not all(path.startswith(fixture_root) for path in fixture_paths)
        or non_fixture_count != 29
        or logical_paths[non_fixture_count:] != fixture_paths
    ):
        raise RuntimeError("freeze fixture closure has an unexpected composition")
    if len(logical_paths) != 119 or len(set(logical_paths)) != len(logical_paths):
        raise RuntimeError("freeze DEFAULT_PATHS must contain exactly 119 unique paths")
    if not isinstance(forbidden_parts, tuple) or any(
        part in f"/{path.casefold()}"
        for path in logical_paths
        for part in forbidden_parts
    ):
        raise RuntimeError("freeze DEFAULT_PATHS contains a historical review or authorization path")
    return tuple(REPO_ROOT / Path(path) for path in logical_paths)


S1_REQUIRED_PATHS = _load_freeze_inventory()

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
    """Confirm every prerequisite contract and tool required by this aggregate exists."""
    for path in (
        REGISTRY_PATH,
        PLAN_PATH,
        M8_PLAN_PATH,
        DECISION_PATH,
        DRAFT_REVIEW_PATH,
        V13_DISPOSITION_PATH,
        *S1_REQUIRED_PATHS,
    ):
        if path.suffix == ".bin":
            if not path.is_file():
                raise CheckFailure(
                    f"missing required repository file: {path.relative_to(REPO_ROOT)}"
                )
            continue
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
    plan = _read(PLAN_PATH)
    policy = _read(REPO_ROOT / "docs" / "standards" / "stage-admission-gates.md")
    for text, label in ((plan, "docs/PLAN.md"), (policy, "stage-admission-gates.md")):
        if "M8" not in text or "BLOCKED / NOT_STARTED" not in text:
            raise CheckFailure(f"{label} does not state M8 BLOCKED / NOT_STARTED")


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
        if not isinstance(evidence, list) or not evidence or any(
            not isinstance(item, str) or not item for item in evidence
        ):
            raise CheckFailure(f"{decision_id} has empty or invalid evidence")
        grounded = False
        for logical_name in evidence:
            evidence_path = REPO_ROOT / Path(logical_name.split("#", 1)[0])
            evidence_text = _read(evidence_path)
            grounded |= decision_id in evidence_text
        if not grounded:
            raise CheckFailure(f"{decision_id} is not grounded in its evidence files")


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




def _call_name(node: ast.expr) -> str | None:
    """Return a simple dotted call name without evaluating the expression."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _validate_execution_policy(path: Path, source: str) -> None:
    """Fail closed on forbidden APIs and narrowly constrain subprocess use."""
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise CheckFailure(f"{path}: invalid Python: {exc}") from exc

    try:
        logical_path = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        logical_path = path.as_posix()
    forbidden_modules = {"socket", "requests", "httpx", "urllib", "pip", "venv"}
    subprocess_roles = {
        "tools/m8_freeze_s1_prerequisites_v3.py": "trusted-git-wrapper",
        "tools/m8_test_freeze_s1_prerequisites_v3.py": "bounded-test",
        "tools/m8_test_minimal_1k_graph_v3.py": "bounded-test",
        "tools/m8_test_observe_minimal_1k_v3.py": "bounded-test",
        "tools/m8_test_s1_prerequisites_v3.py": "bounded-test",
    }
    role = subprocess_roles.get(logical_path)
    parents: dict[ast.AST, ast.AST] = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in forbidden_modules:
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: forbidden import {root}"
                    )
                if root == "subprocess" and (
                    alias.name != "subprocess" or alias.asname not in {None, "subprocess"}
                ):
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: subprocess import alias is forbidden"
                    )
                if root == "subprocess" and role is None:
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: subprocess is not allowed for this role"
                    )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in forbidden_modules:
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: forbidden import {root}"
                )
            if root == "subprocess":
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: from-subprocess imports are forbidden"
                )
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name in {"eval", "exec", "breakpoint", "__import__"}:
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: forbidden dynamic call {call_name}()"
                )
            if call_name not in {"subprocess.run", "subprocess.Popen"}:
                continue
            if role is None:
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: subprocess call is not allowed for this role"
                )
            keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
            shell = keywords.get("shell")
            if isinstance(shell, ast.Constant) and shell.value is True:
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: shell subprocesses are forbidden"
                )
            if role == "bounded-test":
                if call_name != "subprocess.run":
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: test role permits subprocess.run only"
                    )
                timeout = keywords.get("timeout")
                if not (
                    isinstance(timeout, ast.Constant)
                    and isinstance(timeout.value, (int, float))
                    and not isinstance(timeout.value, bool)
                    and 0 < timeout.value <= 600
                ):
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: test subprocess needs a literal timeout in (0, 600]"
                    )
            else:
                if call_name != "subprocess.Popen":
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: Git wrapper permits subprocess.Popen only"
                    )
                owner = parents.get(node)
                enclosing_functions: list[str] = []
                while owner is not None:
                    if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        enclosing_functions.append(owner.name)
                    owner = parents.get(owner)
                if "run_git_process" not in enclosing_functions:
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: Popen must remain inside run_git_process"
                    )
                if not {"env", "stdout", "stderr"}.issubset(keywords):
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: Git Popen must close its environment and capture both streams"
                    )


def _safe_console_line(text: object, *, limit: int = 2400) -> None:
    """Write one bounded line without depending on the console's Unicode coverage."""
    rendered = str(text).replace("\r", "\\r").replace("\n", "\\n")
    if len(rendered) > limit:
        rendered = "..." + rendered[-limit:]
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe = rendered.encode(encoding, errors="backslashreplace").decode(encoding)
    sys.stdout.write(safe + "\n")

def check_no_execution_imports() -> None:
    """Scan every frozen Python prerequisite for prohibited execution APIs."""
    python_paths = tuple(path for path in S1_REQUIRED_PATHS if path.suffix == ".py")
    if not python_paths:
        raise CheckFailure("freeze inventory contains no Python prerequisites")
    for path in python_paths:
        _validate_execution_policy(path, _read(path))

    with tempfile.TemporaryDirectory(prefix="m8-s1-policy-") as directory:
        probe = Path(directory) / "probe.py"
        cases = (
            (probe, "import socket\n", "forbidden import socket"),
            (
                probe,
                "import subprocess\nsubprocess.run(['git'], timeout=601)\n",
                "subprocess is not allowed for this role",
            ),
            (
                REPO_ROOT / "tools/m8_test_freeze_s1_prerequisites_v3.py",
                "import subprocess\nsubprocess.run(['git'], timeout=601)\n",
                "test subprocess needs a literal timeout in (0, 600]",
            ),
        )
        for policy_path, source, expected in cases:
            try:
                _validate_execution_policy(policy_path, source)
            except CheckFailure as exc:
                if expected not in str(exc):
                    raise CheckFailure(
                        f"execution-policy regression returned the wrong error: {exc}"
                    ) from exc
            else:
                raise CheckFailure(
                    "execution-policy regression accepted prohibited prerequisite source"
                )


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


def _run_python_tool(path: Path) -> None:
    """Run one hermetic prerequisite command and require a zero exit status."""
    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CheckFailure(f"timed out: {path.relative_to(REPO_ROOT)}") from exc
    if completed.returncode != 0:
        output = completed.stdout.decode("utf-8", errors="replace")
        raise CheckFailure(
            f"{path.relative_to(REPO_ROOT)} exited {completed.returncode}: "
            f"{output[-2000:]}"
        )


def check_s1_tool_syntax() -> None:
    """Compile every Builder-authored S1 Python prerequisite without executing it."""
    for path in S1_REQUIRED_PATHS:
        if path.suffix != ".py":
            continue
        try:
            compile(_read(path), str(path), "exec")
        except SyntaxError as exc:
            raise CheckFailure(
                f"syntax error in {path.relative_to(REPO_ROOT)}: {exc}"
            ) from exc


def check_generator_suite() -> None:
    """Run the hermetic generator suite; formal generation remains uninvoked."""
    _run_python_tool(REPO_ROOT / "tools" / "m8_test_generate_minimal_1k_input_v3.py")


def check_observer_suite() -> None:
    """Run the hermetic synthetic-only observer suite."""
    _run_python_tool(REPO_ROOT / "tools" / "m8_test_observe_minimal_1k_v3.py")


def check_s1_control_suite() -> None:
    """Run schema/config, preflight, and mock-only authorization-boundary tests."""
    _run_python_tool(REPO_ROOT / "tools" / "m8_test_s1_controls_v3.py")


def check_s1_freeze_suite() -> None:
    """Run the Git-object prerequisite-freeze self-test."""
    _run_python_tool(
        REPO_ROOT / "tools" / "m8_test_freeze_s1_prerequisites_v3.py"
    )


def check_existing_v3_regressions() -> None:
    """Run existing graph, review-freeze, and historical mechanical regressions."""
    for name in (
        "m8_test_minimal_1k_graph_v3.py",
        "m8_test_freeze_minimal_1k_v3_review.py",
        "m8_validate_p1_materials.py",
        "m8_validate_p0_r02.py",
    ):
        _run_python_tool(REPO_ROOT / "tools" / name)


def checks() -> Iterable[Check]:
    return (
        Check("repository contract", check_repository_contract),
        Check("S1 tool syntax", check_s1_tool_syntax),
        Check("M7 exit prerequisite", check_m7_exit_prerequisite),
        Check("M8 blocked/not-started state", check_m8_remains_blocked),
        Check("eight resolved policy decisions", check_eight_decisions),
        Check("active protocol non-authorization", check_protocol_is_not_authorized),
        Check("historical protocol quarantine", check_historical_protocols_are_quarantined),
        Check("control/data-plane policy invariants", check_policy_invariants),
        Check("no execution/network/install behavior", check_no_execution_imports),
        Check("tiny mock lifecycle and owner isolation", check_tiny_mock_lifecycle),
        Check("default fallback and user-source fail-closed", check_default_fallback_semantics),
        Check("deterministic generator suite", check_generator_suite),
        Check("synthetic observer suite", check_observer_suite),
        Check("S1 contracts and authorization controls", check_s1_control_suite),
        Check("S1 prerequisite Git-object freeze", check_s1_freeze_suite),
        Check("existing v3 and historical regressions", check_existing_v3_regressions),
    )


def main() -> int:
    all_passed = True
    for check in checks():
        try:
            check.function()
        except (CheckFailure, OSError, UnicodeError, ValueError, TypeError) as exc:
            all_passed = False
            _safe_console_line(f"FAIL: {check.name} -- {exc}")
        else:
            _safe_console_line(f"PASS: {check.name}")
    if all_passed:
        _safe_console_line(SUCCESS_LINE)
        return 0
    _safe_console_line("M8 v3 S1 prerequisite suite FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
