#!/usr/bin/env python3
"""Update Study4 part IDs from cached public detail pages."""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_parts(html: str) -> list[dict[str, int | str | None]]:
    parts = []
    pattern = re.compile(
        r"<input[^>]+(?:id=['\"]part-(?P<id1>\d+)['\"][^>]+value=['\"](?P<value1>\d+)['\"]"
        r"|value=['\"](?P<value2>\d+)['\"][^>]+id=['\"]part-(?P<id2>\d+)['\"])[^>]*>"
        r".*?<label[^>]*>(?P<label>.*?)</label>",
        re.IGNORECASE | re.DOTALL,
    )
    for index, match in enumerate(pattern.finditer(html), start=1):
        part_id = int(match.group("value1") or match.group("value2") or match.group("id1") or match.group("id2"))
        label = clean_text(match.group("label"))
        count_match = re.search(r"\((\d+)\s*câu hỏi\)", label)
        parts.append(
            {
                "study4_part_id": part_id,
                "sort_order": index,
                "label": label,
                "question_count": int(count_match.group(1)) if count_match else None,
            }
        )
    return parts


def question_range(sort_order: int) -> tuple[int, int]:
    if sort_order == 1:
        return 1, 5
    if sort_order == 2:
        return 6, 7
    return 8, 8


def update_parts(db_path: Path, cache_dir: Path) -> int:
    updated_tests = 0
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        tests = conn.execute(
            """
            SELECT study4_test_id, test_number
            FROM toeic_sw_writing_tests
            ORDER BY test_number
            """
        ).fetchall()

        for test in tests:
            path = cache_dir / f"study4_detail_{test['study4_test_id']}.html"
            if not path.exists():
                print(f"missing detail cache for test {test['test_number']}: {path}")
                continue

            parts = parse_parts(path.read_text(encoding="utf-8", errors="replace"))
            if len(parts) != 3:
                print(f"skipped test {test['test_number']}: found {len(parts)} parts")
                continue

            for part in parts:
                old_part = conn.execute(
                    """
                    SELECT study4_part_id
                    FROM toeic_sw_writing_parts
                    WHERE study4_test_id = ? AND sort_order = ?
                    """,
                    (test["study4_test_id"], part["sort_order"]),
                ).fetchone()

                if old_part and old_part["study4_part_id"] != part["study4_part_id"]:
                    conn.execute(
                        "UPDATE toeic_sw_writing_questions SET study4_part_id = NULL WHERE study4_part_id = ?",
                        (old_part["study4_part_id"],),
                    )
                    conn.execute(
                        "DELETE FROM toeic_sw_writing_parts WHERE study4_part_id = ?",
                        (old_part["study4_part_id"],),
                    )

                conn.execute(
                    """
                    INSERT INTO toeic_sw_writing_parts (
                        study4_part_id, study4_test_id, sort_order, label, question_count, source
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(study4_part_id) DO UPDATE SET
                        study4_test_id = excluded.study4_test_id,
                        sort_order = excluded.sort_order,
                        label = excluded.label,
                        question_count = excluded.question_count,
                        source = excluded.source
                    """,
                    (
                        part["study4_part_id"],
                        test["study4_test_id"],
                        part["sort_order"],
                        part["label"],
                        part["question_count"] or 0,
                        "study4_detail",
                    ),
                )

                start, end = question_range(int(part["sort_order"]))
                conn.execute(
                    """
                    UPDATE toeic_sw_writing_questions
                    SET study4_part_id = ?
                    WHERE study4_test_id = ?
                        AND question_number BETWEEN ? AND ?
                    """,
                    (part["study4_part_id"], test["study4_test_id"], start, end),
                )

            conn.execute(
                """
                UPDATE toeic_sw_writing_tests
                SET source = CASE
                    WHEN source LIKE '%datamd%' THEN source
                    ELSE 'study4_detail'
                END
                WHERE study4_test_id = ?
                """,
                (test["study4_test_id"],),
            )
            updated_tests += 1

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")

    return updated_tests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/database.db"))
    parser.add_argument("--cache-dir", type=Path, default=Path("/private/tmp/study4_details"))
    args = parser.parse_args()
    count = update_parts(args.db, args.cache_dir)
    print(f"Updated part IDs for {count} tests")


if __name__ == "__main__":
    main()
