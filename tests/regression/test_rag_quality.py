"""RAG 质量回归测试。

量化验证检索效果不低于基线（Recall@3 ≥ 0.8）。
M3a（向量库变更）后必须运行。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[2] / "platform"
REPO_ROOT = Path(__file__).resolve().parents[2]

if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

from app.retrieval import MultiRecallService  # noqa: E402

# 基线阈值（来自 M1d 验证结果）
RECALL_THRESHOLD = 0.8
EVAL_FILES = {
    "os": REPO_ROOT / "tools" / "evaluations" / "os.json",
    "ds": REPO_ROOT / "tools" / "evaluations" / "ds.json",
    "co": REPO_ROOT / "tools" / "evaluations" / "co.json",
}


def _load_eval_set(path: Path) -> dict[str, list[str]]:
    """加载评测集。"""
    if not path.exists():
        pytest.skip(f"评测集不存在: {path}")
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _compute_recall(
    service: MultiRecallService,
    test_set: dict[str, list[str]],
    k: int,
) -> float:
    """计算 Recall@k。"""
    recalls = []
    for q, rel_files in test_set.items():
        if not rel_files:
            continue
        results, _ = service.recall(q, top_k=k)
        hit_files = {r.file for r in results} & set(rel_files)
        recalls.append(len(hit_files) / len(rel_files))
    return sum(recalls) / len(recalls) if recalls else 0.0


@pytest.fixture(scope="module")
def rag_service():
    return MultiRecallService()


@pytest.mark.slow
class TestRagQualityRegression:
    """RAG 质量回归：Recall@3 ≥ 0.8。"""

    def test_os_recall_at_3(self, rag_service):
        """OS Recall@3 应 ≥ 0.8。"""
        test_set = _load_eval_set(EVAL_FILES["os"])
        recall = _compute_recall(rag_service, test_set, k=3)
        assert recall >= RECALL_THRESHOLD, (
            f"OS Recall@3={recall:.3f} < {RECALL_THRESHOLD}，检索质量退化！"
        )

    def test_ds_recall_at_3(self, rag_service):
        """DS Recall@3 应 ≥ 0.8。"""
        test_set = _load_eval_set(EVAL_FILES["ds"])
        recall = _compute_recall(rag_service, test_set, k=3)
        assert recall >= RECALL_THRESHOLD, (
            f"DS Recall@3={recall:.3f} < {RECALL_THRESHOLD}，检索质量退化！"
        )

    def test_co_recall_at_3(self, rag_service):
        """CO Recall@3 应 ≥ 0.8。"""
        test_set = _load_eval_set(EVAL_FILES["co"])
        recall = _compute_recall(rag_service, test_set, k=3)
        assert recall >= RECALL_THRESHOLD, (
            f"CO Recall@3={recall:.3f} < {RECALL_THRESHOLD}，检索质量退化！"
        )
