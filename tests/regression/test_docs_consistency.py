"""跨文档耐久事实一致性契约。"""

from __future__ import annotations

import json


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
        assert "M6a 已获准开工" in plan
        assert "M6b–M10" in root
        assert "M6–M10" in plan
        for text in (root, plan):
            assert "BLOCKED / NOT_STARTED" in text
        assert "ADMITTED / NOT_STARTED" in root
        assert "M6b–M10 仍为 `BLOCKED / NOT_STARTED`" in root
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
        assert "OS 0.987" in root
        assert "加权 0.972" in root

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
    EXPECTED_STAGES = ("M6a", "M6b", "M7", "M8", "M9", "M10")
    APPROVAL_FIELDS = (
        "approved_by",
        "approved_at",
        "approval_reference",
        "plan_revision",
        "decision_set_version",
    )

    def test_registry_schema_status_and_plan_files(self, repo_root):
        registry = _load_admission_registry(repo_root)

        assert registry["schema_version"] == 1
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
        seen_ids: set[str] = set()

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
        m6b_prerequisites = {item["id"] for item in stages["M6b"]["prerequisites"]}
        m7_prerequisites = {item["id"] for item in stages["M7"]["prerequisites"]}

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
        ):
            assert filename in docs
            assert filename in plans

        assert "Agent 不得自行批准" in plan
        assert "计划存在只代表设定澄清准备" in docs
        assert "不接管 `/api/v1/study-sessions`" in plan
        assert "状态机继续作为正式默认" in plan
        assert "无 LLM 降级路径" in plan

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
        assert "不得把用户原始材料复制进 Git" in prd
