from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from ..config import MAX_IMAGE_ATTACHMENTS, SYSTEM_PROMPT_DIR
from ..utils import decode_assets
from . import ai as ai_service
from . import images as image_service
from .scoring import fetch_image_as_data_url

VOCAB_SYSTEM_PROMPT_PATH = SYSTEM_PROMPT_DIR / "vocab.md"
VOCAB_DETAIL_PROMPT_PATH = SYSTEM_PROMPT_DIR / "vocab_detail.md"

MAX_CATEGORIES = 6
MAX_TERMS_PER_CATEGORY = 6
MAX_TOTAL_TERMS = 28


def _system_prompt() -> str:
    if VOCAB_SYSTEM_PROMPT_PATH.exists():
        prompt = VOCAB_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8", errors="replace").strip()
        if prompt:
            return prompt
    return (
        "You are an expert TOEIC Writing vocabulary curator. "
        'Return ONLY a JSON object: {"topic": "LABEL", "categories": '
        '[{"name": "CATEGORY", "terms": ["..."]}]} with 3-6 categories, '
        "3-6 terms each, at most 28 total terms, no duplicates."
    )


def _strip_html(html: str | None) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def build_vocab_user_content(
    question_row: dict[str, Any],
    answer: str,
    score_text: str,
) -> list[dict[str, Any]]:
    assets = decode_assets(question_row.get("asset_urls"))
    lines = [
        f"Test: {question_row.get('title') or ''}",
        f"Part: {question_row.get('part_order') or ''} ({question_row.get('part_label') or 'Unknown part'})",
        f"Question number: {question_row.get('question_number')}",
        f"Prompt text:\n{question_row.get('prompt_text') or ''}",
        f"Prompt (from HTML):\n{_strip_html(question_row.get('prompt_html'))}",
        "Image or asset URLs:\n" + ("\n".join(assets) if assets else "None"),
        f"User answer:\n{answer}",
        f"Examiner feedback:\n{score_text or ''}",
        (
            "Using the scene shown in the attached images (or described above), "
            "generate the topic-grouped vocabulary study table as a single JSON "
            "object only."
        ),
    ]
    content: list[dict[str, Any]] = [{"type": "text", "text": "\n\n".join(lines)}]

    failures: list[str] = []
    for index, url in enumerate(assets[:MAX_IMAGE_ATTACHMENTS], start=1):
        data_url, error = fetch_image_as_data_url(url)
        if error:
            failures.append(error)
            continue
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": data_url, "detail": "high"},
            }
        )
        content.append({"type": "text", "text": f"Attached image {index}: {url}"})

    if len(assets) > MAX_IMAGE_ATTACHMENTS:
        failures.append(
            f"{len(assets) - MAX_IMAGE_ATTACHMENTS} image(s) were skipped by MAX_IMAGE_ATTACHMENTS"
        )
    if failures:
        content.append(
            {
                "type": "text",
                "text": "Image fetch notes:\n"
                + "\n".join(f"- {failure}" for failure in failures),
            }
        )

    return content


def _extract_json(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("Empty response")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found")
        cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg}") from exc


def _item_from_raw(raw_item: Any) -> dict[str, Any] | None:
    if isinstance(raw_item, str):
        raw_item = {"term": raw_item}
    if not isinstance(raw_item, dict):
        return None
    term = str(raw_item.get("term") or "").strip()
    if not term:
        return None
    raw_synonyms = raw_item.get("synonyms")
    if not isinstance(raw_synonyms, list):
        raw_synonyms = []
    synonyms = [str(s).strip() for s in raw_synonyms if str(s).strip()]
    return {
        "term": term,
        "part_of_speech": str(raw_item.get("part_of_speech") or "").strip(),
        "ipa": str(raw_item.get("ipa") or "").strip(),
        "meaning": str(
            raw_item.get("meaning") or raw_item.get("explanation") or ""
        ).strip(),
        "synonyms": synonyms,
        "example": str(raw_item.get("example") or "").strip(),
        "vietnamese_meaning": str(
            raw_item.get("vietnamese_meaning")
            or raw_item.get("vietnamese")
            or ""
        ).strip(),
    }


def _normalize_table(raw: dict[str, Any]) -> dict[str, Any]:
    topic = str(raw.get("topic") or "").strip().upper()
    raw_categories = raw.get("categories")
    if not isinstance(raw_categories, list):
        raise ValueError("Missing 'categories' array")

    seen: set[str] = set()
    categories: list[dict[str, Any]] = []
    total = 0

    for category in raw_categories[:MAX_CATEGORIES]:
        if not isinstance(category, dict):
            continue
        name = str(category.get("name") or "").strip().upper()
        if not name:
            continue
        raw_items = category.get("items")
        if not isinstance(raw_items, list):
            raw_items = category.get("terms") or []
        if not isinstance(raw_items, list):
            continue
        clean_items: list[dict[str, Any]] = []
        for raw_item in raw_items[:MAX_TERMS_PER_CATEGORY]:
            if total >= MAX_TOTAL_TERMS:
                break
            item = _item_from_raw(raw_item)
            if item is None:
                continue
            key = item["term"].lower()
            if key in seen:
                continue
            seen.add(key)
            clean_items.append(item)
            total += 1
        if clean_items:
            categories.append({"name": name, "items": clean_items})
        if total >= MAX_TOTAL_TERMS:
            break

    if not categories:
        raise ValueError("No usable vocabulary terms found in response")

    return {"topic": topic, "categories": categories}


async def generate_table(
    question_row: dict[str, Any],
    answer: str,
    score_text: str,
) -> dict[str, Any]:
    user_content = await run_in_threadpool(
        build_vocab_user_content, question_row, answer, score_text
    )
    raw_text = await ai_service.ai_chat(_system_prompt(), user_content)
    try:
        raw = _extract_json(raw_text)
        table = _normalize_table(raw)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Could not parse vocab table: {exc}") from exc

    categories_with_images = await run_in_threadpool(
        image_service.attach_images, table["categories"], table["topic"]
    )
    return {"topic": table["topic"], "categories": categories_with_images}


def _detail_system_prompt() -> str:
    if VOCAB_DETAIL_PROMPT_PATH.exists():
        prompt = VOCAB_DETAIL_PROMPT_PATH.read_text(encoding="utf-8", errors="replace").strip()
        if prompt:
            return prompt
    return (
        "You are an English vocabulary coach. Return ONLY a JSON object: "
        '{"term": "...", "part_of_speech": "...", "ipa": "/.../", '
        '"register": "...", "explanation": "...", "example": "...", '
        '"synonyms": ["..."], "collocations": ["..."]} for the given term.'
    )


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


@lru_cache(maxsize=1024)
def _cached_term_explanation(term: str, topic: str, question_prompt: str) -> dict[str, Any]:
    user_text = f"Term: {term}"
    if topic:
        user_text += f"\nScene / topic context: {topic}"
    if question_prompt:
        user_text += (
            "\nQuestion picture / prompt description (the example MUST relate to this):\n"
            + question_prompt
        )
    user_text += "\n\nReturn the study-card JSON for this term only."
    raw_text = ai_service._ai_chat_sync(
        _detail_system_prompt(), [{"type": "text", "text": user_text}]
    )
    try:
        raw = _extract_json(raw_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not parse vocab detail: {exc}"
        ) from exc

    return {
        "term": term,
        "part_of_speech": str(raw.get("part_of_speech") or "").strip(),
        "ipa": str(raw.get("ipa") or "").strip(),
        "register": str(raw.get("register") or "").strip(),
        "explanation": str(raw.get("explanation") or "").strip(),
        "example": str(raw.get("example") or "").strip(),
        "synonyms": _as_str_list(raw.get("synonyms")),
        "collocations": _as_str_list(raw.get("collocations")),
    }


async def generate_term_detail(
    term: str,
    topic: str,
    main_image_url: str | None = None,
    question_prompt: str = "",
) -> dict[str, Any]:
    clean_term = (term or "").strip()
    if not clean_term:
        raise HTTPException(status_code=400, detail="term is required")

    detail = await run_in_threadpool(
        _cached_term_explanation, clean_term, topic, (question_prompt or "").strip()
    )
    primary_query = clean_term
    extras = await run_in_threadpool(
        image_service.search_extra_images, primary_query, exclude_url=main_image_url, count=2
    )
    if not extras and topic:
        extras = await run_in_threadpool(
            image_service.search_extra_images,
            f"{topic} {clean_term}",
            exclude_url=main_image_url,
            count=2,
        )
    detail["images"] = extras
    return detail
