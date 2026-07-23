from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import User
from ..utils import now

_USERNAME_MAX = 32
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


def _sanitize_google_username(email: str) -> str:
    base = email.split("@")[0] if "@" in email else email
    base = re.sub(r"[^A-Za-z0-9_.-]", "", base)
    if not _USERNAME_RE.match(base):
        base = "g" + base
    if len(base) > _USERNAME_MAX:
        base = base[:_USERNAME_MAX]
    if not _USERNAME_RE.match(base):
        base = "google_user"
    return base


def _ensure_unique_username(conn: Session, username: str) -> str:
    candidate = username
    suffix = 1
    while conn.scalar(select(User).where(User.username == candidate)) is not None:
        trimmed = username[: _USERNAME_MAX - len(str(suffix))]
        candidate = f"{trimmed}{suffix}"
        suffix += 1
    return candidate


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


def find_user_by_google_id(
    conn: Session, google_id: str
) -> dict[str, Any] | None:
    user = conn.scalar(select(User).where(User.google_id == google_id))
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "google_id": user.google_id,
        "created_at": user.created_at,
    }


def find_user_by_email(
    conn: Session, email: str
) -> dict[str, Any] | None:
    user = conn.scalar(select(User).where(User.email == email))
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "google_id": user.google_id,
        "created_at": user.created_at,
    }


def insert_google_user(
    conn: Session, google_id: str, email: str, _username: str
) -> int:
    username = _ensure_unique_username(conn, _sanitize_google_username(email))
    user = User(
        username=username,
        password_hash="",
        google_id=google_id,
        email=email,
        created_at=now(),
    )
    conn.add(user)
    conn.flush()
    return user.id


def update_user_email(conn: Session, user_id: int, email: str) -> None:
    user = conn.get(User, user_id)
    if user is None:
        return
    user.email = email


def link_google_id(conn: Session, user_id: int, google_id: str) -> None:
    user = conn.get(User, user_id)
    if user is None:
        return
    user.google_id = google_id
