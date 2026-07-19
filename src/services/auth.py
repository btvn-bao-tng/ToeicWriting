from __future__ import annotations

from typing import Any

import bcrypt
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from ..config import ALLOW_SIGNUP, USERNAME_RE
from ..database import db
from ..repositories import users as users_repo


def register_user(username: str, password: str) -> dict[str, Any]:
    if not ALLOW_SIGNUP:
        raise HTTPException(status_code=403, detail="Sign-up is disabled on this server.")
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-32 chars (A-Z, a-z, 0-9, ., _, -).",
        )

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    with db() as conn:
        try:
            uid = users_repo.insert_user(conn, username, password_hash)
            conn.commit()
        except IntegrityError:
            conn.rollback()
            raise HTTPException(status_code=409, detail="That username is already taken.")

    return {"id": uid, "username": username}


def authenticate_user(username: str, password: str) -> dict[str, Any]:
    with db() as conn:
        user = users_repo.find_user_by_username(conn, username)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    try:
        ok = bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("ascii"))
    except ValueError:
        ok = False
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    return {"id": user["id"], "username": user["username"]}
