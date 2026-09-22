"""离线 CI 的耐久门禁契约。"""

from __future__ import annotations


import yaml

class TestOfflineCiContract:
    @staticmethod
    def _load_workflow(repo_root):
        path = repo_root / ".github" / "workflows" / "offline-ci.yml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @staticmethod
    def _run_commands(job):
        return [
            step["run"].strip()
            for step in job["steps"]
            if "run" in step
        ]

    def test_offline_job_runs_platform_fast_and_full_rag_gates(self, repo_root):
        workflow = self._load_workflow(repo_root)
        offline = workflow["jobs"]["offline"]
        commands = self._run_commands(offline)

        assert offline["env"] == {
            "SA_USE_VECTOR": "false",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        }
        assert "python -m pytest platform/tests -q --tb=short" in commands
        assert any(
            command.startswith("python -m pytest tests/M0_M2")
            and "tests/M6a" in command
            and "tests/M6b" in command
            and "tests/regression" in command
            and '-m "not slow and not m6b_benchmark and not m9_benchmark"' in command
            for command in commands
        )
        assert (
            "python -m pytest tests/regression/test_rag_quality.py "
            "-q --tb=short -m slow"
        ) in commands
        assert (
            "python -m pytest tests/M6b -q --tb=short -m m6b_benchmark"
        ) in commands
        benchmark_step = next(
            step
            for step in offline["steps"]
            if step.get("name") == "Run blocking M6b offline preview benchmark"
        )
        evidence_id = "${{ github.run_id }}-${{ github.run_attempt }}"
        assert benchmark_step["env"] == {
            "M6B_BENCHMARK_EVIDENCE_ID": evidence_id,
            "M6B_BENCHMARK_REPORT": (
                f"reports/m6b-offline-preview-benchmark-{evidence_id}.json"
            ),
        }
        upload_step = next(
            step
            for step in offline["steps"]
            if step.get("name") == "Upload sanitized M6b benchmark report"
        )
        assert upload_step["uses"] == "actions/upload-artifact@v4"
        assert upload_step["with"] == {
            "name": f"m6b-offline-preview-benchmark-{evidence_id}",
            "path": f"reports/m6b-offline-preview-benchmark-{evidence_id}.json",
            "if-no-files-found": "error",
        }
        assert "python tools/run_evaluation.py --smoke" in commands

        # M9 计划路径比较与 M6b 预览基准同形：独占报告 + 证据 ID 绑定 + 上传步骤。
        # 它只跑 1K：外部 AI 路径由确定性 stub 驱动，故这一步既不需要网络也不需要凭据。
        assert "python -m pytest tests/M9 -q --tb=short -m m9_benchmark" in commands
        m9_step = next(
            step
            for step in offline["steps"]
            if step.get("name") == "Run blocking M9 plan-path benchmark at 1K"
        )
        assert m9_step["env"] == {
            "M9_BENCHMARK_EVIDENCE_ID": evidence_id,
            "M9_BENCHMARK_REPORT": f"reports/m9-plan-ai-benchmark-{evidence_id}.json",
        }
        m9_upload = next(
            step
            for step in offline["steps"]
            if step.get("name") == "Upload sanitized M9 plan-path benchmark report"
        )
        assert m9_upload["uses"] == "actions/upload-artifact@v4"
        assert m9_upload["with"] == {
            "name": f"m9-plan-ai-benchmark-{evidence_id}",
            "path": f"reports/m9-plan-ai-benchmark-{evidence_id}.json",
            "if-no-files-found": "error",
        }

        serialized = yaml.safe_dump(workflow)
        assert "huggingface-cli" not in serialized.lower()
        assert "SA_LLM_API_KEY" not in serialized
        assert "ANTHROPIC_API_KEY" not in serialized
        assert "SA_AGENT_PREVIEW_TOKEN" not in serialized
        # 外部 AI 路径的令牌同样不得进 CI：这一步必须靠 stub 离线跑通。
        assert "SA_PLAN_AI_TOKEN" not in serialized
        assert "SA_PLAN_AI_ENABLED" not in serialized

    def test_crawler_jobs_remain_isolated_and_online_is_explicit(self, repo_root):
        workflow = self._load_workflow(repo_root)
        jobs = workflow["jobs"]
        offline = jobs["crawler-offline"]
        online = jobs["crawler-online-smoke"]
        offline_commands = self._run_commands(offline)
        online_commands = self._run_commands(online)

        assert any(
            "tools/crawler/requirements.txt" in command
            for command in offline_commands
        )
        assert (
            "python -m pytest tests/M6_crawler -q --tb=short "
            '-m "m6_crawler and not online"'
        ) in offline_commands
        assert online["if"] == (
            "github.event_name == 'workflow_dispatch' "
            "&& inputs.crawler_online_smoke"
        )
        assert online["env"]["CRAWLER_ONLINE"] == "true"
        assert (
            "python -m pytest tests/M6_crawler -q --tb=short "
            '-m "m6_crawler and online"'
        ) in online_commands

    #: Stage test directories that are deliberately absent from the shared stage
    #: command, each with the reason. Every other `tests/*/` directory that holds
    #: `test_*.py` must be in that command.
    _STAGE_DIRS_WITHOUT_SHARED_COMMAND = {
        "M6_crawler": "runs in the dedicated crawler-offline / crawler-online-smoke jobs",
        "M7": "excluded: 3 TXT cases fail closed on CPython 3.13 by design (see TEST_PLAN)",
        "source_inventory": "read-only external inventory; not a gate",
    }

    def test_every_stage_test_directory_is_covered_by_ci(self, repo_root):
        """A stage suite must not be able to land without CI coverage.

        M10 shipped 115 tests — including the write-authorization, crash-recovery
        and atomic-publication guards — and was absent from the stage command
        until it was noticed by hand. The existing assertions are subset checks,
        so they cannot catch an omission. Enumerating the tree can.
        """
        tests_root = repo_root / "tests"
        present = sorted(
            path.name
            for path in tests_root.iterdir()
            if path.is_dir()
            and path.name not in {"__pycache__", "utils"}
            and any(path.glob("test_*.py"))
        )
        assert present, "the enumeration found no stage directories at all"

        commands = self._run_commands(
            self._load_workflow(repo_root)["jobs"]["offline"]
        )
        stage_command = next(
            command for command in commands
            if command.startswith("python -m pytest tests/M0_M2")
        )

        missing = [
            name for name in present
            if name not in self._STAGE_DIRS_WITHOUT_SHARED_COMMAND
            and f"tests/{name}" not in stage_command
        ]
        assert missing == [], (
            f"stage suites with no CI coverage: {missing}"
        )
        # Non-vacuity: the exclusion list must be a decision, not an escape hatch
        # that could be widened until the check passes for anything.
        assert set(self._STAGE_DIRS_WITHOUT_SHARED_COMMAND) <= set(present)
        for name in self._STAGE_DIRS_WITHOUT_SHARED_COMMAND:
            assert (tests_root / name).is_dir(), f"{name} vanished from the tree"
