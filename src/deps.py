from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from .database import db
from .repositories import users as users_repo


def current_user(request: Request) -> dict[str, Any] | None:
    uid = request.session.get("uid")
    if not uid:
        return None
    with db() as conn:
        return users_repo.find_user_by_id(conn, uid)


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
