from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..database import db
from ..deps import require_user
from ..repositories import attempts as attempts_repo
from ..repositories import drafts as drafts_repo
from ..schemas import DraftRequest

router = APIRouter()


@router.get("/api/progress")
def get_progress(
    study4_test_id: int,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    with db() as conn:
        attempts_repo.normalize_streaming(conn, user["id"])
        draft_rows = drafts_repo.list_drafts(conn, user["id"], study4_test_id)
        attempt_rows = attempts_repo.list_attempts(conn, user["id"], study4_test_id)

    return {
        "drafts": [
            {"question_number": r["question_number"], "body": r["body"]}
            for r in draft_rows
        ],
        "attempts": attempt_rows,
    }


@router.put("/api/draft")
def put_draft(
    body: DraftRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, bool]:
    with db() as conn:
        drafts_repo.upsert_draft(
            conn, user["id"], body.study4_test_id, body.question_number, body.body
        )
        conn.commit()
    return {"ok": True}


@router.delete("/api/progress")
def delete_progress(
    study4_test_id: int,
    question_number: int,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, bool]:
    with db() as conn:
        drafts_repo.delete_draft(conn, user["id"], study4_test_id, question_number)
        attempts_repo.delete_attempts_for_question(
            conn, user["id"], study4_test_id, question_number
        )
        conn.commit()
    return {"ok": True}
