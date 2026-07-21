from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..deps import require_user
from ..services import tts as tts_service

router = APIRouter()


@router.get("/api/tts")
async def text_to_speech(
    text: str = Query(..., min_length=1, max_length=tts_service.MAX_TEXT_LENGTH),
    accent: str = Query(tts_service.DEFAULT_ACCENT, pattern="^(us|uk)$"),
    user: dict[str, Any] = Depends(require_user),
) -> Response:
    try:
        audio = await tts_service.synthesize_async(text, accent)
    except Exception as error:  # noqa: BLE001 - surface a clean 503 to the client
        raise HTTPException(
            status_code=503,
            detail=f"Text-to-speech is unavailable: {error}",
        ) from error
    return Response(content=audio, media_type="audio/mpeg")
