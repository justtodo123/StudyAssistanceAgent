#!/usr/bin/env python3
"""RAG 效果评估（参考项目 RagEvaluationService 的轻量移植）。

指标：
- Recall@k：top-k 结果中出现在「相关文档集合」的比例
- Precision@k：top-k 结果中相关文档的比例
- F1：二者调和平均
- Latency：平均检索耗时

用法（在 platform/.venv 或已安装依赖的任意 Python 中）：
    python tools/run_evaluation.py                # 打印默认评测集结果
    python tools/run_evaluation.py -k 1,3,5       # 指定多个 k
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 允许从任意位置运行：找到仓库根
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "platform"))

from app.retrieval import MultiRecallService  # noqa: E402

DEFAULT_TEST_SET = {
    "进程调度算法有哪些": [
        "knowledge/os/process-scheduling.md",
    ],
    "什么是虚拟内存": [],
    "静默周期是什么": [],
}


def load_test_set(path: str | None) -> dict[str, list[str]]:
    if path:
        p = Path(path)
        if not p.exists():
            print(f"[warn] 评测集不存在: {p}，使用内置示例", file=sys.stderr)
            return DEFAULT_TEST_SET
        return dict(json.loads(p.read_text(encoding="utf-8")))
    return dict(DEFAULT_TEST_SET)


def evaluate(test_set: dict[str, list[str]], top_ks: list[int]) -> None:
    service = MultiRecallService()
    print(f"评测集大小: {len(test_set)}，topKs: {top_ks}\n")
    print(f"{'k':<3}{'Recall@k':<10}{'Precision@k':<13}{'F1':<8}{'AvgLatency(ms)':<14}")
    print("-" * 50)

    for k in top_ks:
        recalls, precisions, latencies = [], [], []
        for q, rel_files in test_set.items():
            t0 = time.perf_counter()
            results, _mode = service.recall(q, top_k=k)
            latencies.append((time.perf_counter() - t0) * 1000)
            if not rel_files:  # 无标注相关文档 → 跳过该样本
                continue
            # 对同一文件可能命中多个切片：按「文档是否被召回」计，避免重复计数虚高
            hit_files = {r.file for r in results} & set(rel_files)
            recalls.append(len(hit_files) / len(rel_files))
            precisions.append(len(hit_files) / max(len(results), 1))
        if not recalls:
            print(f"{k:<3}（本组无标注样本）")
            continue
        r = sum(recalls) / len(recalls)
        p = sum(precisions) / len(precisions)
        f1 = 2 * r * p / (r + p) if (r + p) else 0.0
        lat = sum(latencies) / len(latencies)
        print(f"{k:<3}{r:<10.3f}{p:<13.3f}{f1:<8.3f}{lat:<14.1f}")


def main() -> None:
    ap = argparse.ArgumentParser(description="RAG 效果评估")
    ap.add_argument("--test-set", default=None, help="评测集 JSON（问题→相关文件数组）")
    ap.add_argument("-k", "--top-ks", default="1,3,5", help="逗号分隔的 top-k 列表")
    args = ap.parse_args()
    top_ks = [int(x) for x in args.top_ks.split(",") if x.strip()]
    evaluate(load_test_set(args.test_set), top_ks)


if __name__ == "__main__":
    main()
