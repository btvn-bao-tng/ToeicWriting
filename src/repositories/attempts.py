from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Attempt
from ..utils import now


async def find_attempt(conn: AsyncSession, attempt_id: int) -> dict[str, Any] | None:
    attempt = await conn.get(Attempt, attempt_id)
    if attempt is None:
        return None
    return {
        "id": attempt.id,
        "user_id": attempt.user_id,
        "study4_test_id": attempt.study4_test_id,
        "question_number": attempt.question_number,
        "answer": attempt.answer,
        "score_text": attempt.score_text,
        "score_state": attempt.score_state,
        "model": attempt.model,
        "created_at": attempt.created_at,
    }


async def insert_attempt(
    conn: AsyncSession,
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
    await conn.flush()
    return attempt.id


async def mark_visible(
    conn: AsyncSession, attempt_id: int, score_text: str
) -> None:
    attempt = await conn.get(Attempt, attempt_id)
    if attempt is None:
        return
    attempt.score_text = score_text
    attempt.score_state = "visible"
    attempt.updated_at = now()


async def mark_error(
    conn: AsyncSession, attempt_id: int, detail: str
) -> None:
    attempt = await conn.get(Attempt, attempt_id)
    if attempt is None:
        return
    attempt.score_state = "error"
    attempt.score_text = detail
    attempt.updated_at = now()


async def list_attempts(
    conn: AsyncSession, user_id: int, study4_test_id: int
) -> list[dict[str, Any]]:
    latest_ids = (
        select(func.max(Attempt.id).label("id"))
        .where(Attempt.user_id == user_id, Attempt.study4_test_id == study4_test_id)
        .group_by(Attempt.question_number)
    ).subquery()

    rows = (
        await conn.execute(
            select(
                Attempt.id,
                Attempt.question_number,
                Attempt.answer,
                Attempt.score_text,
                Attempt.score_state,
                Attempt.model,
                Attempt.created_at,
            )
            .join(latest_ids, Attempt.id == latest_ids.c.id)
            .order_by(Attempt.question_number)
        )
    ).all()
    return [dict(row._mapping) for row in rows]


async def normalize_streaming(
    conn: AsyncSession, user_id: int
) -> None:
    rows = (
        await conn.scalars(
            select(Attempt).where(
                Attempt.user_id == user_id,
                Attempt.score_state == "streaming",
                Attempt.score_text == "",
            )
        )
    ).all()
    timestamp = now()
    for attempt in rows:
        attempt.score_state = "error"
        attempt.score_text = "Scoring was interrupted."
        attempt.updated_at = timestamp


async def delete_attempts_for_question(
    conn: AsyncSession,
    user_id: int,
    study4_test_id: int,
    question_number: int,
) -> None:
    await conn.execute(
        delete(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.study4_test_id == study4_test_id,
            Attempt.question_number == question_number,
        )
    )
