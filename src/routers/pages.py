from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..config import INDEX_PATH
from ..database import engine

router = APIRouter()


@router.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_PATH, headers={"Cache-Control": "no-store"})


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "database": engine.dialect.name}
