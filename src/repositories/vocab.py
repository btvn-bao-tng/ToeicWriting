from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import VocabCategory, VocabTable, VocabTerm
from ..utils import now


async def upsert_vocab_table(
    conn: AsyncSession,
    user_id: int,
    study4_test_id: int,
    question_number: int,
    topic: str,
    table_dict: dict[str, Any],
    model: str | None,
    attempt_id: int | None = None,
) -> int:
    timestamp = now()
    row = await conn.scalar(
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
    await conn.flush()
    vocab_id = row.id

    await conn.execute(delete(VocabTerm).where(VocabTerm.vocab_table_id == vocab_id))
    await conn.execute(
        delete(VocabCategory).where(VocabCategory.vocab_table_id == vocab_id)
    )

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
        await conn.flush()
        for term_idx, item in enumerate(category.get("items") or []):
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            if not term:
                continue
            image = item.get("image") if isinstance(item.get("image"), dict) else None
            raw_synonyms = item.get("synonyms")
            if not isinstance(raw_synonyms, list):
                raw_synonyms = []
            synonyms_list = [str(s).strip() for s in raw_synonyms if str(s).strip()]
            synonyms_json = json.dumps(synonyms_list, ensure_ascii=False) if synonyms_list else None
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
                    part_of_speech=(str(item.get("part_of_speech") or "").strip() or None),
                    ipa=(str(item.get("ipa") or "").strip() or None),
                    meaning=(str(item.get("meaning") or "").strip() or None),
                    example=(str(item.get("example") or "").strip() or None),
                    vietnamese_meaning=(str(item.get("vietnamese_meaning") or "").strip() or None),
                    synonyms=synonyms_json,
                )
            )
    await conn.flush()
    return vocab_id


async def _assemble_payload(conn: AsyncSession, row: VocabTable) -> dict[str, Any]:
    rows = (
        await conn.execute(
            select(
                VocabCategory.id.label("cat_id"),
                VocabCategory.name.label("cat_name"),
                VocabCategory.sort_order.label("cat_sort"),
                VocabTerm.id.label("term_id"),
                VocabTerm.term,
                VocabTerm.sort_order.label("term_sort"),
                VocabTerm.image_url,
                VocabTerm.image_page_url,
                VocabTerm.image_photographer,
                VocabTerm.image_alt,
                VocabTerm.part_of_speech,
                VocabTerm.ipa,
                VocabTerm.meaning,
                VocabTerm.example,
                VocabTerm.vietnamese_meaning,
                VocabTerm.synonyms,
            )
            .outerjoin(
                VocabTerm,
                VocabTerm.vocab_category_id == VocabCategory.id,
            )
            .where(VocabCategory.vocab_table_id == row.id)
            .order_by(
                VocabCategory.sort_order,
                VocabCategory.id,
                VocabTerm.sort_order,
                VocabTerm.id,
            )
        )
    ).all()

    categories: list[dict[str, Any]] = []
    current_cat: dict[str, Any] | None = None
    for r in rows:
        m = r._mapping
        if current_cat is None or m["cat_id"] != current_cat["cat_id"]:
            current_cat = {"cat_id": m["cat_id"], "name": m["cat_name"], "items": []}
            categories.append(current_cat)
        if m["term_id"] is not None:
            if m["image_url"]:
                image = {
                    "url": m["image_url"],
                    "page_url": m["image_page_url"],
                    "photographer": m["image_photographer"] or "",
                    "alt": m["image_alt"],
                }
            else:
                image = None
            synonyms: list[str] = []
            if m["synonyms"]:
                try:
                    parsed = json.loads(m["synonyms"])
                    if isinstance(parsed, list):
                        synonyms = [str(s) for s in parsed if s]
                except (json.JSONDecodeError, TypeError):
                    synonyms = []
            current_cat["items"].append({
                "term": m["term"],
                "image": image,
                "part_of_speech": m["part_of_speech"] or "",
                "ipa": m["ipa"] or "",
                "meaning": m["meaning"] or "",
                "synonyms": synonyms,
                "example": m["example"] or "",
                "vietnamese_meaning": m["vietnamese_meaning"] or "",
            })

    return {
        "id": row.id,
        "attempt_id": row.attempt_id,
        "study4_test_id": row.study4_test_id,
        "question_number": row.question_number,
        "topic": row.topic,
        "categories": [{"name": c["name"], "items": c["items"]} for c in categories],
        "model": row.model,
        "created_at": row.created_at,
    }


async def find_vocab_table_by_question_owned(
    conn: AsyncSession, user_id: int, study4_test_id: int, question_number: int
) -> dict[str, Any] | None:
    row = await conn.scalar(
        select(VocabTable).where(
            VocabTable.user_id == user_id,
            VocabTable.study4_test_id == study4_test_id,
            VocabTable.question_number == question_number,
        )
    )
    if row is None:
        return None
    return await _assemble_payload(conn, row)
