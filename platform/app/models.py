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
