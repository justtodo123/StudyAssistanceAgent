from __future__ import annotations

import hashlib
import json

import pytest

pytestmark = pytest.mark.m11

EXPECTED_DIGEST = "4069d835477c50ce0edc5c6117a269500997deed91f1154b0304a2bb85f83a54"
REQUIRED_CATEGORIES = {
    "zh-teaching-fact", "protocol-number-title", "registry-fact",
    "cross-language", "hard-negative", "delete-zero-recall",
}


def _load(repo_root, relative):
    path = repo_root / relative
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_independent_workload_is_non_empty_distinct_and_digest_frozen(repo_root):
    path, workload = _load(repo_root, "tools/evaluations/m11-3k-independent-v1.json")
    cases = workload["cases"]
    assert cases
    assert REQUIRED_CATEGORIES <= {case["category"] for case in cases}
    assert len({case["id"] for case in cases}) == len(cases)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_DIGEST
    assert workload["workload_id"] == "m11-3k-independent-v1"


def test_gate_protocol_has_owner_approved_thresholds_but_still_fails_closed(repo_root):
    _, protocol = _load(repo_root, "data/manifests/m11-3k-gate-protocol-v1.json")
    assert protocol["workload_digest"] == EXPECTED_DIGEST
    assert protocol["status"] == "THRESHOLDS_APPROVED_REVIEW_PENDING"
    assert protocol["threshold_approval"] == {
        "approved_by": "justtodo123",
        "approved_at": "2026-09-24",
        "approval_reference": "User instruction: 保守门槛（推荐）",
        "scope": "M11 3K Gate only; does not authorize formal run or publication",
    }
    assert protocol["thresholds"] == {
        "human_fact_accuracy_minimum": 0.95,
        "recall_at_3_minimum": 0.85,
        "recall_at_5_minimum": 0.90,
        "mrr_minimum": 0.75,
        "no_hit_max_errors": 3,
        "hard_negative_max_errors": 3,
    }
    assert protocol["human_review"]["sample_size"] is None
    assert protocol["human_review"]["reviewer"] is None
    assert protocol["formal_run_authorized"] is False
    assert protocol["publication_authorized"] is False


def test_protected_90_question_baseline_is_frozen(repo_root):
    _, protocol = _load(repo_root, "data/manifests/m11-3k-gate-protocol-v1.json")
    baseline = protocol["baseline"]
    assert baseline["question_count"] == 90
    assert baseline["recall_at_3_minimum"] == {
        "os": 1.0, "ds": 0.929, "co": 1.0, "weighted": 0.978
    }
    assert baseline["latest_run"]["weighted"] >= baseline["recall_at_3_minimum"]["weighted"]
