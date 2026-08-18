"""Fixtures for deterministic M5b study-session tests."""

from __future__ import annotations

from app.models import (
    QaResponse,
    QuizQuestion,
    QuizResponse,
    RetrievalChunk,
    ReviewLogRequest,
)
from app.study_session import StudySessionService


class FakeQaService:
    def __init__(self, answer: str = "死锁需要互斥、占有并等待、不可剥夺和循环等待四个条件。"):
        self.answer_text = answer
        self.calls = 0

    def answer(self, req):
        self.calls += 1
        return QaResponse(
            question=req.question,
            answer=self.answer_text,
            mode="keyword-only",
            sources=[
                RetrievalChunk(
                    id="deadlock",
                    file="knowledge/os/deadlock.md",
                    title="死锁",
                    course=req.course or "os",
                    tags=["死锁", "同步"],
                    content=self.answer_text,
                )
            ],
        )


class FakeQuizService:
    def __init__(self, questions: list[QuizQuestion] | None = None):
        self.questions = questions or [
            QuizQuestion(
                question="死锁产生的四个必要条件是什么？",
                type="example",
                answer="互斥、占有并等待、不可剥夺、循环等待",
                source_file="knowledge/os/deadlock.md",
                source_title="死锁",
                tags=["死锁"],
                difficulty="中等",
            )
        ]
        self.calls = 0

    def generate(self, req):
        self.calls += 1
        selected = self.questions[: req.count]
        return QuizResponse(
            quiz_name=f"{req.course}-quiz",
            course=req.course,
            generated_at="2026-08-18T00:00:00",
            count=len(selected),
            questions=selected,
            summary={"total_pool": len(self.questions)},
        )


class FakeReviewScheduler:
    def __init__(self):
        self.logged: list[ReviewLogRequest] = []

    def log_review(self, req: ReviewLogRequest):
        self.logged.append(req)
        return {
            "file": req.file,
            "review_count": len(self.logged),
            "next_review": "2026-08-19T00:00:00",
            "interval_days": 1,
            "message": "已记录复习（第 1 次），下次复习：2026-08-19（1 天后）",
        }


def make_service(
    questions: list[QuizQuestion] | None = None,
    qa_answer: str | None = None,
) -> tuple[StudySessionService, FakeQaService, FakeQuizService, FakeReviewScheduler]:
    qa = FakeQaService(qa_answer) if qa_answer is not None else FakeQaService()
    quiz = FakeQuizService(questions)
    scheduler = FakeReviewScheduler()
    service = StudySessionService(
        qa_service=qa,
        quiz_service=quiz,
        review_scheduler=scheduler,
    )
    return service, qa, quiz, scheduler
