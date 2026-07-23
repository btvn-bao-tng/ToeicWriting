from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .config import STATIC_PATH
from .database import engine, init_db
from .middleware import register_middleware
from .routers import auth as auth_router
from .routers import mock_exams as mock_exams_router
from .routers import pages as pages_router
from .routers import progress as progress_router
from .routers import revision as revision_router
from .routers import score as score_router
from .routers import tests as tests_router
from .routers import tts as tts_router
from .routers import vocab as vocab_router

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="TOEIC SW Writing Browser")
register_middleware(app)
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

app.include_router(pages_router.router)
app.include_router(tests_router.router)
app.include_router(auth_router.router)
app.include_router(progress_router.router)
app.include_router(score_router.router)
app.include_router(mock_exams_router.router)
app.include_router(vocab_router.router)
app.include_router(tts_router.router)
app.include_router(revision_router.router)


@app.on_event("startup")
async def _startup() -> None:
    logger.info(
        "Starting %s with %s database at %s",
        app.title,
        engine.dialect.name,
        engine.url.render_as_string(hide_password=True),
    )
    await run_in_threadpool(init_db)
    logger.info("Database schema is ready")
