from __future__ import annotations

import sqlite3

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import DB_PATH, STATIC_PATH
from .database import ensure_user_schema
from .middleware import register_middleware
from .routers import auth as auth_router
from .routers import pages as pages_router
from .routers import progress as progress_router
from .routers import score as score_router
from .routers import tests as tests_router

app = FastAPI(title="TOEIC SW Writing Browser")
register_middleware(app)
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

app.include_router(pages_router.router)
app.include_router(tests_router.router)
app.include_router(auth_router.router)
app.include_router(progress_router.router)
app.include_router(score_router.router)


@app.on_event("startup")
def _startup() -> None:
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        ensure_user_schema(conn)
