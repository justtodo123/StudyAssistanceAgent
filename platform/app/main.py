"""FastAPI 入口：健康检查、搜索、问答（普通 / 流式）。

对齐参考项目 AiAgentController 的对外 API 形态，但只保留学习辅助所需的最小端点。
启动：uvicorn app.main:app --reload（在 platform/ 目录下）
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from . import config
from .models import QaRequest, QaResponse, QuizRequest, QuizResponse, ReviewDueResponse, ReviewLogRequest, ReviewPlanRequest, ReviewPlanResponse, SearchRequest, SearchResponse
from .qa import QaService
from .quiz import QuizService
from .retrieval import MultiRecallService
from .review_plan import ReviewPlanService
from .review_scheduler import ReviewSchedulerService

app = FastAPI(
    title="StudyAssistanceAgent API",
    description="局域网/本机学习辅助 API：多路召回检索知识库 + 带出处问答",
    version="0.1.0",
)

_recall = MultiRecallService()
_qa = QaService()
_review_plan = ReviewPlanService()
_quiz = QuizService()
_review_scheduler = ReviewSchedulerService()


@app.get("/health")
def health() -> dict[str, Any]:
    from .vector_store import LocalVectorStore

    return {
        "status": "UP",
        "vector_engine": "local" if LocalVectorStore.available() else "not-installed",
        "knowledge_root": str(config.KNOWLEDGE_ROOT),
        "llm_configured": bool(config.LLM_API_KEY),
    }


@app.post("/api/v1/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    results, mode = _recall.recall(req.question, req.top_k, course=req.course)
    if not req.use_vector and results:
        # 模拟「关闭向量」仅观察关键词路：BM25 单路重算
        results = bm25_only(req.question, req.top_k, req.course)
        mode = "keyword-only"
    return SearchResponse(question=req.question, mode=mode, results=results)


@app.post("/api/v1/qa", response_model=QaResponse)
def qa(req: QaRequest) -> QaResponse:
    return _qa.answer(req)


@app.post("/api/v1/qa/stream")
def qa_stream(req: QaRequest) -> StreamingResponse:
    resp = _qa.answer(req)

    def gen() -> Any:
        # 先返回来源，再逐段返回正文（演示 SSE 流式输出能力）
        meta = {
            "mode": resp.mode,
            "sources": [c.model_dump() for c in resp.sources],
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"
        for para in resp.answer.split("\n\n"):
            yield f"data: {json.dumps({'delta': para}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/v1/quiz", response_model=QuizResponse)
def quiz(req: QuizRequest) -> QuizResponse:
    """测验生成：从知识条目例题、评测集、概念标签生成测验。"""
    return _quiz.generate(req)


@app.post("/api/v1/review-log")
def review_log(req: ReviewLogRequest) -> dict[str, Any]:
    """记录一次复习完成，更新间隔重复排程。"""
    return _review_scheduler.log_review(req)


@app.get("/api/v1/review-due", response_model=ReviewDueResponse)
def review_due(course: str | None = None) -> ReviewDueResponse:
    """查询今日待复习条目（基于遗忘曲线间隔重复）。"""
    return _review_scheduler.get_due(course)


@app.post("/api/v1/review-plan", response_model=ReviewPlanResponse)
def review_plan(req: ReviewPlanRequest) -> ReviewPlanResponse:
    """生成复习计划：输入课程 + 目标日期 → 输出分日学习计划。"""
    return _review_plan.generate(req)


def bm25_only(question: str, top_k: int, course: str | None = None):
    """关闭向量时展示关键词单路效果（示意，供可观测对比）。"""
    from .bm25 import Bm25Search
    from .knowledge_index import build_index_cached

    chunks = build_index_cached()
    if course:
        chunks = [c for c in chunks if c.course == course]
    pool = chunks if config.BM25_POOL <= 0 else chunks[: config.BM25_POOL]
    bm25 = Bm25Search(pool)
    return bm25.search(question, top_k)
