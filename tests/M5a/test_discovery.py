"""Evaluation-set discovery for the unified runner."""

from __future__ import annotations

import json

import pytest


@pytest.mark.m5a
class TestDiscoverEvaluationSets:
    def test_discovers_known_course_files(self, eval_module, fake_eval_dir, tmp_path):
        found = eval_module.discover_evaluation_sets(tmp_path, eval_dir=fake_eval_dir)
        assert [item["course"] for item in found] == ["os", "ds", "co"]

    def test_filters_by_requested_courses(self, eval_module, fake_eval_dir, tmp_path):
        found = eval_module.discover_evaluation_sets(
            tmp_path,
            courses=["co", "os"],
            eval_dir=fake_eval_dir,
        )
        assert [item["course"] for item in found] == ["co", "os"]

    def test_skips_missing_course_files(self, eval_module, tmp_path):
        eval_dir = tmp_path / "evaluations"
        eval_dir.mkdir()
        (eval_dir / "os.json").write_text("{}", encoding="utf-8")
        found = eval_module.discover_evaluation_sets(tmp_path, eval_dir=eval_dir)
        assert [item["course"] for item in found] == ["os"]


@pytest.mark.m5a
class TestResolveDatasets:
    def test_test_set_overrides_course_filter(self, eval_module, fake_eval_dir, tmp_path):
        args = eval_module.parse_args(
            ["--test-set", str(fake_eval_dir / "ds.json"), "--courses", "os"]
        )
        datasets = eval_module.resolve_datasets(args, tmp_path)
        assert len(datasets) == 1
        assert datasets[0]["course"] == "ds"

    def test_missing_test_set_raises(self, eval_module, tmp_path):
        args = eval_module.parse_args(["--test-set", "missing.json"])
        with pytest.raises(FileNotFoundError, match="not found"):
            eval_module.resolve_datasets(args, tmp_path)

    def test_custom_test_set_uses_custom_course(self, eval_module, tmp_path):
        path = tmp_path / "extra.json"
        path.write_text(json.dumps({"q": ["knowledge/os/a.md"]}), encoding="utf-8")
        args = eval_module.parse_args(["--test-set", str(path)])
        datasets = eval_module.resolve_datasets(args, tmp_path)
        assert datasets[0]["course"] == "custom"

    def test_repo_sets_cover_ninety_questions(self, eval_module, repo_root):
        found = eval_module.discover_evaluation_sets(repo_root)
        counts = {
            item["course"]: len(eval_module.load_test_set(item["path"])) for item in found
        }
        assert counts == {"os": 38, "ds": 28, "co": 24}
        assert sum(counts.values()) == 90
