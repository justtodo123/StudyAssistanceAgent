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
    assert payload["vector_backend"] == "source_local_hash"
    assert payload["workloads"][0]["vector_status"] == "attached"
    assert payload["workloads"][0]["identity_vector"] is True
    assert payload["network_promoted"] is False
    assert payload["m8_started"] is False
    assert payload["workloads"][0]["exit_eligible"] is False
    assert payload["workloads"][0]["query_count"] == 2
    assert "C:\\Users" not in dumped
    assert "secret" not in dumped

from tools import run_m7_frozen_benchmark as frozen


def test_m7_frozen_runner_quick_smoke_never_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_m7_frozen_benchmark.py",
            "--quick",
            "--report",
            str(tmp_path / "frozen.json"),
        ],
    )
    assert frozen.main() == 0
    payload = json.loads((tmp_path / "frozen.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "sa.source.benchmark.v1"
    assert payload["protocol"] == "m7-3-frozen-bge"
    assert payload["m7_exit"] is False
    assert payload["vector_backend"] == "source_local_hash"
    assert payload["network_promoted"] is False
    assert payload["m8_started"] is False
    dumped = json.dumps(payload)
    assert "C:\\Users" not in dumped
