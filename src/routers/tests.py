from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..database import db
from ..deps import require_user
from ..repositories import tests as tests_repo
from ..utils import decode_assets

router = APIRouter()


@router.get("/api/tests")
def list_tests(user: dict[str, Any] = Depends(require_user)) -> list[dict[str, Any]]:
    with db() as conn:
        return tests_repo.list_tests(conn)


@router.get("/api/tests/{study4_test_id}")
def get_test(
    study4_test_id: int,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    with db() as conn:
        test = tests_repo.find_test(conn, study4_test_id)
        if test is None:
            raise HTTPException(status_code=404, detail="Test not found")

        parts = tests_repo.list_parts(conn, study4_test_id)
        questions = tests_repo.list_questions(conn, study4_test_id)

    for item in questions:
        item["asset_urls"] = decode_assets(item.get("asset_urls"))

    return {"test": test, "parts": parts, "questions": questions}
