"""Report format tests for the unified evaluation runner."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


@pytest.mark.m5a
class TestReportFormat:
    def test_report_contains_required_fields(self, eval_module, fake_eval_dir, tmp_path):
        args = eval_module.parse_args(
            ["--eval-dir", str(fake_eval_dir), "--courses", "os,ds", "-k", "1,3"]
        )

        def recall_fn(question: str, top_k: int):
            mapping = {
                "os question one": "knowledge/os/a.md",
                "os question two": "knowledge/os/b.md",
                "ds question": "knowledge/ds/a.md",
            }
            return [SimpleNamespace(file=mapping[question])], "keyword-only"

        report = eval_module.run(args, recall_fn=recall_fn, repo_root=tmp_path)
        assert report["mode"] == "keyword-only"
        assert report["use_vector"] is False
        assert report["top_ks"] == [1, 3]
        assert report["total_questions"] == 3
        assert report["labeled_questions"] == 3
        assert set(report["courses"]) == {"os", "ds"}
        assert report["courses"]["os"]["questions"] == 2
        assert report["summary"]["metrics"]["3"]["recall"] == 1.0
        assert "generated_at" in report

    def test_console_output_includes_mode_and_summary(self, eval_module):
        report = {
            "mode": "keyword-only",
            "use_vector": False,
            "top_ks": [3],
            "total_questions": 2,
            "labeled_questions": 2,
            "courses": {
                "os": {
                    "path": "tools/evaluations/os.json",
                    "questions": 2,
                    "labeled_questions": 2,
                    "metrics": {
                        "3": {
                            "recall": 1.0,
                            "precision": 0.5,
                            "f1": 2 / 3,
                            "avg_latency_ms": 4.0,
                            "labeled_questions": 2,
                        }
                    },
                }
            },
            "summary": {
                "questions": 2,
                "labeled_questions": 2,
                "metrics": {
                    "3": {
                        "recall": 1.0,
                        "precision": 0.5,
                        "f1": 2 / 3,
                        "avg_latency_ms": 4.0,
                        "labeled_questions": 2,
                    }
                },
            },
        }
        text = eval_module.format_console(report)
        assert "mode: keyword-only" in text
        assert "SA_USE_VECTOR=false" in text
        assert "[os] tools/evaluations/os.json" in text
        assert "[summary] 2 questions" in text
        assert "1.000" in text

    def test_json_report_round_trip(self, eval_module, tmp_path):
        report = {
            "mode": "keyword-only",
            "use_vector": False,
            "top_ks": [1],
            "total_questions": 1,
            "labeled_questions": 1,
            "courses": {},
            "summary": {"questions": 1, "labeled_questions": 1, "metrics": {}},
        }
        path = tmp_path / "reports" / "eval.json"
        written = eval_module.write_json_report(path, report)
        loaded = json.loads(written.read_text(encoding="utf-8"))
        assert loaded["mode"] == "keyword-only"
        assert loaded["total_questions"] == 1

    def test_default_mode_stays_offline(self, eval_module):
        assert eval_module.requested_mode(False) == "keyword-only"
        assert eval_module.requested_mode(True) == "hybrid"
