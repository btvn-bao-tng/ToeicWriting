from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any

from ..config import PEXELS_API_KEY, PEXELS_SEARCH_TIMEOUT

PEXELS_ENDPOINT = "https://api.pexels.com/v1/search"
MAX_IMAGE_WORKERS = 6
MAX_TOTAL_TERMS = 28


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query or "").strip().lower()


@lru_cache(maxsize=2048)
def _cached_pexels_search(query: str) -> dict[str, Any] | None:
    if not PEXELS_API_KEY:
        return None
    params = urllib.parse.urlencode(
        {"query": query, "per_page": 1, "orientation": "landscape"}
    )
    request = urllib.request.Request(
        f"{PEXELS_ENDPOINT}?{params}",
        headers={
            "Authorization": PEXELS_API_KEY,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=PEXELS_SEARCH_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None

    photos = data.get("photos") or []
    if not photos:
        return None
    photo = photos[0]
    return {
        "url": photo["src"]["medium"],
        "page_url": photo["url"],
        "photographer": photo.get("photographer", ""),
        "alt": photo.get("alt") or query,
    }


def search_image(query: str) -> dict[str, Any] | None:
    normalized = _normalize_query(query)
    if not normalized:
        return None
    return _cached_pexels_search(normalized)


def _photo_to_dict(photo: dict[str, Any], fallback_query: str) -> dict[str, Any]:
    return {
        "url": photo["src"]["medium"],
        "page_url": photo["url"],
        "photographer": photo.get("photographer", ""),
        "alt": photo.get("alt") or fallback_query,
    }


@lru_cache(maxsize=1024)
def _cached_pexels_search_many(query: str, count: int) -> tuple[dict[str, Any], ...]:
    if not PEXELS_API_KEY:
        return ()
    params = urllib.parse.urlencode(
        {"query": query, "per_page": count, "orientation": "landscape"}
    )
    request = urllib.request.Request(
        f"{PEXELS_ENDPOINT}?{params}",
        headers={
            "Authorization": PEXELS_API_KEY,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=PEXELS_SEARCH_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        return ()

    photos = data.get("photos") or []
    return tuple(_photo_to_dict(p, query) for p in photos[:count])


def search_image_set(query: str, count: int = 4) -> list[dict[str, Any]]:
    normalized = _normalize_query(query)
    if not normalized or count <= 0:
        return []
    return list(_cached_pexels_search_many(normalized, count))


def search_extra_images(
    query: str, exclude_url: str | None = None, count: int = 2
) -> list[dict[str, Any]]:
    pool = search_image_set(query, count + 2)
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


def _search_for_term(term: str, topic: str) -> dict[str, Any] | None:
    result = search_image(term)
    if result is None and topic:
        result = search_image(f"{topic} {term}")
    return result


def attach_images(
    categories: list[dict[str, Any]], topic: str
) -> list[dict[str, Any]]:
    jobs: list[tuple[int, int, str]] = []
    for cat_index, category in enumerate(categories):
        terms = category.get("terms") or []
        for term_index, term in enumerate(terms):
            if not isinstance(term, str) or not term.strip():
                continue
            jobs.append((cat_index, term_index, term.strip()))

    results: dict[tuple[int, int], dict[str, Any] | None] = {}
    if jobs:
        with ThreadPoolExecutor(max_workers=MAX_IMAGE_WORKERS) as executor:
            futures = {
                executor.submit(_search_for_term, term, topic): (cat_index, term_index)
                for cat_index, term_index, term in jobs
            }
            for future, (cat_index, term_index) in futures.items():
                try:
                    results[(cat_index, term_index)] = future.result()
                except Exception:
                    results[(cat_index, term_index)] = None

    out_categories: list[dict[str, Any]] = []
    for cat_index, category in enumerate(categories):
        terms = category.get("terms") or []
        items: list[dict[str, Any]] = []
        for term_index, term in enumerate(terms):
            if not isinstance(term, str) or not term.strip():
                continue
            image = results.get((cat_index, term_index))
            items.append({"term": term.strip(), "image": image})
        out_categories.append({"name": category.get("name") or "", "items": items})

    return out_categories
