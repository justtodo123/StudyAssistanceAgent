"""FastAPI 入口：健康检查、搜索、问答（普通 / 流式）。

对齐参考项目 AiAgentController 的对外 API 形态，但只保留学习辅助所需的最小端点。
启动：uvicorn app.main:app --reload（在 platform/ 目录下）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .errors import ErrorCode, http_error
from .models import (
    GoalPlanRequest,
    GoalPlanResponse,
    PlanAdoptRequest,
    PlanProgressEvent,
    PlanProgressRequest,
    PlanReplanRequest,
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
from .goal_planner import GoalPlannerService
from .mastery_projection import MasteryProjectionService
from .plan_lifecycle import (
    IllegalPlanProgressEventError,
    PlanLifecycleService,
    PlanNotFoundError,
)
from .qa import QaService
from .quiz import QuizService
from .retrieval import MultiRecallService, RetrievalScope
from .snapshot_publisher import CombinedSnapshotPublisher
from .source_summary_projection import LazySourceSummaryProjection
from .user_source_search import LazyUserSourceSearch
from .worker_topology import (
    ServiceLock,
    enforce_single_worker_topology,
    service_lock_path,
)
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

_snapshot_publisher = CombinedSnapshotPublisher(
    config.INDEX_CACHE_PATH,
    expected_default_revision=config.EXPECTED_DEFAULT_PACK_REVISION,
)
_service_lock = ServiceLock(service_lock_path())


_user_source_search = LazyUserSourceSearch(
    config.SOURCE_REGISTRY_PATH,
    config.USER_SOURCE_CACHE_PATH,
)
_recall = MultiRecallService(
    snapshot_provider=_snapshot_publisher.view,
    user_source_search=_user_source_search,
)
_qa = QaService(_recall, scope=RetrievalScope.DEFAULT_PLUS_EXTRAS)
_review_plan = ReviewPlanService()
_quiz = QuizService()
_learning_store = SqliteLearningStore(config.LEARNING_STORE_PATH)
_review_scheduler = ReviewSchedulerService(
    repository=ReviewHistoryRepositoryAdapter(_learning_store)
)
# mastery 只读投影：传活对象而非快照，使计划身份与排序随答题状态刷新（与 _review_scheduler 同形）
_mastery_projection = MasteryProjectionService(_learning_store)
# 授权 Source 只读摘要：懒装配。registry 库不存在时不打开控制面，且绝不因缺库而建库
# （`SqliteSourceRegistry.__init__` 会 mkdir 建表，故守卫必须在构造之前）。
_source_summary = LazySourceSummaryProjection(config.SOURCE_REGISTRY_PATH)
_goal_planner = GoalPlannerService(
    review_history=_learning_store.all_reviews(),
    mastery_projection=_mastery_projection,
    source_summary=_source_summary,
)
_plan_lifecycle = PlanLifecycleService(
    _learning_store,
    _goal_planner,
    review_scheduler=_review_scheduler,
)
_study_sessions = StudySessionService(
    qa_service=QaService(_recall, scope=RetrievalScope.DEFAULT_ONLY),
    quiz_service=_quiz,
    review_scheduler=_review_scheduler,
    session_repository=_learning_store,
)


if config.AGENT_PREVIEW_ENABLED:
    from .preview_service import PreviewService, build_preview_router
    from .tool_registry import ToolRegistry
    from .tools.quiz import QuizTool
    from .tools.retrieve import RetrieveTool
    from .tools.review_due import ReviewDueTool

    _preview_registry = ToolRegistry()
    _preview_registry.register(RetrieveTool(_recall))
    _preview_registry.register(QuizTool(_quiz))
    _preview_registry.register(ReviewDueTool(_review_scheduler))
    _preview_service = PreviewService(
        token=config.AGENT_PREVIEW_TOKEN,
        provider_key=config.ANTHROPIC_API_KEY,
        registry=_preview_registry,
        limits=config.AGENT_PREVIEW_LIMITS,
    )
    app.include_router(build_preview_router(_preview_service))


def _initialize_runtime() -> None:
    """Take the single-worker lock and publish one complete snapshot."""
    enforce_single_worker_topology()
    _service_lock.acquire()
    try:
        _snapshot_publisher.publish()
    except Exception:
        _service_lock.release()
        raise


def _shutdown_runtime() -> None:
    """Release the process-lifetime service lock."""
    _service_lock.release()


app.router.add_event_handler("startup", _initialize_runtime)
app.router.add_event_handler("shutdown", _shutdown_runtime)


@app.get("/", include_in_schema=False)
def workbench() -> FileResponse:
    """Serve the minimal learning workbench as the first screen."""
    if not _WORKBENCH_INDEX.is_file():
        raise http_error(ErrorCode.WORKBENCH_UNAVAILABLE, "learning workbench is unavailable")
    return FileResponse(_WORKBENCH_INDEX)


@app.get("/health")
def health() -> dict[str, Any]:
    from .observability import metrics
    from .vector_store import LocalVectorStore, SqliteVectorStore

    if config.VECTOR_STORE == "sqlite":
        vector_engine = "sqlite" if SqliteVectorStore.available() else "sqlite-unavailable"
    else:
        vector_engine = "linear" if LocalVectorStore.available() else "linear-unavailable"

    _generation, chunks = _snapshot_publisher.view(
        RetrievalScope.DEFAULT_PLUS_EXTRAS
    )
    metrics.set_index_size(len(chunks))
    snapshot = metrics.snapshot()
    return {
        "status": "UP",
        "vector_engine": vector_engine,
        "knowledge_root": "knowledge-pack",
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
    results, mode = _recall.recall(
        req.question,
        req.top_k,
        course=req.course,
        scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
        use_vector=req.use_vector,
    )
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


def _plan_error(exc: Exception) -> HTTPException:
    """把计划生命周期领域异常映射为稳定错误码，避免用户输入错误变成 500。"""
    if isinstance(exc, PlanNotFoundError):
        return http_error(ErrorCode.PLAN_NOT_FOUND, str(exc))
    return http_error(ErrorCode.ILLEGAL_PLAN_PROGRESS_EVENT, str(exc))


@app.post("/api/v1/plans", response_model=GoalPlanResponse)
def goal_plan(req: GoalPlanRequest) -> GoalPlanResponse:
    """生成目标驱动学习计划（M9 确定性 Planner，仅生成、不写状态）。

    任务的 mastery 字段与排序取自权威 mastery 只读投影；plan_id 含派生输入摘要，
    因此复习/mastery 状态变化后会得到新的 plan_id（旧计划记录只读保留）。
    """
    response = _goal_planner.generate(req)
    _plan_lifecycle.persist_generated(response)
    return response


@app.post("/api/v1/plans/{plan_id}/adopt")
def adopt_plan(plan_id: str) -> dict[str, Any]:
    """采纳一个已生成的目标驱动计划。"""
    try:
        return _plan_lifecycle.adopt(plan_id)
    except PlanNotFoundError as exc:
        raise _plan_error(exc) from exc


@app.post("/api/v1/plans/{plan_id}/progress", response_model=PlanProgressEvent)
def record_plan_progress(plan_id: str, req: PlanProgressRequest) -> PlanProgressEvent:
    """记录一个计划任务的进度事件（completed / skipped / overdue）。"""
    try:
        return _plan_lifecycle.record_progress(req)
    except (PlanNotFoundError, IllegalPlanProgressEventError) as exc:
        raise _plan_error(exc) from exc


@app.post("/api/v1/plans/{plan_id}/replan")
def replan(plan_id: str, req: PlanReplanRequest | None = None) -> dict[str, Any]:
    """按未消费偏差（跳过 + 逾期 ≥ 3）或目标/约束变化确定性重规划，生成新 revision。

    已消费的偏差不再触发；未触发时不写盘，因此重复调用不会持续追加内容相同的新 revision。
    """
    try:
        return _plan_lifecycle.replan(plan_id, req)
    except PlanNotFoundError as exc:
        raise _plan_error(exc) from exc


@app.get("/api/v1/plans/{plan_id}")
def get_plan(plan_id: str) -> dict[str, Any]:
    """查询一个目标驱动计划的当前状态。"""
    try:
        return _plan_lifecycle.get(plan_id)
    except PlanNotFoundError as exc:
        raise _plan_error(exc) from exc


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


if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
