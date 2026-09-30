"""FastAPI 入口：健康检查、搜索、问答（普通 / 流式）。

对齐参考项目 AiAgentController 的对外 API 形态，但只保留学习辅助所需的最小端点。
启动：uvicorn app.main:app --reload（在 platform/ 目录下）
"""

from __future__ import annotations

import json
from dataclasses import dataclass
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
from .combined_snapshot import build_snapshot_for_settings
from .goal_planner import GoalPlannerService
from .mastery_projection import MasteryProjectionService
from .plan_ai_adapter import PlanAIAdapter, build_anthropic_proposer
from .plan_grounding import PlanGroundingService
from .plan_lifecycle import (
    IllegalPlanProgressEventError,
    PlanLifecycleService,
    PlanNotFoundError,
)
from .qa import QaService
from .review_history_projection import ReviewHistoryProjection
from .quiz import QuizService
from .retrieval import MultiRecallService, RetrievalScope
from .snapshot_publisher import CombinedSnapshotPublisher
from .source_summary_projection import LazySourceSummaryProjection
from .topic_graph_projection import TopicGraphProjection
from .user_source_search import LazyUserSourceSearch
from .worker_topology import (
    ServiceLock,
    enforce_single_worker_topology,
    service_lock_path,
)
from .review_plan import ReviewPlanService
from .review_scheduler import ReviewSchedulerService
from .study_session import IllegalSessionStateError, SessionNotFoundError, StudySessionService

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_WORKBENCH_INDEX = _STATIC_DIR / "workbench" / "index.html"


@dataclass
class RuntimeServices:
    """Services owned by exactly one FastAPI application instance."""

    settings: config.Settings
    snapshot_publisher: CombinedSnapshotPublisher
    service_lock: ServiceLock
    user_source_search: LazyUserSourceSearch
    recall: MultiRecallService
    qa: QaService
    review_plan: ReviewPlanService
    quiz: QuizService
    learning_store: SqliteLearningStore
    review_scheduler: ReviewSchedulerService
    mastery_projection: MasteryProjectionService
    source_summary: LazySourceSummaryProjection
    topic_graph: TopicGraphProjection
    plan_grounding: PlanGroundingService
    plan_review_history: ReviewHistoryProjection
    plan_ai: PlanAIAdapter
    goal_planner: GoalPlannerService
    plan_lifecycle: PlanLifecycleService
    study_sessions: StudySessionService
    preview_registry: Any | None = None
    preview_service: Any | None = None
    runner_service: Any | None = None


def _build_runtime(settings: config.Settings) -> RuntimeServices:
    snapshot_publisher = CombinedSnapshotPublisher(
        settings.index_cache_path,
        builder=lambda: build_snapshot_for_settings(settings),
        expected_default_revision=settings.expected_default_pack_revision,
    )
    service_lock = ServiceLock(service_lock_path(settings.index_cache_path))
    user_source_search = LazyUserSourceSearch(
        settings.source_registry_path,
        settings.user_source_cache_path,
    )
    recall = MultiRecallService(
        snapshot_provider=snapshot_publisher.view,
        user_source_search=user_source_search,
    )
    qa_service = QaService(recall, scope=RetrievalScope.DEFAULT_PLUS_EXTRAS)
    review_plan_service = ReviewPlanService()
    quiz_service = QuizService()
    learning_store = SqliteLearningStore(settings.learning_store_path)
    review_scheduler = ReviewSchedulerService(
        repository=ReviewHistoryRepositoryAdapter(learning_store)
    )
    mastery_projection = MasteryProjectionService(learning_store)
    source_summary = LazySourceSummaryProjection(settings.source_registry_path)
    topic_graph = TopicGraphProjection()
    plan_grounding = PlanGroundingService(recall, source_summary=source_summary)
    plan_review_history = ReviewHistoryProjection(learning_store)
    plan_ai = PlanAIAdapter(
        proposer=(
            build_anthropic_proposer(token=settings.plan_ai_token)
            if settings.plan_ai_enabled
            else None
        ),
        limits=settings.plan_ai_limits,
        enabled=settings.plan_ai_enabled,
    )
    goal_planner = GoalPlannerService(
        mastery_projection=mastery_projection,
        source_summary=source_summary,
        topic_graph=topic_graph,
        review_history_projection=plan_review_history,
        plan_ai=plan_ai,
    )
    plan_lifecycle = PlanLifecycleService(
        learning_store,
        goal_planner,
        review_scheduler=review_scheduler,
    )
    study_sessions = StudySessionService(
        qa_service=QaService(recall, scope=RetrievalScope.DEFAULT_ONLY),
        quiz_service=quiz_service,
        review_scheduler=review_scheduler,
        session_repository=learning_store,
    )
    return RuntimeServices(
        settings=settings,
        snapshot_publisher=snapshot_publisher,
        service_lock=service_lock,
        user_source_search=user_source_search,
        recall=recall,
        qa=qa_service,
        review_plan=review_plan_service,
        quiz=quiz_service,
        learning_store=learning_store,
        review_scheduler=review_scheduler,
        mastery_projection=mastery_projection,
        source_summary=source_summary,
        topic_graph=topic_graph,
        plan_grounding=plan_grounding,
        plan_review_history=plan_review_history,
        plan_ai=plan_ai,
        goal_planner=goal_planner,
        plan_lifecycle=plan_lifecycle,
        study_sessions=study_sessions,
    )


def _plan_error(exc: Exception) -> HTTPException:
    """把计划生命周期领域异常映射为稳定错误码，避免用户输入错误变成 500。"""
    if isinstance(exc, PlanNotFoundError):
        return http_error(ErrorCode.PLAN_NOT_FOUND, str(exc))
    return http_error(ErrorCode.ILLEGAL_PLAN_PROGRESS_EVENT, str(exc))


def create_app(settings: config.Settings | None = None) -> FastAPI:
    """Create one isolated application and its owned runtime services."""
    selected = settings or config.DEFAULT_SETTINGS
    application = FastAPI(
        title="StudyAssistanceAgent API",
        description="局域网/本机学习辅助 API：多路召回检索知识库 + 带出处问答",
        version="0.1.0",
    )
    runtime = _build_runtime(selected)
    application.state.services = runtime

    if selected.agent_preview_enabled:
        from .preview_service import PreviewService, build_preview_router
        from .tool_registry import ToolRegistry
        from .tools.quiz import QuizTool
        from .tools.retrieve import RetrieveTool
        from .tools.review_due import ReviewDueTool

        runtime.preview_registry = ToolRegistry()
        runtime.preview_registry.register(RetrieveTool(runtime.recall))
        runtime.preview_registry.register(QuizTool(runtime.quiz))
        runtime.preview_registry.register(ReviewDueTool(runtime.review_scheduler))
        runtime.preview_service = PreviewService(
            token=selected.agent_preview_token,
            provider_key=selected.anthropic_api_key,
            registry=runtime.preview_registry,
            limits=selected.agent_preview_limits,
        )
        application.include_router(build_preview_router(runtime.preview_service))

    if selected.runner_enabled:
        from .runner_authority import RunnerWriteRegistry, argument_digest
        from .runner_service import RUNNER_PATH, RunnerService

        runtime.runner_service = RunnerService(
            store_path=selected.learning_store_path.parent / "runner_state.sqlite3",
            authority=RunnerWriteRegistry(),
        )

        @application.post(RUNNER_PATH)
        def autonomous_run(req: dict[str, Any]) -> dict[str, Any]:
            """可选自主 Runner（默认关闭）：提交**一次**受控复习记录写。

            写经既有 `ReviewSchedulerService.log_review`，Runner 不新增领域权威；kill switch 在
            每个效果边界生效；确认令牌由服务端按本次请求的精确参数签发，故不接受调用方提供的令牌。
            """
            runner = runtime.runner_service
            assert runner is not None
            job_id = str(req.get("job_id") or "")
            file_key = req.get("file")
            if not job_id or not isinstance(file_key, str) or not file_key:
                return {"terminal": "refused", "reason": "RUNNER_REQUEST_INVALID"}
            if runner.killed:
                return {"terminal": "cancelled", "reason": "RUNNER_KILLED"}
            arguments = {
                "file": file_key,
                "course": str(req.get("course") or ""),
                "source_session_id": str(req.get("source_session_id") or ""),
            }
            if runner.status(job_id) is None:
                runner.start_job(
                    job_id=job_id,
                    scope_id="m10-autonomous-runner-v1",
                    learner_id=str(req.get("learner_id") or "local"),
                )

            def domain_write() -> str:
                runtime.review_scheduler.log_review(ReviewLogRequest(**arguments))
                return argument_digest(arguments)

            outcome = runner.log_review(
                job_id=job_id,
                arguments=arguments,
                apply=domain_write,
            )
            return {
                "terminal": outcome.terminal.value,
                "reason": outcome.reason,
                "effect_id": outcome.effect_id,
                "replayed": outcome.replayed,
            }

    def initialize_runtime() -> None:
        enforce_single_worker_topology()
        runtime.service_lock.acquire()
        try:
            runtime.snapshot_publisher.publish()
        except Exception:
            runtime.service_lock.release()
            raise

    def shutdown_runtime() -> None:
        runtime.service_lock.release()

    application.router.add_event_handler("startup", initialize_runtime)
    application.router.add_event_handler("shutdown", shutdown_runtime)

    @application.get("/", include_in_schema=False)
    def workbench() -> FileResponse:
        """Serve the minimal learning workbench as the first screen."""
        if not _WORKBENCH_INDEX.is_file():
            raise http_error(
                ErrorCode.WORKBENCH_UNAVAILABLE,
                "learning workbench is unavailable",
            )
        return FileResponse(_WORKBENCH_INDEX)

    @application.get("/health")
    def health() -> dict[str, Any]:
        from .observability import metrics
        from .vector_store import LocalVectorStore, SqliteVectorStore

        if selected.vector_store == "sqlite":
            vector_engine = (
                "sqlite" if SqliteVectorStore.available() else "sqlite-unavailable"
            )
        else:
            vector_engine = (
                "linear" if LocalVectorStore.available() else "linear-unavailable"
            )
        _generation, chunks = runtime.snapshot_publisher.view(
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
            "llm_configured": bool(selected.llm_api_key),
        }

    @application.post("/api/v1/search", response_model=SearchResponse)
    def search(req: SearchRequest) -> SearchResponse:
        results, mode = runtime.recall.recall(
            req.question,
            req.top_k,
            course=req.course,
            scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
            use_vector=req.use_vector,
        )
        return SearchResponse(question=req.question, mode=mode, results=results)

    @application.post("/api/v1/qa", response_model=QaResponse)
    def qa(req: QaRequest) -> QaResponse:
        return runtime.qa.answer(req)

    @application.post("/api/v1/qa/stream")
    def qa_stream(req: QaRequest) -> StreamingResponse:
        resp = runtime.qa.answer(req)

        def gen() -> Any:
            meta = {
                "mode": resp.mode,
                "sources": [chunk.model_dump() for chunk in resp.sources],
            }
            yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"
            for para in resp.answer.split("\n\n"):
                yield f"data: {json.dumps({'delta': para}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @application.post("/api/v1/quiz", response_model=QuizResponse)
    def quiz(req: QuizRequest) -> QuizResponse:
        """测验生成：从知识条目例题、评测集、概念标签生成测验。"""
        return runtime.quiz.generate(req)

    @application.post("/api/v1/review-log")
    def review_log(req: ReviewLogRequest) -> dict[str, Any]:
        """记录一次复习完成，更新间隔重复排程。"""
        return runtime.review_scheduler.log_review(req)

    @application.get("/api/v1/review-due", response_model=ReviewDueResponse)
    def review_due(course: str | None = None) -> ReviewDueResponse:
        """查询今日待复习条目（基于遗忘曲线间隔重复）。"""
        return runtime.review_scheduler.get_due(course)

    @application.post("/api/v1/review-plan", response_model=ReviewPlanResponse)
    def review_plan(req: ReviewPlanRequest) -> ReviewPlanResponse:
        """生成复习计划：输入课程 + 目标日期 → 输出分日学习计划。"""
        return runtime.review_plan.generate(req)

    @application.post("/api/v1/plans", response_model=GoalPlanResponse)
    def goal_plan(req: GoalPlanRequest) -> GoalPlanResponse:
        """生成目标驱动学习计划（M9 确定性 Planner，仅生成、不写状态）。

        任务的 mastery 字段与排序取自权威 mastery 只读投影；plan_id 含派生输入摘要，
        因此复习/mastery 状态变化后会得到新的 plan_id（旧计划记录只读保留）。
        """
        response = runtime.goal_planner.generate(req)
        runtime.plan_lifecycle.persist_generated(response)
        return response

    @application.post("/api/v1/plans/{plan_id}/adopt")
    def adopt_plan(plan_id: str) -> dict[str, Any]:
        """采纳一个已生成的目标驱动计划。"""
        try:
            return runtime.plan_lifecycle.adopt(plan_id)
        except PlanNotFoundError as exc:
            raise _plan_error(exc) from exc

    @application.post(
        "/api/v1/plans/{plan_id}/progress",
        response_model=PlanProgressEvent,
    )
    def record_plan_progress(
        plan_id: str,
        req: PlanProgressRequest,
    ) -> PlanProgressEvent:
        """记录一个计划任务的进度事件（completed / skipped / overdue）。"""
        try:
            return runtime.plan_lifecycle.record_progress(req)
        except (PlanNotFoundError, IllegalPlanProgressEventError) as exc:
            raise _plan_error(exc) from exc

    @application.post("/api/v1/plans/{plan_id}/replan")
    def replan(
        plan_id: str,
        req: PlanReplanRequest | None = None,
    ) -> dict[str, Any]:
        """按未消费偏差（跳过 + 逾期 ≥ 3）或目标/约束变化确定性重规划，生成新 revision。

        已消费的偏差不再触发；未触发时不写盘，因此重复调用不会持续追加内容相同的新 revision。
        """
        try:
            return runtime.plan_lifecycle.replan(plan_id, req)
        except PlanNotFoundError as exc:
            raise _plan_error(exc) from exc

    @application.get("/api/v1/plans/{plan_id}")
    def get_plan(plan_id: str) -> dict[str, Any]:
        """查询一个目标驱动计划的当前状态。"""
        try:
            return runtime.plan_lifecycle.get(plan_id)
        except PlanNotFoundError as exc:
            raise _plan_error(exc) from exc

    @application.post("/api/v1/study-sessions", response_model=StudySessionResponse)
    def create_study_session(req: StudySessionCreateRequest) -> StudySessionResponse:
        """创建学习会话：检索讲解并出题。"""
        return runtime.study_sessions.create(req)

    @application.get(
        "/api/v1/study-sessions/{session_id}",
        response_model=StudySessionResponse,
    )
    def get_study_session(session_id: str) -> StudySessionResponse:
        """查询学习会话状态。"""
        try:
            return runtime.study_sessions.get(session_id)
        except SessionNotFoundError as exc:
            raise http_error(ErrorCode.SESSION_NOT_FOUND, str(exc)) from exc

    @application.post(
        "/api/v1/study-sessions/{session_id}/answers",
        response_model=StudySessionResponse,
    )
    def submit_study_answer(
        session_id: str,
        req: StudySessionAnswerRequest,
    ) -> StudySessionResponse:
        """提交当前题目答案并评估掌握度。"""
        try:
            return runtime.study_sessions.submit_answer(session_id, req)
        except SessionNotFoundError as exc:
            raise http_error(ErrorCode.SESSION_NOT_FOUND, str(exc)) from exc
        except IllegalSessionStateError as exc:
            raise http_error(ErrorCode.ILLEGAL_SESSION_STATE, str(exc)) from exc

    if _STATIC_DIR.is_dir():
        application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    return application


app = create_app()
_default_services: RuntimeServices = app.state.services

# Transitional compatibility aliases. New tests and callers use app.state.services.
_snapshot_publisher = _default_services.snapshot_publisher
_service_lock = _default_services.service_lock
_user_source_search = _default_services.user_source_search
_recall = _default_services.recall
_qa = _default_services.qa
_review_plan = _default_services.review_plan
_quiz = _default_services.quiz
_learning_store = _default_services.learning_store
_review_scheduler = _default_services.review_scheduler
_mastery_projection = _default_services.mastery_projection
_source_summary = _default_services.source_summary
_topic_graph = _default_services.topic_graph
_plan_grounding = _default_services.plan_grounding
_plan_review_history = _default_services.plan_review_history
_plan_ai = _default_services.plan_ai
_goal_planner = _default_services.goal_planner
_plan_lifecycle = _default_services.plan_lifecycle
_study_sessions = _default_services.study_sessions
_preview_registry = _default_services.preview_registry
_preview_service = _default_services.preview_service
_runner_service = _default_services.runner_service
