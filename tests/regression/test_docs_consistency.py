"""跨文档耐久事实一致性契约。"""

from __future__ import annotations

import json
import re


# docs/PLAN.md 里程碑表的一行：`| M9 | `ADMITTED` | `IN_PROGRESS` | ... |`
_MILESTONE_ROW = re.compile(
    r"^\|\s*(M\d+[a-z]?)\s*\|\s*`([A-Z_]+)`\s*\|\s*`([A-Z_]+)`\s*\|"
)

# 导航文档里的「当前状态」断言：阶段名、`A / D` 状态对、`M8–M12` 形式的区间与阻断表述。
_STAGE_NAME = re.compile(r"\bM(?:6a|6b|7|8|9|10|11|12)\b")
_STAGE_RANGE = re.compile(r"M(\d+)\s*[–\-]\s*M(\d+)")
# 阻断表述：中文「阻断」，或与登记表 `BLOCKED` + `NOT_STARTED` 逐字相同的状态对。
_BLOCKED_CLAIM = re.compile(r"阻断|`BLOCKED / NOT_STARTED`")


def _state_pair_pattern(registry: dict) -> re.Pattern:
    """只匹配**准入 / 交付状态对**，词表直接取自登记表。

    刻意不是 `\\`([A-Z_]+) / ([A-Z_]+)\\``：那会连 `FAILED / RETURNED`、`REJECTED / stop`
    这类**协议链处置**一并捕获，把 M8 的失败链叙述误判成阶段状态断言。
    """
    admission = "|".join(registry["admission_statuses"])
    delivery = "|".join(registry["delivery_statuses"])
    return re.compile(rf"`((?:{admission}) / (?:{delivery}))`")


def _paragraphs(text: str):
    """按空行切段，逐段返回 `(起始行号, 段落文本)`。

    表格行各自成段：连续的表格行是**多条独立断言**，合在一起会把前一行的阶段名
    误当成后一行状态对的归属者（`docs/plans/README.md` 的计划表即如此）。
    """
    blocks = []
    start = 1
    current: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("|"):
            if current:
                blocks.append((start, "\n".join(current)))
                current = []
            blocks.append((lineno, line))
        elif line.strip():
            if not current:
                start = lineno
            current.append(line)
        elif current:
            blocks.append((start, "\n".join(current)))
            current = []
    if current:
        blocks.append((start, "\n".join(current)))
    return blocks


def _line_of(paragraph: str, start: int, offset: int) -> int:
    """把段落内偏移换算回文件行号，便于报错定位。"""
    return start + paragraph.count("\n", 0, offset)


def _logical_lines(paragraph: str):
    """把 markdown 软换行拼回逻辑行，逐行返回 `(行内偏移, 文本)`。

    本仓的换行惯例是「列表项 / 标题 / 表格行顶格，句子续行缩进」，故**缩进行**属上一行的
    同一句。不拼接会让区间规则读到下一行的阶段名而误判归属——那正是它一度空转的原因。
    """
    lines = paragraph.splitlines()
    joined: list[list] = []
    offset = 0
    for line in lines:
        if joined and line[:1].isspace():
            joined[-1][1] += line.strip()
        else:
            joined.append([offset, line])
        offset += len(line) + 1
    return [(position, text) for position, text in joined]


def _read(repo_root, relative_path: str) -> str:
    return (repo_root / relative_path).read_text(encoding="utf-8")


def _load_admission_registry(repo_root) -> dict:
    return json.loads(
        _read(repo_root, "docs/standards/stage-admission-gates.json")
    )


class TestProjectStatusConsistency:
    def test_m6_status_and_capability_boundary(self, repo_root):
        root = _read(repo_root, "README.md")
        plan = _read(repo_root, "docs/PLAN.md")

        assert "M6a-P0 crawler 已收口" in root
        assert "M6a、M6b、M7 均为 `ADMITTED / COMPLETE`" in plan
        assert "M6a、M6b、M7 均为 `ADMITTED / COMPLETE`" in root
        assert "M8 与 M10–M12" in root
        assert "M6–M12" in plan
        for text in (root, plan):
            assert "BLOCKED / NOT_STARTED" in text
        assert "ADMITTED / COMPLETE" in root
        assert "M6a 契约与兼容骨架" in root
        assert "M7 生产开工门禁保持" in root
        assert "独立人工完成批准" in root
        assert "M8–M10 的事实型" in root
        assert "M7 退出前置已满足" in root
        assert "M8 与 M10–M12 仍为 `BLOCKED / NOT_STARTED`" in root
        assert "M9 八项 Decision 已 `RESOLVED`" in root
        assert "M0–M5 MVP 可用。" in root
        assert "M10" in root and "自主 Runner" in root
        assert "课程笔记创建" not in root
        assert "错题集管理" not in root
        assert "crawler 候选默认不检索" in root

    def test_current_routes_are_documented(self, repo_root):
        root = _read(repo_root, "README.md")
        platform = _read(repo_root, "platform/README.md")
        routes = (
            "/api/v1/search",
            "/api/v1/qa",
            "/api/v1/qa/stream",
            "/api/v1/review-plan",
            "/api/v1/quiz",
            "/api/v1/review-log",
            "/api/v1/review-due",
            "/api/v1/study-sessions",
        )
        for route in routes:
            assert route in root
            assert route in platform


class TestStorageAndBaselineConsistency:
    def test_current_and_future_storage_are_separated(self, repo_root):
        root = _read(repo_root, "README.md")
        plan = _read(repo_root, "docs/PLAN.md")
        platform = _read(repo_root, "platform/README.md")

        for text in (root, plan, platform):
            assert "SqliteVectorStore" in text
            assert "LocalVectorStore" in text
            assert "线性余弦" in text
            assert "M8" in text
            assert "LanceDB" in text
            assert "Qdrant" in text
        assert "learning_state.sqlite3" in plan
        assert "learning_state.sqlite3" in platform
        assert "review_history.json" in platform
        assert "兼容读取" in platform

    def test_historical_and_current_baselines_coexist(self, repo_root):
        baselines = _read(repo_root, "docs/baselines.md")
        root = _read(repo_root, "README.md")

        assert "2026-08-18" in baselines
        assert "历史基线" in baselines
        assert "2026-08-24" in baselines
        assert "当前 checkout 复测" in baselines
        assert "0.987" in baselines
        assert "0.972" in baselines
        assert "治理冻结复测 — 2026-08-31" in baselines
        assert "OS `1.000`、DS `0.929`、CO `1.000`" in baselines
        assert "OS 1.000" in root
        assert "加权 0.978" in root

    def test_default_evaluation_excludes_network(self, repo_root):
        tools = _read(repo_root, "tools/README.md")
        plan = _read(repo_root, "docs/PLAN.md")

        for text in (tools, plan):
            assert "OS/DS/CO" in text
            assert "90 题" in text
            assert "Network" in text
        assert "不自动发现" in tools
        assert "Network 30 题仍为显式扩展集" in plan


class TestVersionSemantics:
    def test_package_version_is_tooling_metadata(self, repo_root):
        package = json.loads(_read(repo_root, "package.json"))
        assert package["private"] is True
        assert "Commitizen" in package["description"]
        assert "非产品版本" in package["description"]

        plan = _read(repo_root, "docs/PLAN.md")
        assert "PLAN 文档修订" in plan
        assert "不是产品发布版本" in plan


class TestStageAdmissionConsistency:
    EXPECTED_STAGES = (
        "M6a",
        "M6b",
        "M7",
        "M8",
        "M9",
        "M10",
        "M11",
        "M12",
    )
    APPROVAL_FIELDS = (
        "approved_by",
        "approved_at",
        "approval_reference",
        "plan_revision",
        "decision_set_version",
    )
    APPROVAL_SCOPE_FIELDS = ("scope_id", "included", "excluded")
    IMPLEMENTATION_START_FIELDS = (
        "status",
        "authorized_by",
        "authorized_at",
        "authorization_reference",
    )
    # 承载「当前状态」断言的导航/政策文档。不含 `docs/PLAN.md`（另有里程碑表护栏，且正文混有
    # append-only 修订日志）与 `docs/plans/references/`（历史治理记录，只读且不得改写）。
    CURRENT_STATE_DOCS = (
        "README.md",
        "docs/README.md",
        "docs/plans/README.md",
        "docs/prds/README.md",
        "docs/standards/stage-admission-gates.md",
    )

    def test_registry_schema_status_and_plan_files(self, repo_root):
        registry = _load_admission_registry(repo_root)

        assert registry["schema_version"] == 2
        implementation_start_statuses = set(
            registry["implementation_start_statuses"]
        )
        assert implementation_start_statuses == {
            "NOT_AUTHORIZED",
            "AUTHORIZED",
        }
        assert registry["authority"] == "docs/PLAN.md"
        assert registry["policy"] == "docs/standards/stage-admission-gates.md"
        assert (repo_root / registry["authority"]).is_file()
        assert (repo_root / registry["policy"]).is_file()

        decision_statuses = set(registry["decision_statuses"])
        admission_statuses = set(registry["admission_statuses"])
        delivery_statuses = set(registry["delivery_statuses"])
        prerequisite_statuses = set(registry["prerequisite_statuses"])
        assert decision_statuses == {"OPEN", "RESOLVED"}
        assert admission_statuses == {"BLOCKED", "ADMITTED", "REVOKED"}
        assert delivery_statuses == {"NOT_STARTED", "IN_PROGRESS", "COMPLETE"}
        assert prerequisite_statuses == {"OPEN", "SATISFIED"}

        stages = registry["stages"]
        assert [stage["stage"] for stage in stages] == list(self.EXPECTED_STAGES)
        assert len({stage["stage"] for stage in stages}) == len(stages)

        prerequisite_ids: set[str] = set()
        for stage in stages:
            assert stage["admission_status"] in admission_statuses
            assert stage["delivery_status"] in delivery_statuses
            assert (repo_root / stage["plan"]).is_file()
            assert stage["mandatory_decisions"]
            assert stage["prerequisites"]
            plan = _read(repo_root, stage["plan"])
            for prerequisite in stage["prerequisites"]:
                prerequisite_id = prerequisite["id"]
                assert prerequisite_id
                assert prerequisite_id not in prerequisite_ids
                prerequisite_ids.add(prerequisite_id)
                assert prerequisite_id in plan
                assert prerequisite["status"] in prerequisite_statuses
                if prerequisite["status"] == "SATISFIED":
                    assert prerequisite["evidence"]

    def test_decision_ids_and_admission_invariants(self, repo_root):
        registry = _load_admission_registry(repo_root)
        decision_statuses = set(registry["decision_statuses"])
        implementation_start_statuses = set(
            registry["implementation_start_statuses"]
        )
        seen_ids: set[str] = set()
        seen_scope_ids: set[str] = set()

        for stage in registry["stages"]:
            plan = _read(repo_root, stage["plan"])
            decisions = stage["mandatory_decisions"]
            has_open = False

            for decision in decisions:
                decision_id = decision["id"]
                assert decision_id
                assert decision_id not in seen_ids
                seen_ids.add(decision_id)
                assert decision["status"] in decision_statuses
                assert decision_id in plan

                if decision["status"] == "OPEN":
                    has_open = True
                else:
                    assert decision["value"] not in (None, "", "TBD")
                    assert not isinstance(decision["value"], list)
                    assert decision["evidence"]

            admission = stage["admission_status"]
            delivery = stage["delivery_status"]
            prerequisites = stage["prerequisites"]
            approval = stage["approval"]
            assert set(approval) == set(self.APPROVAL_FIELDS)

            approval_scope = stage.get("approval_scope")
            if approval_scope is not None:
                assert set(approval_scope) == set(self.APPROVAL_SCOPE_FIELDS)
                scope_id = approval_scope["scope_id"]
                included = approval_scope["included"]
                excluded = approval_scope["excluded"]
                assert isinstance(scope_id, str) and scope_id.strip()
                assert scope_id not in seen_scope_ids
                seen_scope_ids.add(scope_id)
                assert isinstance(included, list) and included
                assert isinstance(excluded, list) and excluded
                assert all(isinstance(item, str) and item.strip() for item in included)
                assert all(isinstance(item, str) and item.strip() for item in excluded)
                assert len(included) == len(set(included))
                assert len(excluded) == len(set(excluded))
                assert set(included).isdisjoint(excluded)

            implementation_start = stage.get("implementation_start")
            if implementation_start is not None:
                assert set(implementation_start) == set(
                    self.IMPLEMENTATION_START_FIELDS
                )
                start_status = implementation_start["status"]
                assert start_status in implementation_start_statuses
                authorization_fields = self.IMPLEMENTATION_START_FIELDS[1:]
                if start_status == "AUTHORIZED":
                    assert admission == "ADMITTED"
                    assert all(
                        implementation_start[field]
                        for field in authorization_fields
                    )
                else:
                    assert delivery == "NOT_STARTED"
                    assert all(
                        implementation_start[field] is None
                        for field in authorization_fields
                    )

            if delivery == "IN_PROGRESS":
                assert admission == "ADMITTED"
            if admission == "BLOCKED":
                assert delivery == "NOT_STARTED"
            if admission == "REVOKED":
                assert delivery != "IN_PROGRESS"
            if has_open:
                assert admission != "ADMITTED"
                assert delivery != "IN_PROGRESS"

            if admission == "ADMITTED":
                assert all(decision["status"] == "RESOLVED" for decision in decisions)
                assert all(
                    prerequisite["status"] == "SATISFIED"
                    and prerequisite["evidence"]
                    for prerequisite in prerequisites
                )
                assert all(approval[field] for field in self.APPROVAL_FIELDS)
            elif not all(approval[field] for field in self.APPROVAL_FIELDS):
                assert admission == "BLOCKED"

    def test_m6b_and_m7_are_independent_sibling_stages(self, repo_root):
        stages = {
            stage["stage"]: stage
            for stage in _load_admission_registry(repo_root)["stages"]
        }
        m6b = stages["M6b"]
        m7 = stages["M7"]
        m6b_prerequisites = {item["id"] for item in m6b["prerequisites"]}
        m7_prerequisites = {item["id"] for item in m7["prerequisites"]}

        assert m6b_prerequisites == {
            "M6B-M6A-EXIT",
            "M6B-PROTECTED-BASELINE",
        }
        assert m7_prerequisites == {
            "M7-M6A-SOURCE-CONTRACT",
            "M7-PROTECTED-BASELINE",
        }
        assert not any("M7" in item for item in m6b_prerequisites)
        assert not any("M6B" in item for item in m7_prerequisites)

        assert m6b["admission_status"] == "ADMITTED"
        assert m6b["delivery_status"] == "COMPLETE"
        assert m6b["approval"] == {
            "approved_by": "justtodo123",
            "approved_at": "2026-08-27",
            "approval_reference": (
                "docs/plans/m6b-agent-core-plan.md#03-全量准入检查与批准"
            ),
            "plan_revision": "v2.1",
            "decision_set_version": "m6b-decision-set-v1",
        }

        assert m7["admission_status"] == "ADMITTED"
        assert m7["delivery_status"] == "COMPLETE"
        assert m7["approval_scope"] == {
            "scope_id": "m7-infrastructure-only-v1",
            "included": [
                "m7.source-lifecycle-infrastructure",
                "m7.provenance-manifest-parser-infrastructure",
                "m7.sync-delete-isolation-infrastructure",
                "m7.fts5-offline-fallback-infrastructure",
                "m7.1k-3k-benchmark-implementation",
            ],
            "excluded": [
                "network.document-promotion",
                "network.corpus-governance-closure",
                "corpus.automatic-approval",
                "m8.specialized-storage",
                "milvus.backend-selection",
            ],
        }
        assert m7["implementation_start"] == {
            "status": "AUTHORIZED",
            "authorized_by": "justtodo123",
            "authorized_at": "2026-08-31",
            "authorization_reference": (
                "User instruction: 批准开始实施 M7 基础设施，按 M7-1 Source Registry 起步；排除 Network 31 篇晋升、M8/Milvus、M9/M10，不修改已冻结治理结论。"
            ),
        }
        assert m7["approval"] == {
            "approved_by": "justtodo123",
            "approved_at": "2026-08-31",
            "approval_reference": (
                "User instruction: M7 基础设施可以获批；Network 数据仍不获批；M8/Milvus 继续阻断"
            ),
            "plan_revision": "v2.11",
            "decision_set_version": "m7-decision-set-v1",
        }
        assert m7["completion_approval"] == {
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
        assert len(m7["mandatory_decisions"]) == 12
        m7_decisions = {
            decision["id"]: decision["status"]
            for decision in m7["mandatory_decisions"]
        }
        assert m7_decisions == {
            "M7-LIFECYCLE-SCHEMA": "RESOLVED",
            "M7-SYNC-SEMANTICS": "RESOLVED",
            "M7-DELETE-SEMANTICS": "RESOLVED",
            "M7-ISOLATION": "RESOLVED",
            "M7-FTS5-TOKENIZER": "RESOLVED",
            "M7-SCALE-LIMITS": "RESOLVED",
            "M7-BENCHMARK": "RESOLVED",
            "M7-OFFLINE-FALLBACK": "RESOLVED",
            "M7-SOURCE-MANIFEST": "RESOLVED",
            "M7-PARSER-MATRIX": "RESOLVED",
            "M7-NORMALIZED-DOCUMENT": "RESOLVED",
            "M7-PROVENANCE": "RESOLVED",
        }
        m7_baseline = next(
            prerequisite
            for prerequisite in m7["prerequisites"]
            if prerequisite["id"] == "M7-PROTECTED-BASELINE"
        )
        assert m7_baseline == {
            "id": "M7-PROTECTED-BASELINE",
            "status": "SATISFIED",
            "evidence": [
                "docs/baselines.md",
                "docs/plans/m7-source-lifecycle-plan.md",
                "tests/TEST_PLAN.md",
                "tests/regression/test_path_privacy.py",
            ],
        }

        downstream = {
            "M8": "M8-M7-EXIT",
            "M10": "M10-M7-EXIT",
        }
        expected_exit_evidence = [
            "docs/PLAN.md",
            "docs/plans/m7-source-lifecycle-plan.md",
            "docs/baselines.md",
        ]
        for stage_name, prerequisite_id in downstream.items():
            stage = stages[stage_name]
            assert stage["admission_status"] == "BLOCKED"
            assert stage["delivery_status"] == "NOT_STARTED"
            m7_exit = next(
                prerequisite
                for prerequisite in stage["prerequisites"]
                if prerequisite["id"] == prerequisite_id
            )
            assert m7_exit == {
                "id": prerequisite_id,
                "status": "SATISFIED",
                "evidence": expected_exit_evidence,
            }
            assert all(value is None for value in stage["approval"].values())

        m9 = stages["M9"]
        assert m9["admission_status"] == "ADMITTED"
        # 2026-09-22 收口：owner 批准 M9 COMPLETE。本断言随事实移动，并**加强**为同时校验 §4 要求的
        # 独立完成批准——「完成批准不得覆盖原准入批准、不得扩大既有 approval_scope」。
        assert m9["delivery_status"] == "COMPLETE"
        completion = m9["completion_approval"]
        assert completion["approved_by"] == "justtodo123"
        assert completion["approved_at"]
        assert completion["approval_reference"].startswith("User instruction:")
        assert completion["approval_scope"] == m9["approval_scope"]["scope_id"]
        assert completion["evidence"]
        # 原准入批准（v1.5）不被完成批准覆盖：两条记录并存，准入引用仍是 v1.5 那条。
        assert m9["approval"]["plan_revision"] == "v1.5"
        m9_exit = next(
            prerequisite
            for prerequisite in m9["prerequisites"]
            if prerequisite["id"] == "M9-M7-EXIT"
        )
        assert m9_exit["status"] == "SATISFIED"
        assert m9["approval"]["approved_by"] == "justtodo123"
        assert m9["approval_scope"]["scope_id"] == "m9-plan-lifecycle-v1"
        assert m9["implementation_start"]["status"] == "AUTHORIZED"

        m8 = stages["M8"]
        expected_m8_decisions = {
            "M8-CONTROL-SCHEMA": (
                "SQLITE_M7_AUTHORITATIVE_CONTROL_PLANE__"
                "REBUILDABLE_SPECIALIZED_DATA_PLANE"
            ),
            "M8-MIGRATION": (
                "FROZEN_EXPORT__ISOLATED_BUILD__VALIDATE__"
                "SHADOW_READ__MANUAL_CUTOVER"
            ),
            "M8-LANCEDB-CRITERIA": (
                "PRIMARY_LOCAL_SPECIALIZED_CANDIDATE__"
                "OPT_IN_ONLY_AFTER_ALL_HARD_GATES"
            ),
            "M8-QDRANT-CRITERIA": (
                "NOT_A_LOCAL_DEFAULT__"
                "CLOUD_OR_SERVICE_TRIGGERED_CANDIDATE_ONLY"
            ),
            "M8-BACKEND-PARITY": (
                "ZERO_TOLERANCE_IDENTITY_AUTH_LIFECYCLE__"
                "FROZEN_SCORE_ORDER_TOLERANCE"
            ),
            "M8-FALLBACK": (
                "DEFAULT_PACK_SQLITE_BM25_FALLBACK__"
                "USER_SOURCE_FAIL_CLOSED"
            ),
            "M8-DEPENDENCY-PACKAGING": (
                "ISOLATED_OPTIONAL_EXTRAS__NO_MANDATORY_SERVICE_OR_NETWORK"
            ),
            "M8-BENCHMARK": (
                "1K_CORRECTNESS__10K_SINGLE_USER__100K_CAPACITY_FILTERED__"
                "OPTIONAL_CONCURRENCY"
            ),
        }
        actual_m8_decisions = {
            decision["id"]: decision
            for decision in m8["mandatory_decisions"]
        }
        assert set(actual_m8_decisions) == set(expected_m8_decisions)
        for decision_id, expected_value in expected_m8_decisions.items():
            decision = actual_m8_decisions[decision_id]
            assert decision["status"] == "RESOLVED"
            assert decision["value"] == expected_value
            assert decision["evidence"]

        assert m8["admission_status"] == "BLOCKED"
        assert m8["delivery_status"] == "NOT_STARTED"
        assert all(value is None for value in m8["approval"].values())
        assert m8.get("implementation_start") is None

    def test_m11_and_m12_contracts_and_historical_boundaries(self, repo_root):
        stages = {
            stage["stage"]: stage
            for stage in _load_admission_registry(repo_root)["stages"]
        }

        assert {
            item["id"] for item in stages["M11"]["prerequisites"]
        } == {
            "M11-M8-EXIT",
            "M11-M9-EXIT",
            "M11-M10-EXIT",
        }
        assert {
            item["id"] for item in stages["M11"]["mandatory_decisions"]
        } == {
            "M11-SCALE-GATES",
            "M11-SOURCE-ALLOWLIST",
            "M11-PARSER-QUALITY",
            "M11-CHUNK-POLICY",
            "M11-LICENSE-PROVENANCE",
            "M11-QUALITY-EVALUATION",
            "M11-RETRIEVAL-EVALUATION",
            "M11-PUBLICATION",
            "M11-INCREMENTAL-SYNC",
            "M11-PRIVACY-RETENTION",
        }

        assert {
            item["id"] for item in stages["M12"]["prerequisites"]
        } == {
            "M12-M8-EXIT",
            "M12-M9-EXIT",
            "M12-M10-EXIT",
            "M12-M11-EXIT",
        }
        assert {
            item["id"] for item in stages["M12"]["mandatory_decisions"]
        } == {
            "M12-SERVER-BASELINE",
            "M12-DEPLOYMENT-PROFILE",
            "M12-IDENTITY-AUTH",
            "M12-CONTROL-PLANE",
            "M12-VECTOR-DATA-PLANE",
            "M12-INGESTION-WORKER",
            "M12-STORAGE-BACKUP",
            "M12-PRIVACY-RESIDENCY",
            "M12-OBSERVABILITY",
            "M12-SECURITY-HARDENING",
            "M12-COST-CAPACITY",
            "M12-LOCAL-CLOUD-COMPAT",
            "M12-ROLLOUT-ROLLBACK",
        }

        for stage_name in ("M11", "M12"):
            stage = stages[stage_name]
            assert stage["admission_status"] == "BLOCKED"
            assert stage["delivery_status"] == "NOT_STARTED"
            assert stage.get("implementation_start") is None
            assert stage.get("completion_approval") is None
            assert all(value is None for value in stage["approval"].values())
            for item in stage["prerequisites"]:
                assert item["status"] == "OPEN"
                assert item.get("evidence", []) == []
            for decision in stage["mandatory_decisions"]:
                assert decision["status"] == "OPEN"
                assert decision["value"] is None
                assert decision.get("evidence", []) == []

        m8_plan = _read(repo_root, "docs/plans/m8-specialized-storage-plan.md")
        assert "active\nexecution protocol" in m8_plan
        assert "corpus" in m8_plan

        rounds = _read(
            repo_root,
            "docs/plans/references/m8-eleven-rounds-governance-review.md",
        )
        v7_protocol = _read(repo_root, "docs/plans/references/m8-v7-admission-protocol.md")
        v7_auth = _read(repo_root, "docs/plans/references/m8-v7-authorization-20260908.md")
        assert "V6 | `precommit-v6` | `ABORTED`" in rounds
        assert "DISK_PREFLIGHT_FAILED" in rounds
        assert "package_footprint_cap" in v7_protocol
        assert "实测+64 MiB" in v7_protocol
        assert "V7 | `precommit-v7` | `INVALID`" in rounds
        assert "probe 通过" in rounds
        assert "____________" in v7_auth
        assert "授权人" in v7_auth or "authorizer" in v7_auth.lower()

        assert "v6 因磁盘预算 `DISK_PREFLIGHT_FAILED` 以 `ABORTED`" in v7_protocol
        assert "证据无效" in v7_protocol
        assert "不得复用其 harness" in v7_protocol

        historical_failures = {
            "m8-v8-admission-protocol.md": ("`INVALID`", "不得继续或复用"),
            "m8-v9-admission-protocol.md": (
                "PRE_FREEZE_STATIC_AUDIT_FAILED",
                "永久冻结且不可复用",
            ),
            "m8-v10-admission-protocol.md": (
                "PRE_SOURCE_GOVERNANCE_INVALID",
                "根不可复用",
            ),
            "m8-v11-admission-protocol.md": (
                "PRE_SOURCE_PROVENANCE_INVALID",
                "永久不可复用",
            ),
            "m8-v12-admission-protocol.md": (
                "INDEPENDENT_STATIC_AUDIT_FAILED",
                "永久不可复用",
            ),
        }
        for filename, required_phrases in historical_failures.items():
            text = _read(repo_root, f"docs/plans/references/{filename}")
            for phrase in required_phrases:
                assert phrase in text

        v12 = _read(
            repo_root,
            "docs/plans/references/m8-v12-disposition-20260909.md",
        )
        v13 = _read(
            repo_root,
            "docs/plans/references/m8-v13-disposition-20260910.md",
        )
        v13_audit = _read(
            repo_root,
            "docs/plans/references/m8-v13-protocol-text-audit-20260910.md",
        )
        assert "INDEPENDENT_STATIC_AUDIT_FAILED" in v12
        assert "SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED" in v13
        assert "PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED" in v13_audit
        assert "从未产生 repository binding" in v13_audit
        assert "任何后续 M8 实证必须使用全新协议身份" in v13_audit

    def test_authority_and_navigation_match_registry_state(self, repo_root):
        registry = _load_admission_registry(repo_root)
        root = _read(repo_root, "README.md")
        plan = _read(repo_root, "docs/PLAN.md")
        docs = _read(repo_root, "docs/README.md")
        plans = _read(repo_root, "docs/plans/README.md")
        policy_path = "stage-admission-gates.md"

        for text in (root, plan, docs, plans):
            assert policy_path in text
        for stage in registry["stages"]:
            stage_plan = _read(repo_root, stage["plan"])
            current_state = (
                f'{stage["admission_status"]} / {stage["delivery_status"]}'
            )
            assert current_state in stage_plan
            assert stage["stage"] in plan

        current_states = {
            (stage["admission_status"], stage["delivery_status"])
            for stage in registry["stages"]
        }
        if len(current_states) == 1:
            admission, delivery = current_states.pop()
            aggregate_state = f"{admission} / {delivery}"
            for text in (root, plan, plans):
                assert aggregate_state in text

        for filename in (
            "m7-source-lifecycle-plan.md",
            "m8-specialized-storage-plan.md",
            "m9-goal-driven-planning-plan.md",
            "m10-autonomous-runner-plan.md",
            "m11-data-scaling-plan.md",
            "m12-cloud-deployment-plan.md",
        ):
            assert filename in docs
            assert filename in plans

        assert "Agent 不得自行批准" in plan
        assert "计划存在只代表设定澄清准备" in docs
        assert "不接管 `/api/v1/study-sessions`" in plan
        assert "状态机继续作为正式默认" in plan
        assert "无 LLM 降级路径" in plan

    def test_plan_milestone_table_matches_registry(self, repo_root):
        """`docs/PLAN.md` 是准入权威，其里程碑表必须与 JSON 登记表逐行一致。

        回归：M9 曾在登记表已改为 `ADMITTED / IN_PROGRESS` 后仍停留在
        `BLOCKED / NOT_STARTED`，权威文档因此失真，而既有断言只检查阶段名出现。
        """
        registry = _load_admission_registry(repo_root)
        plan = _read(repo_root, "docs/PLAN.md")

        rows: dict[str, tuple[str, str]] = {}
        for line in plan.splitlines():
            match = _MILESTONE_ROW.match(line)
            if match:
                rows[match.group(1)] = (match.group(2), match.group(3))

        for stage in registry["stages"]:
            expected = (stage["admission_status"], stage["delivery_status"])
            assert rows.get(stage["stage"]) == expected, (
                f"{stage['stage']} milestone row {rows.get(stage['stage'])} "
                f"does not match registry {expected}"
            )
        assert set(rows) == {stage["stage"] for stage in registry["stages"]}

    def test_stage_plans_track_registry_prerequisites(self, repo_root):
        """每个阶段计划的前置表必须与登记表逐项一致。

        回归：M9 收口把登记表的 `M10-M9-EXIT` 由 `OPEN` 改为 `SATISFIED`，但 M10 计划的前置表
        仍写着 `OPEN`——两份权威文档因此自相矛盾，而既有断言只检查阶段名与计划文件名出现。
        """
        registry = _load_admission_registry(repo_root)
        checked = 0
        for stage in registry["stages"]:
            plan = _read(repo_root, stage["plan"])
            for prereq in stage["prerequisites"]:
                pattern = re.compile(
                    rf"^\|\s*`{re.escape(prereq['id'])}`\s*\|\s*`([A-Z_]+)`\s*\|",
                    re.MULTILINE,
                )
                match = pattern.search(plan)
                assert match, (
                    f"{stage['stage']}: 前置 {prereq['id']} 未出现在 "
                    f"{stage['plan']} 的前置表"
                )
                assert match.group(1) == prereq["status"], (
                    f"{stage['stage']}: {prereq['id']} 计划记为 {match.group(1)}，"
                    f"登记表为 {prereq['status']}"
                )
                checked += 1
        # 非空性：登记表若把 prerequisites 清空，「逐项一致」会平凡成立。
        assert checked > 0

    def test_stage_plans_track_registry_decision_status(self, repo_root):
        """每个阶段计划的决策表必须与登记表逐项一致。

        回归：M10 闭合批次 ① 把登记表的 `M10-AUTHORITY` 与 `M10-WRITE-AUTHORIZATION`
        由 `OPEN` 改为 `RESOLVED`，但 M10 计划的 §3 决策表仍写着 `OPEN`——**同一次改动**引入的
        漂移，而当时新增的前置护栏只覆盖 `prerequisites`，覆盖不到决策，故无人发现。
        """
        registry = _load_admission_registry(repo_root)
        checked = 0
        for stage in registry["stages"]:
            plan = _read(repo_root, stage["plan"])
            for decision in stage["mandatory_decisions"]:
                pattern = re.compile(
                    rf"^\|\s*`{re.escape(decision['id'])}`\s*\|\s*`([A-Z_]+)`\s*\|",
                    re.MULTILINE,
                )
                match = pattern.search(plan)
                assert match, (
                    f"{stage['stage']}: 决策 {decision['id']} 未出现在 "
                    f"{stage['plan']} 的决策表"
                )
                assert match.group(1) == decision["status"], (
                    f"{stage['stage']}: {decision['id']} 计划记为 {match.group(1)}，"
                    f"登记表为 {decision['status']}"
                )
                checked += 1
        # 非空性：登记表若把 mandatory_decisions 清空，「逐项一致」会平凡成立。
        assert checked > 0

    def test_navigation_docs_do_not_contradict_registry_state(self, repo_root):
        """当前状态导航文档里的阶段状态断言必须与登记表一致。

        回归：M9 收口只改了 `docs/PLAN.md` 的里程碑表，`docs/README.md`、`docs/plans/README.md`、
        `docs/prds/README.md` 与 `stage-admission-gates.md` 仍断言 M9 未收口 / `M8–M12` 全阻断，
        而 `test_authority_and_navigation_match_registry_state` 的状态聚合断言包在
        `if len(current_states) == 1:` 里——登记表有 3 种状态组合，该分支永不执行。

        两条规则都按**逻辑行**判定：段落内的 markdown 软换行先拼回一句（断言句常跨行），
        而列表项 / 标题 / 表格行各自成行——不拼接会让窗口读到下一行的阶段名而误判归属。
        两条规则都是保守的，归属不明则跳过而**不会**判红，因此**覆盖不是穷尽的**：

        ① 阶段区间短语后接阻断表述时，区间内每个阶段都必须是阻断态；
        ② `` `A / D` `` 状态对归属给它前面最近的阶段名，该状态对必须等于登记表。

        已知不覆盖的形态：以「三个阶段」等**计数词**指代一组阶段，而不是写出区间或逐个命名。

        因此**过渡叙述要写成**「由 `A` 改为 `B`」或「当时交付状态为 `A`」，
        而**不要**写成 `` `A / B` `` 状态对——后者在本规则下被读作当前状态断言。

        **刻意不覆盖**：`docs/PLAN.md`（其当前状态由
        `test_plan_milestone_table_matches_registry` 负责，正文另含 append-only 修订日志，
        混有历史时态）与 `docs/plans/references/`（历史治理记录，只读且不得改写）。
        """
        registry = _load_admission_registry(repo_root)
        states = {
            stage["stage"]: (stage["admission_status"], stage["delivery_status"])
            for stage in registry["stages"]
        }
        blocked = {name for name, state in states.items() if state == ("BLOCKED", "NOT_STARTED")}
        state_pair = _state_pair_pattern(registry)

        ranges_checked = 0
        pairs_checked = 0
        for relative_path in self.CURRENT_STATE_DOCS:
            for start, paragraph in _paragraphs(_read(repo_root, relative_path)):
                for offset, sentence in _logical_lines(paragraph):
                    def locate(inner: int, _p=paragraph, _s=start, _o=offset) -> str:
                        return f"{relative_path}:{_line_of(_p, _s, _o + inner)}"

                    for match in _STAGE_RANGE.finditer(sentence):
                        low, high = int(match.group(1)), int(match.group(2))
                        gap = sentence[match.end() : match.end() + 60]
                        claim = _BLOCKED_CLAIM.search(gap)
                        if not claim:
                            continue
                        # 区间与阻断表述**之间**若又出现别的阶段名，就无法把该表述归属给这个区间。
                        # 只看到阻断表述为止——其后同句出现的阶段名（如「…仍为 `BLOCKED / NOT_STARTED`。
                        # M8 的八项 Decision…」）不参与归属判定。
                        if _STAGE_NAME.search(gap[: claim.end()]):
                            continue
                        where = locate(match.start())
                        for number in range(low, high + 1):
                            name = f"M{number}"
                            assert name in states, (
                                f"{where}: 区间 {match.group(0)} 含未登记阶段 {name}"
                            )
                            assert name in blocked, (
                                f"{where}: 区间 {match.group(0)} 被表述为阻断，"
                                f"但登记表 {name} 为 {states[name][0]} / {states[name][1]}"
                            )
                        ranges_checked += 1

                    for pair in state_pair.finditer(sentence):
                        owners = [
                            name
                            for name in _STAGE_NAME.finditer(sentence[: pair.start()])
                            if name.group(0) in states
                        ]
                        if not owners:
                            continue
                        name = owners[-1].group(0)
                        where = locate(pair.start())
                        assert pair.group(1) == f"{states[name][0]} / {states[name][1]}", (
                            f"{where}: {name} 被记为 {pair.group(0)}，"
                            f"登记表为 {states[name][0]} / {states[name][1]}"
                        )
                        pairs_checked += 1

        # 非空性：两条规则都被跳过时，「没有矛盾」会平凡成立。
        assert ranges_checked > 0
        assert pairs_checked > 0

    def test_prd_defers_to_plan_registry_and_stage_gates(self, repo_root):
        prd = _read(
            repo_root,
            "docs/prds/study-assistance-agent-project-plan-v1.0-prd.md",
        )
        registry = _load_admission_registry(repo_root)

        assert registry["authority"] == "docs/PLAN.md"
        assert "最终里程碑与准入仍以 `docs/PLAN.md` 为准" in prd
        assert "测试通过不能替代 `ADMITTED` 准入批准" in prd

        stages = registry["stages"]
        assert [stage["stage"] for stage in stages] == list(self.EXPECTED_STAGES)
        if all(
            stage["admission_status"] == "BLOCKED"
            and stage["delivery_status"] == "NOT_STARTED"
            for stage in stages
        ):
            assert "M6a–M10 保持 `BLOCKED / NOT_STARTED`" in prd
            assert "当前 M6a–M10 均未进入核心开发" in prd

        assert "**现行保护** `[x]`" in prd
        assert "**准入复验** `[ ]`" in prd
        assert "**未来验收** `[ ]`" in prd
        assert "M7-PROTECTED-BASELINE" in prd
        assert "M6b–M10 仍须分别冻结" in prd
        assert "workload、p50/p95、资源、成本和质量阈值" in prd
        assert "不得用现有 90 题基线替代" in prd

        assert "用户原始材料和大文件保存在仓库外" in prd
        assert "Source Registry、revision、索引控制数据和 manifest" in prd
        assert "由 M7/M8/M10 对应阶段契约决定" in prd
        assert "M7 基础设施范围的实现与技术验收已完成" in prd
        assert "独立人工完成批准" in prd
        assert "M8/M9/M10 的事实型 M7 退出前置已满足" in prd
        assert "不得把用户原始材料复制进 Git" in prd
