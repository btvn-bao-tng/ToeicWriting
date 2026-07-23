from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..database import db
from ..repositories import tests as tests_repo
from ..utils import decode_assets

_tests_cache: tuple[dict[str, Any], ...] | None = None
_payload_cache: dict[int, dict[str, Any] | None] = {}
_question_cache: dict[tuple[int, int], dict[str, Any] | None] = {}


async def list_tests() -> list[dict[str, Any]]:
    global _tests_cache
    if _tests_cache is None:
        async with db() as conn:
            _tests_cache = tuple(await tests_repo.list_tests(conn))
    return deepcopy(list(_tests_cache))


async def get_test_payload(study4_test_id: int) -> dict[str, Any] | None:
    if study4_test_id in _payload_cache:
        return deepcopy(_payload_cache[study4_test_id])

    async with db() as conn:
        test = await tests_repo.find_test(conn, study4_test_id)
        if test is None:
            _payload_cache[study4_test_id] = None
            return None

        parts = await tests_repo.list_parts(conn, study4_test_id)
        questions = await tests_repo.list_questions(conn, study4_test_id)

    for item in questions:
        item["asset_urls"] = decode_assets(item.get("asset_urls"))

    payload = {"test": test, "parts": parts, "questions": questions}
    _payload_cache[study4_test_id] = payload
    return deepcopy(payload)


async def find_question(study4_test_id: int, question_number: int) -> dict[str, Any] | None:
    key = (study4_test_id, question_number)
    if key in _question_cache:
        return deepcopy(_question_cache[key])

    async with db() as conn:
        question = await tests_repo.find_question(conn, study4_test_id, question_number)

    _question_cache[key] = question
    return deepcopy(question)


def clear_cache() -> None:
    global _tests_cache
    _tests_cache = None
    _payload_cache.clear()
    _question_cache.clear()
