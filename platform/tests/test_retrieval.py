"""检索链路冒烟测试：验证「知识库切分 → 多路召回/降级 → 带出处问答」端到端可用。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.knowledge_index import build_index, _parse_frontmatter, _split_headings  # noqa: E402
from app.models import QaRequest  # noqa: E402
from app.qa import QaService  # noqa: E402
from app.retrieval import MultiRecallService  # noqa: E402


@pytest.fixture(scope="module")
def chunks():
    return build_index()


def test_index_builds_with_seed_knowledge(chunks):
    assert len(chunks) >= 1, "knowledge/ 应有至少一条可检索切片（示例条目 os）"
    files = {c.file for c in chunks}
    assert any("knowledge/os/" in f for f in files)


def test_frontmatter_parses(chunks):
    os_chunks = [c for c in chunks if c.course == "os"]
    assert os_chunks, "示例条目应带 course: os"
    assert any("调度" in c.tags for c in os_chunks)


def test_bm25_recall_finds_scheduling(chunks):
    service = MultiRecallService()
    results, mode = service.recall("进程调度算法平均等待时间", top_k=5)
    assert results, "检索不应为空"
    assert any("进程调度" in r.title or "scheduling" in r.file for r in results)
    assert mode in ("hybrid", "keyword-only")  # 无向量依赖时也应可用


def test_qa_fallback_returns_sources():
    service = QaService()
    resp = service.answer(QaRequest(question="讲讲 CFS 与 SJF 的区别", use_llm=False))
    assert "出处" in resp.answer
    assert resp.sources, "回答必须带出处切片"
    for s in resp.sources:
        assert s.file.startswith("knowledge/")


def test_split_headings_splits_multiple_sections():
    text = "## A\n内容a\n## B\n内容b\n"
    sections = _split_headings(text)
    assert [t for t, _ in sections] == ["A", "B"]
