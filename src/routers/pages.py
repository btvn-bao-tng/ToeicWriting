from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..config import DB_PATH, INDEX_PATH

router = APIRouter()


@router.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_PATH, headers={"Cache-Control": "no-store"})


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": str(DB_PATH)}
