from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import db_session, require_user_with_db
from ..repositories import attempts as attempts_repo
from ..repositories import drafts as drafts_repo
from ..schemas import DraftRequest

router = APIRouter()


@router.get("/api/progress")
async def get_progress(
    study4_test_id: int,
    user: dict[str, Any] = Depends(require_user_with_db),
    conn: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    await attempts_repo.normalize_streaming(conn, user["id"])
    draft_rows = await drafts_repo.list_drafts(conn, user["id"], study4_test_id)
    attempt_rows = await attempts_repo.list_attempts(conn, user["id"], study4_test_id)
    return {
        "drafts": [
            {"question_number": r["question_number"], "body": r["body"]}
            for r in draft_rows
        ],
        "attempts": attempt_rows,
    }


@router.put("/api/draft")
async def put_draft(
    body: DraftRequest,
    user: dict[str, Any] = Depends(require_user_with_db),
    conn: AsyncSession = Depends(db_session),
) -> dict[str, bool]:
    await drafts_repo.upsert_draft(
        conn,
        user["id"],
        body.study4_test_id,
        body.question_number,
        body.body,
    )
    return {"ok": True}


@router.delete("/api/progress")
async def delete_progress(
    study4_test_id: int,
    question_number: int,
    user: dict[str, Any] = Depends(require_user_with_db),
    conn: AsyncSession = Depends(db_session),
) -> dict[str, bool]:
    await drafts_repo.delete_draft(conn, user["id"], study4_test_id, question_number)
    await attempts_repo.delete_attempts_for_question(
        conn,
        user["id"],
        study4_test_id,
        question_number,
    )
    return {"ok": True}
