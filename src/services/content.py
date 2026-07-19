from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

from ..database import db
from ..repositories import tests as tests_repo
from ..utils import decode_assets


@lru_cache(maxsize=1)
def _cached_tests() -> tuple[dict[str, Any], ...]:
    with db() as conn:
        return tuple(tests_repo.list_tests(conn))


@lru_cache(maxsize=128)
def _cached_test_payload(study4_test_id: int) -> dict[str, Any] | None:
    with db() as conn:
        test = tests_repo.find_test(conn, study4_test_id)
        if test is None:
            return None

        parts = tests_repo.list_parts(conn, study4_test_id)
        questions = tests_repo.list_questions(conn, study4_test_id)

    for item in questions:
        item["asset_urls"] = decode_assets(item.get("asset_urls"))

    return {"test": test, "parts": parts, "questions": questions}


@lru_cache(maxsize=512)
def _cached_question(
    study4_test_id: int,
    question_number: int,
) -> dict[str, Any] | None:
    with db() as conn:
        return tests_repo.find_question(conn, study4_test_id, question_number)


def list_tests() -> list[dict[str, Any]]:
    return deepcopy(list(_cached_tests()))


def get_test_payload(study4_test_id: int) -> dict[str, Any] | None:
    return deepcopy(_cached_test_payload(study4_test_id))


def find_question(study4_test_id: int, question_number: int) -> dict[str, Any] | None:
    return deepcopy(_cached_question(study4_test_id, question_number))


def clear_cache() -> None:
    _cached_tests.cache_clear()
    _cached_test_payload.cache_clear()
    _cached_question.cache_clear()
