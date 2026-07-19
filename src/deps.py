from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Any

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import db, get_db
from .repositories import users as users_repo


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def remember_user(request: Request, user: dict[str, Any]) -> None:
    request.session["uid"] = user["id"]
    request.session["username"] = user["username"]


def session_user(request: Request) -> dict[str, Any] | None:
    uid = request.session.get("uid")
    username = request.session.get("username")
    if not uid or not username:
        return None
    return {"id": uid, "username": username}


@lru_cache(maxsize=1024)
def cached_user_identity(user_id: int) -> tuple[int, str] | None:
    with db() as conn:
        user = users_repo.find_user_by_id(conn, user_id)
    if not user:
        return None
    return user["id"], user["username"]


def clear_user_cache() -> None:
    cached_user_identity.cache_clear()


def find_current_user(request: Request, conn: Session) -> dict[str, Any] | None:
    user: dict[str, Any] | None = session_user(request)
    if user:
        return user

    uid = request.session.get("uid")
    if not uid:
        return None
    try:
        user_id = int(uid)
    except (TypeError, ValueError):
        return None

    identity = cached_user_identity(user_id)
    if not identity:
        return None

    user = {"id": identity[0], "username": identity[1]}
    remember_user(request, user)
    return user


def current_user(request: Request) -> dict[str, Any] | None:
    with db() as conn:
        return find_current_user(request, conn)


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def optional_user(request: Request) -> dict[str, Any] | None:
    return current_user(request)


def require_user_with_db(
    request: Request,
    conn: Session = Depends(db_session),
) -> dict[str, Any]:
    user = find_current_user(request, conn)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
