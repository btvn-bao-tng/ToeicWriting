from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..database import db
from ..deps import require_user
from ..repositories import revision as revision_repo
from ..schemas import RevisionItemRequest, ReviewStateRequest

router = APIRouter()


@router.get("/api/revision")
async def list_revision(
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    async with db() as conn:
        items = await revision_repo.list_revision(conn, user["id"])
    return {"items": items}


@router.post("/api/revision")
async def add_revision(
    request: RevisionItemRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    data = {
        "term": request.term,
        "topic": request.topic,
        "image": request.image,
        "part_of_speech": request.part_of_speech,
        "ipa": request.ipa,
        "meaning": request.meaning,
        "example": request.example,
        "vietnamese_meaning": request.vietnamese_meaning,
        "synonyms": request.synonyms,
    }

    async with db() as conn:
        payload = await revision_repo.upsert_revision(conn, user["id"], data)
        await conn.commit()
    return payload


@router.delete("/api/revision/{item_id}")
async def delete_revision(
    item_id: int,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    async with db() as conn:
        ok = await revision_repo.delete_revision(conn, user["id"], item_id)
        if ok:
            await conn.commit()

    if not ok:
        raise HTTPException(status_code=404, detail="Revision item not found")
    return {"ok": True}


@router.post("/api/revision/{item_id}/review")
async def set_review_state(
    item_id: int,
    request: ReviewStateRequest,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    async with db() as conn:
        payload = await revision_repo.mark_reviewed(
            conn,
            user["id"],
            item_id,
            request.reviewed,
        )

    if payload is None:
        raise HTTPException(status_code=404, detail="Revision item not found")
    return payload
