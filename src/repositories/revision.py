from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import RevisionItem
from ..utils import now


def _assemble(row: RevisionItem) -> dict[str, Any]:
    image: dict[str, Any] | None = None
    if row.image_url:
        image = {
            "url": row.image_url,
            "page_url": row.image_page_url,
            "photographer": row.image_photographer or "",
            "alt": row.image_alt,
        }
    synonyms: list[str] = []
    if row.synonyms:
        try:
            parsed = json.loads(row.synonyms)
            if isinstance(parsed, list):
                synonyms = [str(s) for s in parsed if s]
        except (json.JSONDecodeError, TypeError):
            synonyms = []
    return {
        "id": row.id,
        "term": row.term,
        "topic": row.topic or "",
        "image": image,
        "part_of_speech": row.part_of_speech or "",
        "ipa": row.ipa or "",
        "meaning": row.meaning or "",
        "example": row.example or "",
        "vietnamese_meaning": row.vietnamese_meaning or "",
        "synonyms": synonyms,
        "reviewed": bool(row.reviewed),
        "created_at": row.created_at,
    }


async def list_revision(conn: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    rows = (
        await conn.execute(
            select(RevisionItem)
            .where(RevisionItem.user_id == user_id)
            .order_by(RevisionItem.created_at.desc(), RevisionItem.id.desc())
        )
    ).scalars().all()
    return [_assemble(row) for row in rows]


async def _find_existing(conn: AsyncSession, user_id: int, term: str) -> RevisionItem | None:
    return await conn.scalar(
        select(RevisionItem).where(
            RevisionItem.user_id == user_id,
            func.lower(RevisionItem.term) == term.lower(),
        )
    )


def _image_field(image: dict[str, Any] | None, key: str) -> str | None:
    if not isinstance(image, dict):
        return None
    value = image.get(key)
    return str(value).strip() or None if value else None


async def upsert_revision(conn: AsyncSession, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    term = str(data.get("term") or "").strip()
    if not term:
        raise ValueError("term is required")

    raw_synonyms = data.get("synonyms")
    if not isinstance(raw_synonyms, list):
        raw_synonyms = []
    synonyms_list = [str(s).strip() for s in raw_synonyms if str(s).strip()]
    synonyms_json = json.dumps(synonyms_list, ensure_ascii=False) if synonyms_list else None

    image = data.get("image") if isinstance(data.get("image"), dict) else None

    row = await _find_existing(conn, user_id, term)
    created = False
    if row is None:
        row = RevisionItem(
            user_id=user_id,
            term=term,
            topic=str(data.get("topic") or "").strip(),
            image_url=_image_field(image, "url"),
            image_page_url=_image_field(image, "page_url"),
            image_photographer=_image_field(image, "photographer"),
            image_alt=_image_field(image, "alt"),
            part_of_speech=(str(data.get("part_of_speech") or "").strip() or None),
            ipa=(str(data.get("ipa") or "").strip() or None),
            meaning=(str(data.get("meaning") or "").strip() or None),
            example=(str(data.get("example") or "").strip() or None),
            vietnamese_meaning=(str(data.get("vietnamese_meaning") or "").strip() or None),
            synonyms=synonyms_json,
            created_at=now(),
        )
        conn.add(row)
        created = True
    else:
        row.topic = str(data.get("topic") or "").strip()
        row.image_url = _image_field(image, "url")
        row.image_page_url = _image_field(image, "page_url")
        row.image_photographer = _image_field(image, "photographer")
        row.image_alt = _image_field(image, "alt")
        row.part_of_speech = (str(data.get("part_of_speech") or "").strip() or None)
        row.ipa = (str(data.get("ipa") or "").strip() or None)
        row.meaning = (str(data.get("meaning") or "").strip() or None)
        row.example = (str(data.get("example") or "").strip() or None)
        row.vietnamese_meaning = (
            str(data.get("vietnamese_meaning") or "").strip() or None
        )
        row.synonyms = synonyms_json
    await conn.flush()
    payload = _assemble(row)
    payload["created"] = created
    return payload


async def find_revision_owned(
    conn: AsyncSession, user_id: int, item_id: int
) -> RevisionItem | None:
    return await conn.scalar(
        select(RevisionItem).where(
            RevisionItem.id == item_id,
            RevisionItem.user_id == user_id,
        )
    )


async def delete_revision(conn: AsyncSession, user_id: int, item_id: int) -> bool:
    row = await find_revision_owned(conn, user_id, item_id)
    if row is None:
        return False
    await conn.delete(row)
    await conn.flush()
    return True


async def mark_reviewed(
    conn: AsyncSession, user_id: int, item_id: int, reviewed: bool = True
) -> dict[str, Any] | None:
    row = await find_revision_owned(conn, user_id, item_id)
    if row is None:
        return None
    row.reviewed = 1 if reviewed else 0
    await conn.flush()
    return _assemble(row)
