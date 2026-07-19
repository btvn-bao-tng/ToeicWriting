from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import ToeicWritingPart, ToeicWritingQuestion, ToeicWritingTest


def list_tests(conn: Session) -> list[dict[str, Any]]:
    rows = conn.execute(
        select(
            ToeicWritingTest.study4_test_id,
            ToeicWritingTest.test_number,
            ToeicWritingTest.title,
            ToeicWritingTest.url,
            ToeicWritingTest.duration_minutes,
            ToeicWritingTest.part_count,
            ToeicWritingTest.question_count,
            ToeicWritingTest.practice_count,
            ToeicWritingTest.access_status,
            func.count(ToeicWritingQuestion.id).label("crawled_question_count"),
        )
        .outerjoin(
            ToeicWritingQuestion,
            ToeicWritingQuestion.study4_test_id == ToeicWritingTest.study4_test_id,
        )
        .group_by(
            ToeicWritingTest.study4_test_id,
            ToeicWritingTest.test_number,
            ToeicWritingTest.title,
            ToeicWritingTest.url,
            ToeicWritingTest.duration_minutes,
            ToeicWritingTest.part_count,
            ToeicWritingTest.question_count,
            ToeicWritingTest.practice_count,
            ToeicWritingTest.access_status,
        )
        .order_by(ToeicWritingTest.test_number.desc())
    ).all()
    return [dict(row._mapping) for row in rows]


def find_test(conn: Session, study4_test_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        select(
            ToeicWritingTest.study4_test_id,
            ToeicWritingTest.test_number,
            ToeicWritingTest.title,
            ToeicWritingTest.slug,
            ToeicWritingTest.url,
            ToeicWritingTest.duration_minutes,
            ToeicWritingTest.part_count,
            ToeicWritingTest.question_count,
            ToeicWritingTest.practice_count,
            ToeicWritingTest.access_status,
        ).where(ToeicWritingTest.study4_test_id == study4_test_id)
    ).first()
    return dict(row._mapping) if row else None


def list_parts(conn: Session, study4_test_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        select(
            ToeicWritingPart.study4_part_id,
            ToeicWritingPart.sort_order,
            ToeicWritingPart.label,
            ToeicWritingPart.question_count,
        )
        .where(ToeicWritingPart.study4_test_id == study4_test_id)
        .order_by(ToeicWritingPart.sort_order)
    ).all()
    return [dict(row._mapping) for row in rows]


def list_questions(conn: Session, study4_test_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        select(
            ToeicWritingQuestion.id,
            ToeicWritingQuestion.study4_test_id,
            ToeicWritingQuestion.study4_part_id,
            ToeicWritingQuestion.study4_question_id,
            ToeicWritingQuestion.question_number,
            ToeicWritingQuestion.prompt_html,
            ToeicWritingQuestion.prompt_text,
            ToeicWritingQuestion.asset_urls,
        )
        .where(ToeicWritingQuestion.study4_test_id == study4_test_id)
        .order_by(ToeicWritingQuestion.question_number)
    ).all()
    return [dict(row._mapping) for row in rows]


def find_question(
    conn: Session, study4_test_id: int, question_number: int
) -> dict[str, Any] | None:
    row = conn.execute(
        select(
            ToeicWritingTest.title,
            ToeicWritingQuestion.question_number,
            ToeicWritingQuestion.prompt_text,
            ToeicWritingQuestion.prompt_html,
            ToeicWritingQuestion.asset_urls,
            ToeicWritingPart.sort_order.label("part_order"),
            ToeicWritingPart.label.label("part_label"),
        )
        .join(
            ToeicWritingTest,
            ToeicWritingTest.study4_test_id == ToeicWritingQuestion.study4_test_id,
        )
        .outerjoin(
            ToeicWritingPart,
            ToeicWritingPart.study4_part_id == ToeicWritingQuestion.study4_part_id,
        )
        .where(
            ToeicWritingQuestion.study4_test_id == study4_test_id,
            ToeicWritingQuestion.question_number == question_number,
        )
    ).first()
    return dict(row._mapping) if row else None
