"""M9 测试 fixtures。"""

from __future__ import annotations

import pytest


@pytest.fixture
def goal_planner_service():
    """空复习历史的确定性 Planner（全部条目视为未复习）。"""
    from app.goal_planner import GoalPlannerService

    return GoalPlannerService(review_history={})
