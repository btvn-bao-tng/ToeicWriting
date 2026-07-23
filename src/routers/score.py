from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..config import AI_API_KEY, AI_MODEL
from ..database import db
from ..deps import require_user
from ..repositories import attempts as attempts_repo
from ..schemas import ScoreRequest, ScoreResponse
from ..services import ai as ai_service
from ..services import scoring as scoring_service

router = APIRouter()


@router.post("/api/score", response_model=ScoreResponse)
async def score_answer(
    request: ScoreRequest,
    user: dict[str, Any] = Depends(require_user),
) -> ScoreResponse:
    part_order, question_number, system_prompt, user_prompt = await scoring_service.score_context(
        request
    )
    score_text = await ai_service.ai_chat(system_prompt, user_prompt)

    async with db() as conn:
        attempt_id = await attempts_repo.insert_attempt(
            conn,
            user["id"],
            request.study4_test_id,
            request.question_number,
            request.answer,
            score_text,
            "visible",
            AI_MODEL,
        )
        await conn.commit()

    return ScoreResponse(
        score_text=score_text,
        model=AI_MODEL,
        part=part_order,
        question_number=question_number,
        attempt_id=attempt_id,
    )


@router.post("/api/score/stream")
async def score_answer_stream(
    request: ScoreRequest,
    user: dict[str, Any] = Depends(require_user),
) -> StreamingResponse:
    if not AI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AI_API_KEY is not set. Start the server with AI_API_KEY in the environment.",
        )

    _part_order, _question_number, system_prompt, user_prompt = await scoring_service.score_context(
        request
    )

    async def stream_and_persist():
        async with db() as conn:
            attempt_id = await attempts_repo.insert_attempt(
                conn,
                user["id"],
                request.study4_test_id,
                request.question_number,
                request.answer,
                "",
                "streaming",
                AI_MODEL,
            )
            await conn.commit()

        yield ai_service.sse_event("start", {"attempt_id": attempt_id})

        full_text = ""
        async for event in ai_service.ai_chat_stream(system_prompt, user_prompt):
            if "event: done" in event:
                continue
            if "event: error" in event:
                try:
                    data_line = event.split("data:", 1)[1].strip()
                    detail = json.loads(data_line).get("detail", "Scoring failed.")
                except (IndexError, json.JSONDecodeError):
                    detail = "Scoring failed."
                async with db() as conn:
                    await attempts_repo.mark_error(conn, attempt_id, detail)
                    await conn.commit()
                yield ai_service.sse_event("error", {"detail": detail, "attempt_id": attempt_id})
                return
            if "event: delta" in event:
                try:
                    data_line = event.split("data:", 1)[1].strip()
                    full_text += json.loads(data_line).get("content", "")
                except (IndexError, json.JSONDecodeError):
                    pass
            yield event

        async with db() as conn:
            await attempts_repo.mark_visible(conn, attempt_id, full_text)
            await conn.commit()
        yield ai_service.sse_event("done", {"attempt_id": attempt_id})

    return StreamingResponse(
        stream_and_persist(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
