from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..config import AI_MODEL, PEXELS_API_KEY
from ..database import db
from ..deps import require_user
from ..repositories import attempts as attempts_repo
from ..repositories import vocab as vocab_repo
from ..schemas import VocabDetailRequest, VocabRequest
from ..services import content as content_service
from ..services import vocab as vocab_service

router = APIRouter()


@router.post("/api/vocab")
async def generate_vocab(
    request: VocabRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    if not PEXELS_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="PEXELS_API_KEY is not set. Configure it to generate vocab images.",
        )

    question_row = await content_service.find_question(
        request.study4_test_id, request.question_number
    )
    if question_row is None:
        raise HTTPException(status_code=404, detail="Question not found")

    answer = ""
    score_text = ""
    attempt_id = request.attempt_id
    if attempt_id is not None:
        async with db() as conn:
            attempt = await attempts_repo.find_attempt(conn, attempt_id)
        if attempt is None:
            raise HTTPException(status_code=404, detail="Attempt not found")
        if attempt["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Attempt not found")
        if (
            attempt["study4_test_id"] != request.study4_test_id
            or attempt["question_number"] != request.question_number
        ):
            raise HTTPException(
                status_code=400, detail="Attempt does not match the given question"
            )
        answer = attempt.get("answer") or ""
        score_text = attempt.get("score_text") or ""

    table = await vocab_service.generate_table(question_row, answer, score_text)

    async with db() as conn:
        await vocab_repo.upsert_vocab_table(
            conn,
            user["id"],
            request.study4_test_id,
            request.question_number,
            table["topic"],
            table,
            AI_MODEL,
            attempt_id,
        )
        payload = await vocab_repo.find_vocab_table_by_question_owned(
            conn, user["id"], request.study4_test_id, request.question_number
        )
        await conn.commit()

    return payload


@router.get("/api/vocab")
async def get_vocab(
    study4_test_id: int,
    question_number: int,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    async with db() as conn:
        payload = await vocab_repo.find_vocab_table_by_question_owned(
            conn, user["id"], study4_test_id, question_number
        )
    if payload is None:
        raise HTTPException(status_code=404, detail="No saved vocab table for this question")
    return payload


@router.post("/api/vocab/detail")
async def vocab_detail(
    request: VocabDetailRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    if not PEXELS_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="PEXELS_API_KEY is not set. Configure it to generate vocab images.",
        )
    return await vocab_service.generate_term_detail(
        request.term,
        request.topic,
        request.main_image_url,
        request.question_prompt,
    )
