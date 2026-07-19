from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import Draft
from ..utils import now


def upsert_draft(
    conn: Session,
    user_id: int,
    study4_test_id: int,
    question_number: int,
    body: str,
) -> None:
    timestamp = now()
    draft = conn.scalar(
        select(Draft).where(
            Draft.user_id == user_id,
            Draft.study4_test_id == study4_test_id,
            Draft.question_number == question_number,
        )
    )
    if draft is None:
        conn.add(
            Draft(
                user_id=user_id,
                study4_test_id=study4_test_id,
                question_number=question_number,
                body=body,
                updated_at=timestamp,
            )
        )
        return
    draft.body = body
    draft.updated_at = timestamp


def list_drafts(
    conn: Session, user_id: int, study4_test_id: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        select(Draft.question_number, Draft.body).where(
            Draft.user_id == user_id,
            Draft.study4_test_id == study4_test_id,
        )
    ).all()
    return [dict(row._mapping) for row in rows]


def delete_draft(
    conn: Session,
    user_id: int,
    study4_test_id: int,
    question_number: int,
) -> None:
    draft = conn.scalar(
        select(Draft).where(
            Draft.user_id == user_id,
            Draft.study4_test_id == study4_test_id,
            Draft.question_number == question_number,
        )
    )
    if draft is not None:
        conn.delete(draft)
