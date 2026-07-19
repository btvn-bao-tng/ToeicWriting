from __future__ import annotations

import sqlite3
from typing import Any

from ..database import row_to_dict
from ..utils import now


def upsert_draft(
    conn: sqlite3.Connection,
    user_id: int,
    study4_test_id: int,
    question_number: int,
    body: str,
) -> None:
    conn.execute(
        """
        INSERT INTO drafts (user_id, study4_test_id, question_number, body, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, study4_test_id, question_number) DO UPDATE SET
            body = excluded.body,
            updated_at = excluded.updated_at
        """,
        (user_id, study4_test_id, question_number, body, now()),
    )


def list_drafts(
    conn: sqlite3.Connection, user_id: int, study4_test_id: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT question_number, body
        FROM drafts
        WHERE user_id = ? AND study4_test_id = ?
        """,
        (user_id, study4_test_id),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def delete_draft(
    conn: sqlite3.Connection,
    user_id: int,
    study4_test_id: int,
    question_number: int,
) -> None:
    conn.execute(
        "DELETE FROM drafts WHERE user_id = ? AND study4_test_id = ? AND question_number = ?",
        (user_id, study4_test_id, question_number),
    )
