from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import Attempt
from ..utils import now


def insert_attempt(
    conn: Session,
    user_id: int,
    study4_test_id: int,
    question_number: int,
    answer: str,
    score_text: str,
    score_state: str,
    model: str,
) -> int:
    timestamp = now()
    attempt = Attempt(
        user_id=user_id,
        study4_test_id=study4_test_id,
        question_number=question_number,
        answer=answer,
        score_text=score_text,
        score_state=score_state,
        model=model,
        created_at=timestamp,
        updated_at=timestamp,
    )
    conn.add(attempt)
    conn.flush()
    return attempt.id


def mark_visible(
    conn: Session, attempt_id: int, score_text: str
) -> None:
    attempt = conn.get(Attempt, attempt_id)
    if attempt is None:
        return
    attempt.score_text = score_text
    attempt.score_state = "visible"
    attempt.updated_at = now()


def mark_error(
    conn: Session, attempt_id: int, detail: str
) -> None:
    attempt = conn.get(Attempt, attempt_id)
    if attempt is None:
        return
    attempt.score_state = "error"
    attempt.score_text = detail
    attempt.updated_at = now()


def list_attempts(
    conn: Session, user_id: int, study4_test_id: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        select(
            Attempt.id,
            Attempt.question_number,
            Attempt.answer,
            Attempt.score_text,
            Attempt.score_state,
            Attempt.model,
            Attempt.created_at,
        )
        .where(Attempt.user_id == user_id, Attempt.study4_test_id == study4_test_id)
        .order_by(Attempt.question_number, Attempt.id)
    ).all()
    return [dict(row._mapping) for row in rows]


def normalize_streaming(
    conn: Session, user_id: int
) -> None:
    rows = conn.scalars(
        select(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.score_state == "streaming",
            Attempt.score_text == "",
        )
    ).all()
    timestamp = now()
    for attempt in rows:
        attempt.score_state = "error"
        attempt.score_text = "Scoring was interrupted."
        attempt.updated_at = timestamp


def delete_attempts_for_question(
    conn: Session,
    user_id: int,
    study4_test_id: int,
    question_number: int,
) -> None:
    conn.execute(
        delete(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.study4_test_id == study4_test_id,
            Attempt.question_number == question_number,
        )
    )
