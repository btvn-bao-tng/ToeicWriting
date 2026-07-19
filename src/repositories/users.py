from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import User
from ..utils import now


def insert_user(
    conn: Session, username: str, password_hash: str
) -> int:
    user = User(username=username, password_hash=password_hash, created_at=now())
    conn.add(user)
    conn.flush()
    return user.id


def find_user_by_username(
    conn: Session, username: str
) -> dict[str, Any] | None:
    user = conn.scalar(select(User).where(User.username == username))
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "password_hash": user.password_hash,
        "created_at": user.created_at,
    }


def find_user_by_id(
    conn: Session, user_id: int
) -> dict[str, Any] | None:
    user = conn.get(User, user_id)
    if user is None:
        return None
    return {"id": user.id, "username": user.username, "created_at": user.created_at}
