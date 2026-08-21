"""领域模型：知识块、检索请求/响应、问答请求/响应、复习计划。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RetrievalChunk(BaseModel):
    """知识库中的一个可检索切片（一篇文章或一个 `##` 小节），file 字段即出处。"""

    id: str = Field(description="稳定唯一 ID（文件路径 + 小节标题）")
    file: str = Field(description="知识库文件相对路径，作为回答时的出处")
    title: str = ""
    course: str = ""
    tags: list[str] = []
    difficulty: str = ""
    updated: str = ""
    content: str = ""
    score: float = 0.0


class SearchRequest(BaseModel):
    question: str
    top_k: int = 5
    course: str | None = None
    use_vector: bool = True


class SearchResponse(BaseModel):
    question: str
    mode: str  # hybrid | keyword-only
    results: list[RetrievalChunk]


class QaRequest(BaseModel):
    question: str
    top_k: int = 5
    course: str | None = None
    use_vector: bool = True
    use_llm: bool = False


class QaResponse(BaseModel):
    question: str
    answer: str
    mode: str
    sources: list[RetrievalChunk]
    generation_layer: str = Field(
        default="note_summary",
        description="grounded_llm | note_summary | no_hit",
    )


# ── 复习计划 ──────────────────────────────────────────────────────────────────


class ReviewPlanRequest(BaseModel):
    """复习计划请求：课程 + 目标日期 + 每日可用学时。"""

    course: str = Field(description="课程简称，如 os / ds / co")
    target_date: str | None = Field(default=None, description="目标日期 YYYY-MM-DD，默认 14 天后")
    hours_per_day: float = Field(default=2.0, ge=0.5, le=8.0, description="每天可用学习小时数")
    plan_name: str | None = Field(default=None, description="计划名称，默认 {course}-plan")


class PlanTask(BaseModel):
    """计划中的单个学习任务（对应一篇知识条目）。"""

    file: str = Field(description="知识库文件相对路径")
    title: str = Field(description="条目标题")
    difficulty: str = Field(description="难度：入门 / 中等 / 进阶")
    estimated_minutes: int = Field(description="预估学习时间（分钟）")
    priority: str = Field(description="优先级：high / medium / low")
    tags: list[str] = Field(default_factory=list, description="标签")


class PlanDay(BaseModel):
    """计划中的一天。"""

    day: int = Field(description="第几天（从 1 开始）")
    date: str = Field(description="日期 YYYY-MM-DD")
    tasks: list[PlanTask] = Field(description="当天任务列表")
    total_minutes: int = Field(description="当天总学习时间（分钟）")


class ReviewPlanResponse(BaseModel):
    """复习计划响应：分日学习计划 + 汇总。"""

    plan_name: str
    course: str
    generated_at: str
    target_date: str
    total_days: int
    total_hours: float
    days: list[PlanDay]
    summary: dict[str, Any]


# ── 测验生成 ──────────────────────────────────────────────────────────────────


class QuizRequest(BaseModel):
    """测验生成请求。"""

    course: str = Field(description="课程简称，如 os / ds / co")
    count: int = Field(default=5, ge=1, le=20, description="题目数量")
    difficulty: str | None = Field(default=None, description="难度筛选：入门 / 中等 / 进阶")
    topics: list[str] = Field(default_factory=list, description="按标签筛选，如 ['进程', '调度']")


class QuizQuestion(BaseModel):
    """单道测验题目。"""

    question: str = Field(description="题干")
    type: str = Field(description="题型：example（经典例题）/ concept（概念题）/ retrieval（检索题）")
    answer: str = Field(default="", description="参考答案（经典例题有完整解答，其他为空或提示）")
    source_file: str = Field(default="", description="来源文件路径")
    source_title: str = Field(default="", description="来源条目标题")
    tags: list[str] = Field(default_factory=list, description="相关标签")
    difficulty: str = Field(default="", description="难度")


class QuizResponse(BaseModel):
    """测验响应。"""

    quiz_name: str
    course: str
    generated_at: str
    count: int
    questions: list[QuizQuestion]
    summary: dict[str, Any]


# ── 复习排程 ──────────────────────────────────────────────────────────────────


class ReviewLogRequest(BaseModel):
    """记录一次复习完成。"""

    file: str = Field(description="知识条目文件路径，如 knowledge/os/process-management.md")
    course: str = Field(default="", description="课程简称（可选，自动从条目提取）")
    source_session_id: str = Field(default="", description="来源学习会话 ID，用于会话完成后的幂等记复习")


class ReviewEntry(BaseModel):
    """单条复习排程记录。"""

    file: str = Field(description="知识条目文件路径")
    title: str = Field(default="", description="条目标题")
    course: str = Field(default="", description="课程简称")
    last_reviewed: str = Field(description="上次复习时间 ISO 格式")
    review_count: int = Field(description="累计复习次数")
    next_review: str = Field(description="下次应复习时间 ISO 格式")
    days_overdue: int = Field(description="逾期天数（0 = 今天到期，正数 = 已逾期）")
    interval_days: int = Field(description="当前间隔天数")


class ReviewDueResponse(BaseModel):
    """今日待复习响应。"""

    course: str | None
    checked_at: str
    total_due: int
    entries: list[ReviewEntry]
    summary: dict[str, Any]

# ── 学习会话 ──────────────────────────────────────────────────────────────────


class StudySessionCreateRequest(BaseModel):
    """Create a learning session for one topic."""

    topic: str = Field(min_length=1, description="学习主题，如 死锁 / 进程调度")
    course: str = Field(pattern=r"^(os|ds|co)$", description="课程简称：os / ds / co")
    question_count: int = Field(default=1, ge=1, le=2, description="题目数量，1 或 2")
    use_llm: bool = Field(default=False, description="是否允许 QA 走 LLM，默认关闭")


class StudySessionAnswerRequest(BaseModel):
    """Submit an answer for the current session question."""

    answer: str = Field(min_length=1, description="用户答案")
    question_id: str | None = Field(default=None, description="题目 ID，默认当前题")


class StudySessionSource(BaseModel):
    file: str
    title: str = ""
    course: str = ""


class StudyQuestionView(BaseModel):
    """Public question payload. Reference answers are not included."""

    id: str
    question: str
    type: str
    source_file: str = ""
    source_title: str = ""
    difficulty: str = ""
    tags: list[str] = Field(default_factory=list)


class ToolTraceStep(BaseModel):
    step: str
    service: str
    status: str
    result_count: int = 0
    detail: str = ""
    state_after: str = ""


class AnswerEvaluation(BaseModel):
    question_id: str
    correct: bool
    score: float
    attempt_count: int
    feedback: str
    reference_answer: str = ""
    method: str = "deterministic"


class StudySessionResponse(BaseModel):
    session_id: str
    course: str
    topic: str
    state: str
    explanation: str
    sources: list[StudySessionSource]
    questions: list[StudyQuestionView]
    current_question_id: str | None = None
    attempt_count: int = 0
    score: float | None = None
    last_evaluation: AnswerEvaluation | None = None
    remediation: str = ""
    review: dict[str, Any] | None = None
    tool_trace: list[ToolTraceStep] = Field(default_factory=list)
    created_at: str
    updated_at: str
