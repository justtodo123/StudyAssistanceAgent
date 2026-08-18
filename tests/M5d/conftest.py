"""Fixtures for M5d learning workbench tests."""

from __future__ import annotations

from pathlib import Path

WORKBENCH_DIR = Path(__file__).resolve().parents[2] / "platform" / "app" / "static" / "workbench"
WORKBENCH_INDEX = WORKBENCH_DIR / "index.html"
WORKBENCH_JS = WORKBENCH_DIR / "app.js"
WORKBENCH_CSS = WORKBENCH_DIR / "styles.css"

REQUIRED_VIEW_IDS = (
    "due-panel",
    "start-form",
    "topic",
    "course",
    "explanation",
    "sources",
    "question-panel",
    "answer-form",
    "feedback-panel",
    "completion-panel",
    "next-review",
)

ALLOWED_API_PREFIXES = (
    "/api/v1/review-due",
    "/api/v1/study-sessions",
)

FORBIDDEN_API_PREFIXES = (
    "/api/v1/qa",
    "/api/v1/quiz",
    "/api/v1/review-log",
    "/api/v1/review-plan",
    "/api/v1/search",
)