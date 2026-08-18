"""Metric aggregation for the unified evaluation runner."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.m5a
class TestScoreSample:
    def test_skips_unlabeled_questions(self, eval_module):
        assert eval_module.score_sample(["knowledge/os/a.md"], []) is None

    def test_counts_unique_file_hits(self, eval_module):
        score = eval_module.score_sample(
            ["knowledge/os/a.md", "knowledge/os/a.md", "knowledge/os/b.md"],
            ["knowledge/os/a.md", "knowledge/os/c.md"],
        )
        assert score is not None
        assert score["recall"] == pytest.approx(0.5)
        assert score["precision"] == pytest.approx(1 / 3)


@pytest.mark.m5a
class TestAggregateMetrics:
    def test_empty_samples_are_zero(self, eval_module):
        metrics = eval_module.aggregate_metrics([])
        assert metrics["labeled_questions"] == 0
        assert metrics["recall"] == 0.0
        assert metrics["f1"] == 0.0

    def test_averages_recall_precision_and_latency(self, eval_module):
        metrics = eval_module.aggregate_metrics(
            [
                {"recall": 1.0, "precision": 0.5, "latency_ms": 10.0},
                {"recall": 0.0, "precision": 0.0, "latency_ms": 30.0},
            ]
        )
        assert metrics["recall"] == pytest.approx(0.5)
        assert metrics["precision"] == pytest.approx(0.25)
        assert metrics["f1"] == pytest.approx(1 / 3)
        assert metrics["avg_latency_ms"] == pytest.approx(20.0)
        assert metrics["labeled_questions"] == 2


@pytest.mark.m5a
class TestEvaluateAndSummary:
    def test_evaluate_test_set_slices_max_k_results(self, eval_module):
        test_set = {
            "q1": ["knowledge/os/a.md"],
            "unlabeled": [],
        }

        def recall_fn(question: str, top_k: int):
            assert top_k == 3
            if question == "unlabeled":
                return [], "keyword-only"
            assert question == "q1"
            return [
                SimpleNamespace(file="knowledge/os/a.md"),
                SimpleNamespace(file="knowledge/os/b.md"),
                SimpleNamespace(file="knowledge/os/c.md"),
            ], "keyword-only"

        result = eval_module.evaluate_test_set(test_set, [1, 3], recall_fn)
        assert result["questions"] == 2
        assert result["labeled_questions"] == 1
        assert result["metrics"]["1"]["recall"] == 1.0
        assert result["metrics"]["1"]["precision"] == 1.0
        assert result["metrics"]["3"]["precision"] == pytest.approx(1 / 3)

    def test_weighted_summary_prefers_larger_sets(self, eval_module):
        datasets = [
            {
                "questions": 2,
                "labeled_questions": 2,
                "metrics": {
                    "3": {
                        "recall": 1.0,
                        "precision": 1.0,
                        "f1": 1.0,
                        "avg_latency_ms": 10.0,
                        "labeled_questions": 2,
                    }
                },
            },
            {
                "questions": 1,
                "labeled_questions": 1,
                "metrics": {
                    "3": {
                        "recall": 0.0,
                        "precision": 0.0,
                        "f1": 0.0,
                        "avg_latency_ms": 40.0,
                        "labeled_questions": 1,
                    }
                },
            },
        ]
        summary = eval_module.weighted_summary(datasets, [3])
        assert summary["questions"] == 3
        assert summary["metrics"]["3"]["recall"] == pytest.approx(2 / 3)
        assert summary["metrics"]["3"]["avg_latency_ms"] == pytest.approx(20.0)

