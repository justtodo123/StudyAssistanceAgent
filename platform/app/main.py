"""FastAPI 入口：健康检查、搜索、问答（普通 / 流式）。

对齐参考项目 AiAgentController 的对外 API 形态，但只保留学习辅助所需的最小端点。
启动：uvicorn app.main:app --reload（在 platform/ 目录下）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .errors import ErrorCode, http_error
from .models import (
    QaRequest,
    QaResponse,
    QuizRequest,
    QuizResponse,
    ReviewDueResponse,
    ReviewLogRequest,
    ReviewPlanRequest,
    ReviewPlanResponse,
    SearchRequest,
    SearchResponse,
    StudySessionAnswerRequest,
    StudySessionCreateRequest,
    StudySessionResponse,
)
from .learning_store import ReviewHistoryRepositoryAdapter, SqliteLearningStore
from .qa import QaService
from .quiz import QuizService
from .retrieval import MultiRecallService
from .review_plan import ReviewPlanService
from .review_scheduler import ReviewSchedulerService
from .study_session import IllegalSessionStateError, SessionNotFoundError, StudySessionService

app = FastAPI(
    title="StudyAssistanceAgent API",
    description="局域网/本机学习辅助 API：多路召回检索知识库 + 带出处问答",
    version="0.1.0",
)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_WORKBENCH_INDEX = _STATIC_DIR / "workbench" / "index.html"

_recall = MultiRecallService()
_qa = QaService()
_review_plan = ReviewPlanService()
_quiz = QuizService()
_learning_store = SqliteLearningStore(config.LEARNING_STORE_PATH)
_review_scheduler = ReviewSchedulerService(
    repository=ReviewHistoryRepositoryAdapter(_learning_store)
)
_study_sessions = StudySessionService(
    qa_service=_qa,
    quiz_service=_quiz,
    review_scheduler=_review_scheduler,
    session_repository=_learning_store,
)


@app.get("/", include_in_schema=False)
def workbench() -> FileResponse:
    """Serve the minimal learning workbench as the first screen."""
    if not _WORKBENCH_INDEX.is_file():
        raise http_error(ErrorCode.WORKBENCH_UNAVAILABLE, "learning workbench is unavailable")
    return FileResponse(_WORKBENCH_INDEX)


@app.get("/health")
def health() -> dict[str, Any]:
    from .knowledge_index import build_index_cached
    from .observability import metrics
    from .vector_store import LocalVectorStore, SqliteVectorStore

    if config.VECTOR_STORE == "sqlite":
        vector_engine = "sqlite" if SqliteVectorStore.available() else "sqlite-unavailable"
    else:
        vector_engine = "linear" if LocalVectorStore.available() else "linear-unavailable"

    chunks = build_index_cached()
    metrics.set_index_size(len(chunks))
    snapshot = metrics.snapshot()
    return {
        "status": "UP",
        "vector_engine": vector_engine,
        "knowledge_root": str(config.KNOWLEDGE_ROOT),
        "index_size": len(chunks),
        "cache_status": snapshot["cache_status"],
        "avg_latency_ms": snapshot["avg_latency_ms"],
        "p50_latency_ms": snapshot["p50_latency_ms"],
        "p95_latency_ms": snapshot["p95_latency_ms"],
        "p99_latency_ms": snapshot["p99_latency_ms"],
        "sample_count": snapshot["sample_count"],
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


@app.post("/api/v1/study-sessions", response_model=StudySessionResponse)
def create_study_session(req: StudySessionCreateRequest) -> StudySessionResponse:
    """创建学习会话：检索讲解并出题。"""
    return _study_sessions.create(req)


@app.get("/api/v1/study-sessions/{session_id}", response_model=StudySessionResponse)
def get_study_session(session_id: str) -> StudySessionResponse:
    """查询学习会话状态。"""
    try:
        return _study_sessions.get(session_id)
    except SessionNotFoundError as exc:
        raise http_error(ErrorCode.SESSION_NOT_FOUND, str(exc)) from exc


@app.post("/api/v1/study-sessions/{session_id}/answers", response_model=StudySessionResponse)
def submit_study_answer(
    session_id: str,
    req: StudySessionAnswerRequest,
) -> StudySessionResponse:
    """提交当前题目答案并评估掌握度。"""
    try:
        return _study_sessions.submit_answer(session_id, req)
    except SessionNotFoundError as exc:
        raise http_error(ErrorCode.SESSION_NOT_FOUND, str(exc)) from exc
    except IllegalSessionStateError as exc:
        raise http_error(ErrorCode.ILLEGAL_SESSION_STATE, str(exc)) from exc


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


if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
