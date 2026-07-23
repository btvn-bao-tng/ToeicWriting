from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .database import db
from .repositories import users as users_repo


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with db() as session:
        yield session


def remember_user(request: Request, user: dict[str, Any]) -> None:
    request.session["uid"] = user["id"]
    request.session["username"] = user["username"]


def session_user(request: Request) -> dict[str, Any] | None:
    uid = request.session.get("uid")
    username = request.session.get("username")
    if not uid or not username:
        return None
    return {"id": uid, "username": username}


_user_identity_cache: dict[int, tuple[int, str] | None] = {}


async def cached_user_identity(user_id: int) -> tuple[int, str] | None:
    if user_id in _user_identity_cache:
        return _user_identity_cache[user_id]
    async with db() as conn:
        user = await users_repo.find_user_by_id(conn, user_id)
    identity = (user["id"], user["username"]) if user else None
    _user_identity_cache[user_id] = identity
    return identity


def clear_user_cache() -> None:
    _user_identity_cache.clear()


async def find_current_user(request: Request) -> dict[str, Any] | None:
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

    identity = await cached_user_identity(user_id)
    if not identity:
        return None

    user = {"id": identity[0], "username": identity[1]}
    remember_user(request, user)
    return user


async def current_user(request: Request) -> dict[str, Any] | None:
    return await find_current_user(request)


async def require_user(request: Request) -> dict[str, Any]:
    user = await find_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def optional_user(request: Request) -> dict[str, Any] | None:
    return await find_current_user(request)


async def require_user_with_db(
    request: Request,
    conn: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    user = await find_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
