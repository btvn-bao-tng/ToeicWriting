from __future__ import annotations

import sqlite3
from typing import Any

from ..database import row_to_dict
from ..utils import now


def insert_user(
    conn: sqlite3.Connection, username: str, password_hash: str
) -> int:
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, password_hash, now()),
    )
    return cursor.lastrowid


def find_user_by_username(
    conn: sqlite3.Connection, username: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return row_to_dict(row) if row else None


def find_user_by_id(
    conn: sqlite3.Connection, user_id: int
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, username, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return row_to_dict(row) if row else None
