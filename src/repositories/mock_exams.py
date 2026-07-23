from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import MockExam, MockExamAttempt, MockExamDraft
from ..utils import now


def insert_exam(
    conn: Session,
    user_id: int,
    study4_test_id: int,
    selected_part: str,
) -> int:
    timestamp = now()
    exam = MockExam(
        user_id=user_id,
        study4_test_id=study4_test_id,
        selected_part=selected_part,
        status="in_progress",
        created_at=timestamp,
        updated_at=timestamp,
    )
    conn.add(exam)
    conn.flush()
    return exam.id


def get_exam(
    conn: Session,
    user_id: int,
    mock_exam_id: int,
) -> dict[str, Any] | None:
    row = conn.execute(
        select(
            MockExam.id,
            MockExam.user_id,
            MockExam.study4_test_id,
            MockExam.selected_part,
            MockExam.status,
            MockExam.raw_score,
            MockExam.scaled_score,
            MockExam.created_at,
            MockExam.updated_at,
            MockExam.completed_at,
        ).where(
            MockExam.id == mock_exam_id,
            MockExam.user_id == user_id,
        )
    ).first()
    return dict(row._mapping) if row else None


def list_exams(
    conn: Session,
    user_id: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        select(
            MockExam.id,
            MockExam.study4_test_id,
            MockExam.selected_part,
            MockExam.status,
            MockExam.raw_score,
            MockExam.scaled_score,
            MockExam.created_at,
            MockExam.completed_at,
        )
        .where(MockExam.user_id == user_id)
        .order_by(MockExam.created_at.desc())
    ).all()
    return [dict(row._mapping) for row in rows]


def complete_exam(
    conn: Session,
    mock_exam_id: int,
    raw_score: float,
    scaled_score: int,
) -> None:
    timestamp = now()
    exam = conn.get(MockExam, mock_exam_id)
    if exam is None:
        return
    exam.status = "completed"
    exam.raw_score = raw_score
    exam.scaled_score = scaled_score
    exam.completed_at = timestamp
    exam.updated_at = timestamp


def upsert_draft(
    conn: Session,
    mock_exam_id: int,
    question_number: int,
    body: str,
) -> None:
    timestamp = now()
    draft = conn.scalar(
        select(MockExamDraft).where(
            MockExamDraft.mock_exam_id == mock_exam_id,
            MockExamDraft.question_number == question_number,
        )
    )
    if draft is None:
        conn.add(
            MockExamDraft(
                mock_exam_id=mock_exam_id,
                question_number=question_number,
                body=body,
                updated_at=timestamp,
            )
        )
        return
    draft.body = body
    draft.updated_at = timestamp


def list_drafts(
    conn: Session,
    mock_exam_id: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        select(
            MockExamDraft.question_number,
            MockExamDraft.body,
        )
        .where(MockExamDraft.mock_exam_id == mock_exam_id)
        .order_by(MockExamDraft.question_number)
    ).all()
    return [dict(row._mapping) for row in rows]


def insert_attempt(
    conn: Session,
    mock_exam_id: int,
    question_number: int,
    answer: str,
    score_state: str,
    model: str,
) -> int:
    timestamp = now()
    attempt = MockExamAttempt(
        mock_exam_id=mock_exam_id,
        question_number=question_number,
        answer=answer,
        score_text="",
        score_state=score_state,
        model=model,
        created_at=timestamp,
        updated_at=timestamp,
    )
    conn.add(attempt)
    conn.flush()
    return attempt.id


def mark_visible(
    conn: Session,
    attempt_id: int,
    score_text: str,
    score_10: float | None,
    converted_score: float | None,
    max_score: int | None,
) -> None:
    attempt = conn.get(MockExamAttempt, attempt_id)
    if attempt is None:
        return
    attempt.score_text = score_text
    attempt.score_state = "visible"
    attempt.score_10 = score_10
    attempt.converted_score = converted_score
    attempt.max_score = max_score
    attempt.updated_at = now()


def mark_error(
    conn: Session,
    attempt_id: int,
    detail: str,
    max_score: int | None = None,
) -> None:
    attempt = conn.get(MockExamAttempt, attempt_id)
    if attempt is None:
        return
    attempt.score_state = "error"
    attempt.score_text = detail
    attempt.converted_score = 0
    if max_score is not None:
        attempt.max_score = max_score
    attempt.updated_at = now()


def list_attempts(
    conn: Session,
    mock_exam_id: int,
) -> list[dict[str, Any]]:
    latest_ids = (
        select(func.max(MockExamAttempt.id).label("id"))
        .where(MockExamAttempt.mock_exam_id == mock_exam_id)
        .group_by(MockExamAttempt.question_number)
    ).subquery()

    rows = conn.execute(
        select(
            MockExamAttempt.id,
            MockExamAttempt.question_number,
            MockExamAttempt.answer,
            MockExamAttempt.score_text,
            MockExamAttempt.score_state,
            MockExamAttempt.score_10,
            MockExamAttempt.converted_score,
            MockExamAttempt.max_score,
            MockExamAttempt.model,
            MockExamAttempt.created_at,
        )
        .join(latest_ids, MockExamAttempt.id == latest_ids.c.id)
        .order_by(MockExamAttempt.question_number)
    ).all()
    return [dict(row._mapping) for row in rows]


def normalize_streaming(conn: Session, mock_exam_id: int) -> None:
    from ..services.mock_scoring import MAX_SCORES

    rows = conn.scalars(
        select(MockExamAttempt).where(
            MockExamAttempt.mock_exam_id == mock_exam_id,
            MockExamAttempt.score_state == "streaming",
            MockExamAttempt.score_text == "",
        )
    ).all()
    timestamp = now()
    for attempt in rows:
        attempt.score_state = "error"
        attempt.score_text = "Scoring was interrupted."
        attempt.converted_score = 0
        attempt.max_score = MAX_SCORES.get(attempt.question_number, 3)
        attempt.updated_at = timestamp
