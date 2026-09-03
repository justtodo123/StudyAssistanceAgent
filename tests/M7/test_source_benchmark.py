from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import run_m7_benchmark as benchmark

pytestmark = pytest.mark.m7


def test_m7_benchmark_quick_smoke_is_not_exit_evidence(tmp_path: Path) -> None:
    payload = benchmark.build_report(
        [benchmark.run_workload("quick-smoke", sources=1, documents=2, units=2, measured=1, warmup=0)]
    )
    dumped = json.dumps(payload)
    (tmp_path / "m7-benchmark.json").write_text(dumped, encoding="utf-8")
    assert payload["schema"] == "sa.source.benchmark.v1"
    assert payload["m7_exit"] is False
    assert payload["vector_backend"] == "not_attached"
    assert payload["network_promoted"] is False
    assert payload["m8_started"] is False
    assert payload["workloads"][0]["exit_eligible"] is False
    assert payload["workloads"][0]["query_count"] == 2
    assert "C:\\Users" not in dumped
    assert "secret" not in dumped