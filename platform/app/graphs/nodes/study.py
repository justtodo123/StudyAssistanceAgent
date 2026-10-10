"""Study-session graph nodes — wrap QaService, QuizService, evaluate_answer.

Each function takes the graph *state* dict and returns a partial dict
that LangGraph merges back.  The functions call the same deterministic
services used by :class:`app.study_session.StudySessionService` so the
v2 graph produces results consistent with v1.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from ...models import (
    QaRequest,
    QuizQuestion,
    QuizRequest,
    RetrievalChunk,
    ReviewLogRequest,
)
from ...qa import QaService
from ...quiz import QuizService
from ...review_scheduler import ReviewSchedulerService
from ...study_session import (
    MAX_ATTEMPTS,
    STATE_AWAITING_ANSWER,
    STATE_COMPLETED,
    STATE_EXPLAINING,
    STATE_REMEDIATION,
    evaluate_answer,
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hint(question: QuizQuestion, explanation: str) -> str:
    seed = question.answer or explanation
    snippet = " ".join(seed.split())
    if snippet:
        for sep in ("。", "！", "？", ".", "!", "?"):
            idx = snippet.find(sep)
            if 8 <= idx <= 80:
                return f"提示：{snippet[: idx + 1]} 请结合出处再答一次。"
        return f"提示：{snippet[:80]} 请结合讲解和来源笔记再答一次。"
    return "请结合讲解和来源笔记再答一次。"


def _full_explanation(question: QuizQuestion, explanation: str) -> str:
    if question.answer:
        return f"完整参考：{question.answer}"
    return explanation


def _prefer_examples(pool: list[QuizQuestion], count: int) -> list[QuizQuestion]:
    unique: list[QuizQuestion] = []
    seen: set[str] = set()
    for q in sorted(pool, key=lambda item: 0 if item.type == "example" else 1):
        key = q.question.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(q)
        if len(unique) >= count:
            break
    return unique


def _session_score(questions: list[dict[str, Any]]) -> float | None:
    finished = [q for q in questions if q.get("correct") is not None]
    if not finished:
        return None
    values: list[float] = []
    for q in finished:
        if q["correct"] and q.get("attempt_count", 0) <= 1:
            values.append(1.0)
        elif q["correct"]:
            values.append(0.6)
        else:
            values.append(0.0)
    return round(sum(values) / len(values), 3)


def _build_question(question: QuizQuestion, index: int) -> dict[str, Any]:
    return {
        "id": f"q{index + 1}",
        "question": question.question,
        "type": question.type,
        "answer": question.answer,
        "source_file": question.source_file,
        "source_title": question.source_title,
        "difficulty": question.difficulty,
        "tags": list(question.tags),
        "attempt_count": 0,
        "correct": None,
    }


# ── Graph nodes ──────────────────────────────────────────────────────────────


def initialize_node(
    state: dict[str, Any],
    *,
    qa_service: QaService,
    quiz_service: QuizService,
) -> dict[str, Any]:
    """Retrieve explanation + generate questions (maps to CREATED → AWAITING_ANSWER)."""
    session_id = state.get("session_id") or uuid.uuid4().hex
    course = state.get("course", "")
    topic = state.get("topic", "")
    question_count = state.get("question_count", 1)
    use_llm = state.get("use_llm", False)

    qa_resp = qa_service.answer(
        QaRequest(question=topic, course=course, use_llm=use_llm)
    )
    explanation = qa_resp.answer
    sources = [chunk.model_dump() for chunk in qa_resp.sources]

    topics = [topic]
    for src in qa_resp.sources:
        topics.extend(src.tags)
    unique_topics: list[str] = []
    seen: set[str] = set()
    for t in topics:
        cleaned = t.strip()
        if cleaned and cleaned not in seen:
            unique_topics.append(cleaned)
            seen.add(cleaned)

    pool = quiz_service.generate(
        QuizRequest(
            course=course,
            count=max(question_count * 3, 6),
            topics=unique_topics[:4],
        )
    ).questions
    if len(pool) < question_count:
        pool.extend(
            quiz_service.generate(
                QuizRequest(course=course, count=max(question_count * 3, 6))
            ).questions
        )
    selected = _prefer_examples(pool, question_count)

    questions = [_build_question(q, i) for i, q in enumerate(selected)]

    if questions:
        new_state = "awaiting_answer"
    else:
        new_state = "completed"

    return {
        "session_id": session_id,
        "course": course,
        "topic": topic,
        "state": new_state,
        "explanation": explanation,
        "sources": sources,
        "questions": questions,
        "current_index": 0,
        "score": _session_score(questions) if new_state == "completed" else None,
        "tool_trace": [
            {
                "step": "initialize",
                "service": "LangGraph StudyNode",
                "status": "ok",
                "result_count": len(questions),
                "detail": f"explanation + {len(questions)} question(s)",
                "state_after": new_state,
            }
        ],
    }


def evaluate_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate the user's answer for the current question."""
    questions = list(state.get("questions") or [])
    current_index = state.get("current_index", 0)
    answer = state.get("current_answer", "")
    explanation = state.get("explanation", "")

    if not questions or current_index >= len(questions):
        return {"state": "completed"}

    q = questions[current_index]
    quiz_q = QuizQuestion(
        question=q["question"],
        type=q.get("type", "example"),
        answer=q.get("answer", ""),
        source_file=q.get("source_file", ""),
        source_title=q.get("source_title", ""),
        tags=q.get("tags", []),
        difficulty=q.get("difficulty", ""),
    )

    evaluation = evaluate_answer(answer, quiz_q, explanation)
    q["attempt_count"] = q.get("attempt_count", 0) + 1

    eval_dict = {
        "question_id": q["id"],
        "correct": evaluation.correct,
        "score": evaluation.score,
        "attempt_count": q["attempt_count"],
        "feedback": evaluation.feedback,
        "reference_answer": evaluation.reference_answer,
        "method": evaluation.method,
    }

    updates: dict[str, Any] = {
        "questions": questions,
        "last_evaluation": eval_dict,
        "state": "evaluating",
    }

    if evaluation.correct:
        q["correct"] = True
        updates["remediation"] = ""
    elif q["attempt_count"] < MAX_ATTEMPTS:
        q["correct"] = False
        eval_dict["reference_answer"] = ""
        updates["remediation"] = _hint(quiz_q, explanation)
        updates["state"] = STATE_AWAITING_ANSWER
    else:
        q["correct"] = False
        updates["remediation"] = _full_explanation(quiz_q, explanation)
        eval_dict["reference_answer"] = quiz_q.answer or explanation

    return updates


def advance_node(
    state: dict[str, Any],
    *,
    review_scheduler: ReviewSchedulerService | None = None,
    course: str = "",
    session_id: str = "",
) -> dict[str, Any]:
    """Move to the next question or complete the session."""
    questions = list(state.get("questions") or [])
    current_index = state.get("current_index", 0)
    last_eval = state.get("last_evaluation") or {}

    if last_eval.get("correct"):
        pass
    elif questions and current_index < len(questions):
        q = questions[current_index]
        if q.get("attempt_count", 0) < MAX_ATTEMPTS and not q.get("correct"):
            return {
                "state": STATE_AWAITING_ANSWER,
                "questions": questions,
            }

    if current_index + 1 < len(questions):
        return {
            "current_index": current_index + 1,
            "state": STATE_AWAITING_ANSWER,
            "score": _session_score(questions),
        }

    score = _session_score(questions)
    review: dict[str, Any] | None = None
    if review_scheduler is not None:
        sources = state.get("sources") or []
        source_file = ""
        if sources:
            source_file = sources[0].get("file", "")
        elif questions:
            source_file = questions[0].get("source_file", "")
        if not source_file:
            source_file = f"knowledge/{course}/{state.get('topic', '')}.md"
        review = review_scheduler.log_review(
            ReviewLogRequest(
                file=source_file,
                course=course,
                source_session_id=session_id,
            )
        )

    return {
        "state": STATE_COMPLETED,
        "score": score,
        "review": review,
    }


def remediation_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Generate remediation after an incorrect answer."""
    questions = list(state.get("questions") or [])
    current_index = state.get("current_index", 0)
    explanation = state.get("explanation", "")

    if not questions or current_index >= len(questions):
        return {"state": STATE_COMPLETED}

    q = questions[current_index]
    quiz_q = QuizQuestion(
        question=q["question"],
        type=q.get("type", "example"),
        answer=q.get("answer", ""),
        source_file=q.get("source_file", ""),
        source_title=q.get("source_title", ""),
        tags=q.get("tags", []),
        difficulty=q.get("difficulty", ""),
    )

    if q.get("attempt_count", 0) >= MAX_ATTEMPTS:
        remediation = _full_explanation(quiz_q, explanation)
    else:
        remediation = _hint(quiz_q, explanation)

    return {
        "remediation": remediation,
        "state": STATE_REMEDIATION,
    }
