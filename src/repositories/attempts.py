from __future__ import annotations

import sqlite3
from typing import Any

from ..database import row_to_dict
from ..utils import now


def insert_attempt(
    conn: sqlite3.Connection,
    user_id: int,
    study4_test_id: int,
    question_number: int,
    answer: str,
    score_text: str,
    score_state: str,
    model: str,
) -> int:
    timestamp = now()
    cursor = conn.execute(
        """
        INSERT INTO attempts (
            user_id, study4_test_id, question_number, answer,
            score_text, score_state, model, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            study4_test_id,
            question_number,
            answer,
            score_text,
            score_state,
            model,
            timestamp,
            timestamp,
        ),
    )
    return cursor.lastrowid


def mark_visible(
    conn: sqlite3.Connection, attempt_id: int, score_text: str
) -> None:
    conn.execute(
        """
        UPDATE attempts
        SET score_text = ?, score_state = 'visible', updated_at = ?
        WHERE id = ?
        """,
        (score_text, now(), attempt_id),
    )


def mark_error(
    conn: sqlite3.Connection, attempt_id: int, detail: str
) -> None:
    conn.execute(
        """
        UPDATE attempts
        SET score_state = 'error',
            score_text = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (detail, now(), attempt_id),
    )


def list_attempts(
    conn: sqlite3.Connection, user_id: int, study4_test_id: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, question_number, answer, score_text, score_state, model, created_at
        FROM attempts
        WHERE user_id = ? AND study4_test_id = ?
        ORDER BY question_number, id
        """,
        (user_id, study4_test_id),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def normalize_streaming(
    conn: sqlite3.Connection, user_id: int
) -> None:
    conn.execute(
        """
        UPDATE attempts
        SET score_state = 'error',
            score_text = COALESCE(NULLIF(score_text, ''), 'Scoring was interrupted.'),
            updated_at = ?
        WHERE user_id = ?
            AND score_state = 'streaming'
            AND score_text = ''
        """,
        (now(), user_id),
    )


def delete_attempts_for_question(
    conn: sqlite3.Connection,
    user_id: int,
    study4_test_id: int,
    question_number: int,
) -> None:
    conn.execute(
        "DELETE FROM attempts WHERE user_id = ? AND study4_test_id = ? AND question_number = ?",
        (user_id, study4_test_id, question_number),
    )
