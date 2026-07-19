from __future__ import annotations

import sqlite3
from typing import Any

from ..database import row_to_dict


def list_tests(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            t.study4_test_id,
            t.test_number,
            t.title,
            t.url,
            t.duration_minutes,
            t.part_count,
            t.question_count,
            t.practice_count,
            t.access_status,
            COUNT(q.id) AS crawled_question_count
        FROM toeic_sw_writing_tests t
        LEFT JOIN toeic_sw_writing_questions q
            ON q.study4_test_id = t.study4_test_id
        GROUP BY t.study4_test_id
        ORDER BY t.test_number DESC
        """
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def find_test(conn: sqlite3.Connection, study4_test_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT
            study4_test_id,
            test_number,
            title,
            slug,
            url,
            duration_minutes,
            part_count,
            question_count,
            practice_count,
            access_status
        FROM toeic_sw_writing_tests
        WHERE study4_test_id = ?
        """,
        (study4_test_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def list_parts(conn: sqlite3.Connection, study4_test_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT study4_part_id, sort_order, label, question_count
        FROM toeic_sw_writing_parts
        WHERE study4_test_id = ?
        ORDER BY sort_order
        """,
        (study4_test_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def list_questions(conn: sqlite3.Connection, study4_test_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            id,
            study4_test_id,
            study4_part_id,
            study4_question_id,
            question_number,
            prompt_html,
            prompt_text,
            asset_urls
        FROM toeic_sw_writing_questions
        WHERE study4_test_id = ?
        ORDER BY question_number
        """,
        (study4_test_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def find_question(
    conn: sqlite3.Connection, study4_test_id: int, question_number: int
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT
            t.title,
            q.question_number,
            q.prompt_text,
            q.prompt_html,
            q.asset_urls,
            p.sort_order AS part_order,
            p.label AS part_label
        FROM toeic_sw_writing_questions q
        JOIN toeic_sw_writing_tests t
            ON t.study4_test_id = q.study4_test_id
        LEFT JOIN toeic_sw_writing_parts p
            ON p.study4_part_id = q.study4_part_id
        WHERE q.study4_test_id = ?
            AND q.question_number = ?
        """,
        (study4_test_id, question_number),
    ).fetchone()
    return row_to_dict(row) if row else None
