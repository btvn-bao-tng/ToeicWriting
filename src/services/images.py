from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
from typing import Any

import httpx

from ..config import PEXELS_API_KEY, PEXELS_SEARCH_TIMEOUT

PEXELS_ENDPOINT = "https://api.pexels.com/v1/search"
MAX_IMAGE_WORKERS = 6
MAX_TOTAL_TERMS = 28


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query or "").strip().lower()


def _headers() -> dict[str, str]:
    return {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }


async def _pexels_get(query: str, per_page: int) -> list[dict[str, Any]]:
    if not PEXELS_API_KEY:
        return []
    params = urllib.parse.urlencode(
        {"query": query, "per_page": per_page, "orientation": "landscape"}
    )
    try:
        async with httpx.AsyncClient(timeout=PEXELS_SEARCH_TIMEOUT) as client:
            response = await client.get(
                f"{PEXELS_ENDPOINT}?{params}", headers=_headers()
            )
    except (httpx.HTTPError, ValueError):
        return []

    if response.status_code >= 400:
        return []
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError):
        return []

    return data.get("photos") or []


_search_cache: dict[str, dict[str, Any] | None] = {}
_search_set_cache: dict[tuple[str, int], tuple[dict[str, Any], ...]] = {}


def _photo_to_dict(photo: dict[str, Any], fallback_query: str) -> dict[str, Any]:
    return {
        "url": photo["src"]["medium"],
        "page_url": photo["url"],
        "photographer": photo.get("photographer", ""),
        "alt": photo.get("alt") or fallback_query,
    }


async def search_image(query: str) -> dict[str, Any] | None:
    normalized = _normalize_query(query)
    if not normalized:
        return None
    if normalized in _search_cache:
        return _search_cache[normalized]
    photos = await _pexels_get(normalized, 1)
    result = _photo_to_dict(photos[0], normalized) if photos else None
    _search_cache[normalized] = result
    return result


async def search_image_set(query: str, count: int = 4) -> list[dict[str, Any]]:
    normalized = _normalize_query(query)
    if not normalized or count <= 0:
        return []
    key = (normalized, count)
    if key in _search_set_cache:
        return list(_search_set_cache[key])
    photos = await _pexels_get(normalized, count)
    result = tuple(_photo_to_dict(p, normalized) for p in photos[:count])
    _search_set_cache[key] = result
    return list(result)


async def search_extra_images(
    query: str, exclude_url: str | None = None, count: int = 2
) -> list[dict[str, Any]]:
    pool = await search_image_set(query, count + 2)
    extras: list[dict[str, Any]] = []
    seen: set[str] = set()
    for image in pool:
        url = image.get("url")
        if not url or url == exclude_url or url in seen:
            continue
        seen.add(url)
        extras.append(image)
        if len(extras) >= count:
            break
    return extras


async def _search_for_term(term: str, topic: str) -> dict[str, Any] | None:
    result = await search_image(term)
    if result is None and topic:
        result = await search_image(f"{topic} {term}")
    return result


async def attach_images(
    categories: list[dict[str, Any]], topic: str
) -> list[dict[str, Any]]:
    jobs: list[tuple[int, int, str]] = []
    for cat_index, category in enumerate(categories):
        items = category.get("items") or []
        for term_index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            if not term:
                continue
            jobs.append((cat_index, term_index, term))

    results: dict[tuple[int, int], dict[str, Any] | None] = {}
    if jobs:
        semaphore = asyncio.Semaphore(MAX_IMAGE_WORKERS)

        async def _bound_search(cat_index: int, term_index: int, term: str) -> None:
            async with semaphore:
                try:
                    results[(cat_index, term_index)] = await _search_for_term(term, topic)
                except Exception:
                    results[(cat_index, term_index)] = None

        await asyncio.gather(
            *(_bound_search(c, t, term) for c, t, term in jobs)
        )

    out_categories: list[dict[str, Any]] = []
    for cat_index, category in enumerate(categories):
        items = category.get("items") or []
        out_items: list[dict[str, Any]] = []
        for term_index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            if not term:
                continue
            enriched = dict(item)
            enriched["image"] = results.get((cat_index, term_index))
            out_items.append(enriched)
        out_categories.append({"name": category.get("name") or "", "items": out_items})

    return out_categories
