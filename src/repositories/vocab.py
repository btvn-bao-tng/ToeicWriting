from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import VocabCategory, VocabTable, VocabTerm
from ..utils import now


def upsert_vocab_table(
    conn: Session,
    user_id: int,
    study4_test_id: int,
    question_number: int,
    topic: str,
    table_dict: dict[str, Any],
    model: str | None,
    attempt_id: int | None = None,
) -> int:
    timestamp = now()
    row = conn.scalar(
        select(VocabTable).where(
            VocabTable.user_id == user_id,
            VocabTable.study4_test_id == study4_test_id,
            VocabTable.question_number == question_number,
        )
    )
    if row is None:
        row = VocabTable(
            attempt_id=attempt_id,
            user_id=user_id,
            study4_test_id=study4_test_id,
            question_number=question_number,
            topic=topic,
            model=model,
            created_at=timestamp,
            updated_at=timestamp,
        )
        conn.add(row)
    else:
        row.attempt_id = attempt_id
        row.user_id = user_id
        row.study4_test_id = study4_test_id
        row.question_number = question_number
        row.topic = topic
        row.model = model
        row.updated_at = timestamp
    conn.flush()
    vocab_id = row.id

    conn.execute(delete(VocabTerm).where(VocabTerm.vocab_table_id == vocab_id))
    conn.execute(delete(VocabCategory).where(VocabCategory.vocab_table_id == vocab_id))

    for cat_idx, category in enumerate(table_dict.get("categories") or []):
        if not isinstance(category, dict):
            continue
        name = str(category.get("name") or "").strip()
        if not name:
            continue
        cat = VocabCategory(
            vocab_table_id=vocab_id,
            name=name,
            sort_order=cat_idx,
        )
        conn.add(cat)
        conn.flush()
        for term_idx, item in enumerate(category.get("items") or []):
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            if not term:
                continue
            image = item.get("image") if isinstance(item.get("image"), dict) else None
            conn.add(
                VocabTerm(
                    vocab_category_id=cat.id,
                    vocab_table_id=vocab_id,
                    term=term,
                    sort_order=term_idx,
                    image_url=(image.get("url") if image else None),
                    image_page_url=(image.get("page_url") if image else None),
                    image_photographer=(image.get("photographer") if image else None),
                    image_alt=(image.get("alt") if image else None),
                )
            )
    conn.flush()
    return vocab_id


def _assemble_payload(conn: Session, row: VocabTable) -> dict[str, Any]:
    cat_rows = conn.execute(
        select(VocabCategory)
        .where(VocabCategory.vocab_table_id == row.id)
        .order_by(VocabCategory.sort_order, VocabCategory.id)
    ).scalars().all()

    categories: list[dict[str, Any]] = []
    for cat in cat_rows:
        term_rows = conn.execute(
            select(VocabTerm)
            .where(VocabTerm.vocab_category_id == cat.id)
            .order_by(VocabTerm.sort_order, VocabTerm.id)
        ).scalars().all()
        items: list[dict[str, Any]] = []
        for t in term_rows:
            if t.image_url:
                image = {
                    "url": t.image_url,
                    "page_url": t.image_page_url,
                    "photographer": t.image_photographer or "",
                    "alt": t.image_alt,
                }
            else:
                image = None
            items.append({"term": t.term, "image": image})
        categories.append({"name": cat.name, "items": items})

    return {
        "id": row.id,
        "attempt_id": row.attempt_id,
        "study4_test_id": row.study4_test_id,
        "question_number": row.question_number,
        "topic": row.topic,
        "categories": categories,
        "model": row.model,
        "created_at": row.created_at,
    }


def find_vocab_table_by_question_owned(
    conn: Session, user_id: int, study4_test_id: int, question_number: int
) -> dict[str, Any] | None:
    row = conn.scalar(
        select(VocabTable).where(
            VocabTable.user_id == user_id,
            VocabTable.study4_test_id == study4_test_id,
            VocabTable.question_number == question_number,
        )
    )
    if row is None:
        return None
    return _assemble_payload(conn, row)


def find_vocab_table_by_attempt_owned(
    conn: Session, attempt_id: int, user_id: int
) -> dict[str, Any] | None:
    row = conn.scalar(
        select(VocabTable).where(
            VocabTable.attempt_id == attempt_id,
            VocabTable.user_id == user_id,
        )
    )
    if row is None:
        return None
    return _assemble_payload(conn, row)
