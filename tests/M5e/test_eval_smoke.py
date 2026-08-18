"""Evaluation smoke mode keeps CI fast and offline."""

from __future__ import annotations

import pytest


@pytest.mark.m5e
class TestEvaluationSmoke:
    def test_smoke_flag_defaults(self):
        import run_evaluation as eval_module

        args = eval_module.parse_args([])
        assert args.smoke is False
        assert args.use_vector is False
        args = eval_module.parse_args(["--smoke", "--smoke-limit", "3"])
        assert args.smoke is True
        assert args.smoke_limit == 3

    def test_limit_keeps_labeled_questions_only(self):
        import run_evaluation as eval_module

        limited = eval_module.limit_smoke_samples(
            {
                "skip": [],
                "q1": ["knowledge/os/a.md"],
                "q2": ["knowledge/os/b.md"],
                "q3": ["knowledge/os/c.md"],
            },
            2,
        )
        assert list(limited) == ["q1", "q2"]

    def test_smoke_run_uses_limited_set(self):
        import run_evaluation as eval_module

        calls: list[str] = []

        def fake_recall(question: str, top_k: int):
            calls.append(question)
            return [type("Chunk", (), {"file": "knowledge/os/a.md"})()], "keyword-only"

        args = eval_module.parse_args(
            ["--test-set", "tools/evaluations/os.json", "--smoke", "--smoke-limit", "2", "-k", "3"]
        )
        report = eval_module.run(args, recall_fn=fake_recall)
        assert report["use_vector"] is False
        assert calls
        assert len(calls) <= 2