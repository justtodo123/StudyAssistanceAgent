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
            and "tests/regression" in command
            and '-m "not slow"' in command
            for command in commands
        )
        assert (
            "python -m pytest tests/regression/test_rag_quality.py "
            "-q --tb=short -m slow"
        ) in commands
        assert "python tools/run_evaluation.py --smoke" in commands

        serialized = yaml.safe_dump(workflow)
        assert "huggingface-cli" not in serialized.lower()
        assert "SA_LLM_API_KEY" not in serialized

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
