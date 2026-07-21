from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from ..deps import optional_user
from ..services import content as content_service

router = APIRouter()


@router.get("/api/tests")
async def list_tests(
    user: dict[str, Any] | None = Depends(optional_user),
) -> list[dict[str, Any]]:
    return await run_in_threadpool(content_service.list_tests)


@router.get("/api/tests/{study4_test_id}")
async def get_test(
    study4_test_id: int,
    user: dict[str, Any] | None = Depends(optional_user),
) -> dict[str, Any]:
    payload = await run_in_threadpool(content_service.get_test_payload, study4_test_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Test not found")
    return payload
