"""Study session orchestrator for the M5b learning loop.

The service only coordinates existing QA, quiz, and review services.
It does not reimplement retrieval, question generation, or scheduling.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import (
    AnswerEvaluation,
    QaRequest,
    QuizQuestion,
    QuizRequest,
    RetrievalChunk,
    ReviewLogRequest,
    StudyQuestionView,
    StudySessionAnswerRequest,
    StudySessionCreateRequest,
    StudySessionResponse,
    StudySessionSource,
    ToolTraceStep,
)
from .learning_store import StudySessionRepository
from .qa import QaService
from .quiz import QuizService
from .review_scheduler import ReviewSchedulerService

STATE_CREATED = "created"
STATE_EXPLAINING = "explaining"
STATE_AWAITING_ANSWER = "awaiting_answer"
STATE_EVALUATING = "evaluating"
STATE_REMEDIATION = "remediation"
STATE_COMPLETED = "completed"

ANSWERABLE_STATES = {STATE_AWAITING_ANSWER, STATE_REMEDIATION}
CORRECT_FIRST_TRY = 1.0
CORRECT_SECOND_TRY = 0.6
MAX_ATTEMPTS = 2
COVERAGE_THRESHOLD = 0.55
_PUNCTUATION_RE = re.compile(r"[，。！？、；：:“”‘’'\".,!?;:()\[\]{}<>\s]")


class SessionNotFoundError(Exception):
    """Raised when a session id is unknown."""


class IllegalSessionStateError(Exception):
    """Raised when an action is not allowed in the current state."""


@dataclass
class _QuestionState:
    id: str
    question: QuizQuestion
    attempt_count: int = 0
    correct: bool | None = None


@dataclass
class _Session:
    session_id: str
    course: str
    topic: str
    state: str
    explanation: str = ""
    sources: list[RetrievalChunk] = field(default_factory=list)
    questions: list[_QuestionState] = field(default_factory=list)
    current_index: int = 0
    score: float | None = None
    last_evaluation: AnswerEvaluation | None = None
    remediation: str = ""
    review: dict[str, Any] | None = None
    tool_trace: list[ToolTraceStep] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    last_answer_normalized: str = ""
    answer_records: list[dict[str, Any]] = field(default_factory=list)


class StudySessionService:
    """Finite-state orchestrator for one learning topic."""

    def __init__(
        self,
        qa_service: QaService | None = None,
        quiz_service: QuizService | None = None,
        review_scheduler: ReviewSchedulerService | None = None,
        session_repository: StudySessionRepository | None = None,
    ) -> None:
        self._qa = qa_service or QaService()
        self._quiz = quiz_service or QuizService()
        self._scheduler = review_scheduler or ReviewSchedulerService()
        self._session_repository = session_repository
        self._sessions: dict[str, _Session] = {}

    def create(self, req: StudySessionCreateRequest) -> StudySessionResponse:
        now = _now()
        session = _Session(
            session_id=uuid.uuid4().hex,
            course=req.course,
            topic=req.topic.strip(),
            state=STATE_CREATED,
            created_at=now,
            updated_at=now,
        )
        self._sessions[session.session_id] = session
        self._trace(
            session,
            step="create",
            service="StudySessionService",
            status="ok",
            result_count=1,
            detail="session created",
            state_after=STATE_CREATED,
        )

        session.state = STATE_EXPLAINING
        session.updated_at = _now()
        qa_resp = self._qa.answer(
            QaRequest(question=session.topic, course=session.course, use_llm=req.use_llm)
        )
        session.explanation = qa_resp.answer
        session.sources = list(qa_resp.sources)
        self._trace(
            session,
            step="qa",
            service="QaService",
            status="ok",
            result_count=len(session.sources),
            detail=f"retrieved {len(session.sources)} sources",
            state_after=STATE_EXPLAINING,
        )
        self._trace(
            session,
            step="explain",
            service="StudySessionService",
            status="ok",
            result_count=1,
            detail="built explanation from retrieved notes",
            state_after=STATE_EXPLAINING,
        )

        selected = self._select_questions(session, req.question_count)
        session.questions = [
            _QuestionState(id=f"q{index + 1}", question=item)
            for index, item in enumerate(selected)
        ]
        if session.questions:
            session.state = STATE_AWAITING_ANSWER
            types = ",".join(item.question.type for item in session.questions)
            self._trace(
                session,
                step="quiz",
                service="QuizService",
                status="ok",
                result_count=len(session.questions),
                detail=f"generated {len(session.questions)} question(s): {types}",
                state_after=STATE_AWAITING_ANSWER,
            )
        else:
            self._trace(
                session,
                step="quiz",
                service="QuizService",
                status="fallback",
                result_count=0,
                detail="no questions available; complete after explanation",
                state_after=STATE_COMPLETED,
            )
            self._complete(session)
        session.updated_at = _now()
        self._persist(session)
        return self.to_response(session)

    def get(self, session_id: str) -> StudySessionResponse:
        return self.to_response(self._require(session_id))

    def submit_answer(
        self,
        session_id: str,
        req: StudySessionAnswerRequest,
    ) -> StudySessionResponse:
        session = self._require(session_id)
        if session.state not in ANSWERABLE_STATES:
            raise IllegalSessionStateError(
                f"cannot submit an answer while session is {session.state}"
            )
        if not session.questions:
            raise IllegalSessionStateError("session has no questions to answer")

        question_state = self._current_question(session, req.question_id)
        normalized = _normalize(req.answer)
        if (
            session.last_answer_normalized
            and session.last_answer_normalized == normalized
            and session.last_evaluation is not None
            and session.last_evaluation.question_id == question_state.id
        ):
            return self.to_response(session)
        session.state = STATE_EVALUATING
        session.updated_at = _now()
        question_state.attempt_count += 1
        session.last_answer_normalized = normalized

        evaluation = evaluate_answer(
            req.answer,
            question_state.question,
            session.explanation,
        )
        evaluation.question_id = question_state.id
        evaluation.attempt_count = question_state.attempt_count
        self._trace(
            session,
            step="evaluate",
            service="StudySessionService",
            status="ok",
            result_count=1,
            detail="correct" if evaluation.correct else "incorrect",
            state_after=STATE_EVALUATING,
        )

        if evaluation.correct:
            question_state.correct = True
            session.remediation = ""
            session.last_evaluation = evaluation
            self._record_attempt(session, question_state, normalized, evaluation)
            self._advance_or_complete(session)
            self._persist(session)
            return self.to_response(session)

        question_state.correct = False
        if question_state.attempt_count < MAX_ATTEMPTS:
            evaluation.reference_answer = ""
            session.last_evaluation = evaluation
            self._record_attempt(session, question_state, normalized, evaluation)
            session.remediation = _hint(question_state.question, session.explanation)
            session.state = STATE_REMEDIATION
            self._trace(
                session,
                step="remediation",
                service="StudySessionService",
                status="ok",
                result_count=1,
                detail="provided hint after incorrect answer",
                state_after=STATE_REMEDIATION,
            )
            session.state = STATE_AWAITING_ANSWER
            self._trace(
                session,
                step="retry",
                service="StudySessionService",
                status="ok",
                result_count=1,
                detail="waiting for another attempt",
                state_after=STATE_AWAITING_ANSWER,
            )
            session.updated_at = _now()
            self._persist(session)
            return self.to_response(session)

        session.remediation = _full_explanation(question_state.question, session.explanation)
        evaluation.reference_answer = question_state.question.answer or session.explanation
        session.last_evaluation = evaluation
        self._record_attempt(session, question_state, normalized, evaluation)
        self._trace(
            session,
            step="remediation",
            service="StudySessionService",
            status="ok",
            result_count=1,
            detail="returned full explanation after two incorrect answers",
            state_after=STATE_REMEDIATION,
        )
        self._advance_or_complete(session)
        self._persist(session)
        return self.to_response(session)

    def to_response(self, session: _Session) -> StudySessionResponse:
        current_id = None
        if session.questions and session.state in ANSWERABLE_STATES:
            current_id = session.questions[session.current_index].id
        return StudySessionResponse(
            session_id=session.session_id,
            course=session.course,
            topic=session.topic,
            state=session.state,
            explanation=session.explanation,
            sources=[
                StudySessionSource(file=item.file, title=item.title, course=item.course)
                for item in session.sources
            ],
            questions=[
                StudyQuestionView(
                    id=item.id,
                    question=item.question.question,
                    type=item.question.type,
                    source_file=item.question.source_file,
                    source_title=item.question.source_title,
                    difficulty=item.question.difficulty,
                    tags=list(item.question.tags),
                )
                for item in session.questions
            ],
            current_question_id=current_id,
            attempt_count=self._current_attempts(session),
            score=session.score,
            last_evaluation=session.last_evaluation,
            remediation=session.remediation,
            review=session.review,
            tool_trace=list(session.tool_trace),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def _require(self, session_id: str) -> _Session:
        session = self._sessions.get(session_id)
        if session is None and self._session_repository is not None:
            record = self._session_repository.get(session_id)
            if record is not None:
                session = deserialize_session(record)
                self._sessions[session_id] = session
        if session is None:
            raise SessionNotFoundError(f"study session not found: {session_id}")
        return session

    def _current_question(self, session: _Session, question_id: str | None) -> _QuestionState:
        current = session.questions[session.current_index]
        if question_id and question_id != current.id:
            raise IllegalSessionStateError(
                f"expected answer for {current.id}, got {question_id}"
            )
        return current

    def _select_questions(self, session: _Session, count: int) -> list[QuizQuestion]:
        topics = [session.topic]
        for source in session.sources:
            topics.extend(source.tags)
        unique_topics: list[str] = []
        seen: set[str] = set()
        for topic in topics:
            cleaned = topic.strip()
            if cleaned and cleaned not in seen:
                unique_topics.append(cleaned)
                seen.add(cleaned)

        pool = self._quiz.generate(
            QuizRequest(course=session.course, count=max(count * 3, 6), topics=unique_topics[:4])
        ).questions
        if len(pool) < count:
            pool.extend(
                self._quiz.generate(
                    QuizRequest(course=session.course, count=max(count * 3, 6))
                ).questions
            )
        return _prefer_examples(pool, count)

    def _advance_or_complete(self, session: _Session) -> None:
        session.score = _session_score(session)
        if session.current_index + 1 < len(session.questions):
            session.current_index += 1
            session.state = STATE_AWAITING_ANSWER
            session.updated_at = _now()
            self._trace(
                session,
                step="next-question",
                service="StudySessionService",
                status="ok",
                result_count=1,
                detail=f"moved to {session.questions[session.current_index].id}",
                state_after=STATE_AWAITING_ANSWER,
            )
            return
        self._complete(session)

    def _complete(self, session: _Session) -> None:
        session.score = _session_score(session)
        if session.review is None:
            session.review = self._log_review(session)
        session.state = STATE_COMPLETED
        session.updated_at = _now()
        review_file = ""
        if session.review:
            review_file = str(session.review.get("file", ""))
        self._trace(
            session,
            step="review-log",
            service="ReviewSchedulerService",
            status="ok",
            result_count=1 if session.review else 0,
            detail=f"recorded review for {review_file}" if review_file else "review recorded",
            state_after=STATE_COMPLETED,
        )

    def _log_review(self, session: _Session) -> dict[str, Any]:
        source_file = ""
        if session.sources:
            source_file = session.sources[0].file
        elif session.questions:
            source_file = session.questions[0].question.source_file
        if not source_file:
            source_file = f"knowledge/{session.course}/{session.topic}.md"
        return self._scheduler.log_review(
            ReviewLogRequest(
                file=source_file,
                course=session.course,
                source_session_id=session.session_id,
            )
        )

    def _trace(
        self,
        session: _Session,
        *,
        step: str,
        service: str,
        status: str,
        result_count: int,
        detail: str,
        state_after: str,
    ) -> None:
        session.tool_trace.append(
            ToolTraceStep(
                step=step,
                service=service,
                status=status,
                result_count=result_count,
                detail=detail,
                state_after=state_after,
            )
        )

    def _persist(self, session: _Session) -> None:
        if self._session_repository is None:
            return
        self._session_repository.save(serialize_session(session))

    @staticmethod
    def _record_attempt(
        session: _Session,
        question_state: _QuestionState,
        normalized: str,
        evaluation: AnswerEvaluation,
    ) -> None:
        session.answer_records.append(
            {
                "question_id": question_state.id,
                "attempt_count": question_state.attempt_count,
                "answer_normalized": normalized,
                "correct": evaluation.correct,
                "feedback": evaluation.feedback,
                "created_at": _now(),
            }
        )

    @staticmethod
    def _current_attempts(session: _Session) -> int:
        if not session.questions or session.current_index >= len(session.questions):
            if session.questions:
                return session.questions[-1].attempt_count
            return 0
        return session.questions[session.current_index].attempt_count


def evaluate_answer(
    user_answer: str,
    question: QuizQuestion,
    explanation: str,
) -> AnswerEvaluation:
    """Deterministic grader. LLM judging is intentionally out of scope for M5b."""
    normalized = _normalize(user_answer)
    if not normalized:
        return AnswerEvaluation(
            question_id="",
            correct=False,
            score=0.0,
            attempt_count=0,
            feedback="empty answer",
            method="deterministic",
        )

    references = [item for item in (question.answer, explanation) if item]
    references.extend(question.tags)
    if question.source_title:
        references.append(question.source_title)
    best_coverage = 0.0
    matched_substring = False
    for reference in references:
        ref_norm = _normalize(reference)
        if not ref_norm:
            continue
        if len(normalized) >= 2 and normalized in ref_norm:
            matched_substring = True
        best_coverage = max(best_coverage, _coverage(normalized, ref_norm))

    correct = matched_substring or best_coverage >= COVERAGE_THRESHOLD
    return AnswerEvaluation(
        question_id="",
        correct=correct,
        score=1.0 if correct else 0.0,
        attempt_count=0,
        feedback="matched reference" if correct else "did not match reference",
        reference_answer=question.answer if correct else "",
        method="deterministic",
    )


def _prefer_examples(pool: list[QuizQuestion], count: int) -> list[QuizQuestion]:
    unique: list[QuizQuestion] = []
    seen: set[str] = set()
    for item in sorted(pool, key=lambda question: 0 if question.type == "example" else 1):
        key = item.question.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= count:
            break
    return unique


def _session_score(session: _Session) -> float | None:
    finished = [item for item in session.questions if item.correct is not None]
    if not finished:
        return None
    values: list[float] = []
    for item in finished:
        if item.correct and item.attempt_count <= 1:
            values.append(CORRECT_FIRST_TRY)
        elif item.correct:
            values.append(CORRECT_SECOND_TRY)
        else:
            values.append(0.0)
    return round(sum(values) / len(values), 3)


def _hint(question: QuizQuestion, explanation: str) -> str:
    seed = question.answer or explanation
    snippet = _first_sentence(seed)
    if snippet:
        return f"提示：{snippet} 请结合出处再答一次。"
    return "请结合讲解和来源笔记再答一次。"


def _full_explanation(question: QuizQuestion, explanation: str) -> str:
    if question.answer:
        return f"完整参考：{question.answer}"
    return explanation


def _first_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    for separator in ("。", "！", "？", ".", "!", "?"):
        index = cleaned.find(separator)
        if 8 <= index <= 80:
            return cleaned[: index + 1]
    return cleaned[:80]


def _normalize(text: str) -> str:
    return _PUNCTUATION_RE.sub("", text).lower()


def _ngrams(text: str, size: int = 2) -> set[str]:
    if not text:
        return set()
    if len(text) < size:
        return {text}
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def _coverage(user: str, reference: str) -> float:
    user_grams = _ngrams(user)
    ref_grams = _ngrams(reference)
    if not user_grams or not ref_grams:
        return 0.0
    return len(user_grams & ref_grams) / len(user_grams)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def serialize_session(session: _Session) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "course": session.course,
        "topic": session.topic,
        "state": session.state,
        "explanation": session.explanation,
        "sources": [item.model_dump() for item in session.sources],
        "questions": [
            {
                "id": item.id,
                "question": item.question.model_dump(),
                "attempt_count": item.attempt_count,
                "correct": item.correct,
            }
            for item in session.questions
        ],
        "current_index": session.current_index,
        "score": session.score,
        "last_evaluation": None
        if session.last_evaluation is None
        else session.last_evaluation.model_dump(),
        "remediation": session.remediation,
        "review": session.review,
        "tool_trace": [item.model_dump() for item in session.tool_trace],
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "last_answer_normalized": session.last_answer_normalized,
        "answer_records": list(session.answer_records),
    }


def deserialize_session(record: dict[str, Any]) -> _Session:
    questions = [
        _QuestionState(
            id=item["id"],
            question=QuizQuestion.model_validate(item["question"]),
            attempt_count=int(item.get("attempt_count", 0)),
            correct=item.get("correct"),
        )
        for item in record.get("questions", [])
    ]
    last_evaluation = record.get("last_evaluation")
    return _Session(
        session_id=record["session_id"],
        course=record.get("course", ""),
        topic=record.get("topic", ""),
        state=record.get("state", STATE_CREATED),
        explanation=record.get("explanation", ""),
        sources=[RetrievalChunk.model_validate(item) for item in record.get("sources", [])],
        questions=questions,
        current_index=int(record.get("current_index", 0)),
        score=record.get("score"),
        last_evaluation=None
        if last_evaluation is None
        else AnswerEvaluation.model_validate(last_evaluation),
        remediation=record.get("remediation", ""),
        review=record.get("review"),
        tool_trace=[ToolTraceStep.model_validate(item) for item in record.get("tool_trace", [])],
        created_at=record.get("created_at", ""),
        updated_at=record.get("updated_at", ""),
        last_answer_normalized=record.get("last_answer_normalized", ""),
        answer_records=list(record.get("answer_records", [])),
    )
