from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Draft
from ..utils import now


async def upsert_draft(
    conn: AsyncSession,
    user_id: int,
    study4_test_id: int,
    question_number: int,
    body: str,
) -> None:
    timestamp = now()
    draft = await conn.scalar(
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


async def list_drafts(
    conn: AsyncSession, user_id: int, study4_test_id: int
) -> list[dict[str, Any]]:
    rows = (
        await conn.execute(
            select(Draft.question_number, Draft.body).where(
                Draft.user_id == user_id,
                Draft.study4_test_id == study4_test_id,
            )
        )
    ).all()
    return [dict(row._mapping) for row in rows]


async def delete_draft(
    conn: AsyncSession,
    user_id: int,
    study4_test_id: int,
    question_number: int,
) -> None:
    draft = await conn.scalar(
        select(Draft).where(
            Draft.user_id == user_id,
            Draft.study4_test_id == study4_test_id,
            Draft.question_number == question_number,
        )
    )
    if draft is not None:
        await conn.delete(draft)
