from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .config import SESSION_COOKIE_NAME, SESSION_SECRET_KEY


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        SessionMiddleware,
        secret_key=SESSION_SECRET_KEY,
        session_cookie=SESSION_COOKIE_NAME,
        same_site="lax",
    )
