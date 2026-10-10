"""Dependency-injection container for LangGraph graphs.

Builds graph instances and injects the deterministic services they wrap.
The container is constructed once per FastAPI application and stored on
``app.state`` alongside :class:`app.main.RuntimeServices`.
"""

from __future__ import annotations

from typing import Any

from ..goal_planner import GoalPlannerService
from ..plan_lifecycle import PlanLifecycleService
from ..qa import QaService
from ..quiz import QuizService
from ..retrieval import MultiRecallService
from ..review_scheduler import ReviewSchedulerService
from .config import LangGraphLimits
from .llm import GraphLLM


class GraphContainer:
    """Holds compiled LangGraph graphs and the services they reference."""

    def __init__(
        self,
        recall: MultiRecallService,
        qa_service: QaService,
        quiz_service: QuizService,
        review_scheduler: ReviewSchedulerService,
        goal_planner: GoalPlannerService,
        plan_lifecycle: PlanLifecycleService,
        limits: LangGraphLimits | None = None,
        llm: GraphLLM | None = None,
    ) -> None:
        self.recall = recall
        self.qa_service = qa_service
        self.quiz_service = quiz_service
        self.review_scheduler = review_scheduler
        self.goal_planner = goal_planner
        self.plan_lifecycle = plan_lifecycle
        self.limits = limits or LangGraphLimits()
        self.llm = llm

        self._study_graph: Any = None
        self._submit_graph: Any = None
        self._plan_graph: Any = None
        self._assistance_graph: Any = None

    @property
    def study_graph(self) -> Any:
        if self._study_graph is None:
            from .study_graph import build_study_graph

            self._study_graph = build_study_graph(self)
        return self._study_graph

    @property
    def submit_graph(self) -> Any:
        if self._submit_graph is None:
            from .study_graph import build_submit_graph

            self._submit_graph = build_submit_graph(self)
        return self._submit_graph

    @property
    def plan_graph(self) -> Any:
        if self._plan_graph is None:
            from .plan_graph import build_plan_graph

            self._plan_graph = build_plan_graph(self)
        return self._plan_graph

    @property
    def assistance_graph(self) -> Any:
        if self._assistance_graph is None:
            from .assistance_graph import build_assistance_graph

            self._assistance_graph = build_assistance_graph(self)
        return self._assistance_graph
