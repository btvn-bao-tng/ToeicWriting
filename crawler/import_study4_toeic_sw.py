#!/usr/bin/env python3
"""Import public Study4 TOEIC SW Writing test metadata into SQLite.

The authenticated practice pages contain the actual prompts, but Study4 redirects
those pages to login without a valid Study4 session cookie. This importer stores
the public metadata and part IDs so the database has stable records for the last
Writing tests discovered from the library listing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sqlite3
from pathlib import Path


BASE_URL = "https://study4.com"


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def find_writing_links(cache_dir: Path) -> list[dict[str, object]]:
    found: dict[int, dict[str, object]] = {}
    pattern = re.compile(
        r"/tests/(?P<id>\d+)/toeic-sw-writing-test-(?P<num>\d+)/",
        re.IGNORECASE,
    )

    for path in sorted(cache_dir.glob("study4_toeic_sw_page*.html")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in pattern.finditer(text):
            test_id = int(match.group("id"))
            test_number = int(match.group("num"))
            slug = f"toeic-sw-writing-test-{test_number}"
            found[test_id] = {
                "study4_test_id": test_id,
                "test_number": test_number,
                "title": f"TOEIC SW Writing Test {test_number}",
                "slug": slug,
                "url": f"{BASE_URL}/tests/{test_id}/{slug}/",
            }

    return sorted(found.values(), key=lambda item: int(item["test_number"]))


def extract_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def parse_detail(cache_dir: Path, test_id: int) -> dict[str, object]:
    path = cache_dir / f"study4_detail_{test_id}.html"
    if not path.exists():
        return {"detail_html_path": None, "parts": [], "access_status": "detail_missing"}

    html_text = path.read_text(encoding="utf-8", errors="replace")
    page_text = clean_text(html_text)

    h1_match = re.search(r"<h1[^>]*>(?P<h1>.*?)</h1>", html_text, re.IGNORECASE | re.DOTALL)
    title = clean_text(h1_match.group("h1")) if h1_match else None

    parts = []
    part_pattern = re.compile(
        r"<input[^>]+(?:id=['\"]part-(?P<id1>\d+)['\"][^>]+value=['\"](?P<value1>\d+)['\"]"
        r"|value=['\"](?P<value2>\d+)['\"][^>]+id=['\"]part-(?P<id2>\d+)['\"])[^>]*>"
        r".*?<label[^>]*>(?P<label>.*?)</label>",
        re.IGNORECASE | re.DOTALL,
    )
    for index, match in enumerate(part_pattern.finditer(html_text), start=1):
        part_id = int(match.group("value1") or match.group("value2") or match.group("id1") or match.group("id2"))
        label = clean_text(match.group("label"))
        question_count = extract_int(r"\((\d+)\s*câu hỏi\)", label)
        parts.append(
            {
                "study4_part_id": part_id,
                "sort_order": index,
                "label": label,
                "question_count": question_count,
            }
        )

    is_login = "/login/" in html_text and "auth-box-wrapper" in html_text
    return {
        "title": title,
        "duration_minutes": extract_int(r"Thời gian làm bài:\s*(\d+)\s*phút", page_text),
        "part_count": extract_int(r"(\d+)\s*phần thi", page_text),
        "question_count": extract_int(r"(\d+)\s*câu hỏi", page_text),
        "practice_count": extract_int(r"(\d+)\s*người đã luyện tập", page_text),
        "detail_html_path": str(path),
        "public_detail_html": html_text,
        "parts": parts,
        "access_status": "login_required_for_prompts" if not is_login else "login_page",
    }


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS crawl_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT NOT NULL,
            crawled_at TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS toeic_sw_writing_tests (
            study4_test_id INTEGER PRIMARY KEY,
            test_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            slug TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            duration_minutes INTEGER,
            part_count INTEGER,
            question_count INTEGER,
            practice_count INTEGER,
            access_status TEXT NOT NULL,
            detail_html_path TEXT,
            public_detail_html TEXT,
            detail_fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS toeic_sw_writing_parts (
            study4_part_id INTEGER PRIMARY KEY,
            study4_test_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL,
            label TEXT NOT NULL,
            question_count INTEGER,
            FOREIGN KEY(study4_test_id) REFERENCES toeic_sw_writing_tests(study4_test_id)
        );

        CREATE TABLE IF NOT EXISTS toeic_sw_writing_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study4_test_id INTEGER NOT NULL,
            study4_part_id INTEGER,
            question_number INTEGER,
            prompt_html TEXT,
            prompt_text TEXT,
            asset_urls TEXT,
            answer_hint TEXT,
            FOREIGN KEY(study4_test_id) REFERENCES toeic_sw_writing_tests(study4_test_id),
            FOREIGN KEY(study4_part_id) REFERENCES toeic_sw_writing_parts(study4_part_id),
            UNIQUE(study4_test_id, question_number)
        );
        """
    )
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(toeic_sw_writing_tests)").fetchall()
    }
    if "public_detail_html" not in columns:
        conn.execute("ALTER TABLE toeic_sw_writing_tests ADD COLUMN public_detail_html TEXT")


def import_tests(db_path: Path, cache_dir: Path, limit: int) -> list[dict[str, object]]:
    now = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    tests = find_writing_links(cache_dir)[-limit:]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO crawl_runs (source_url, crawled_at, status, note)
            VALUES (?, ?, ?, ?)
            """,
            (
                f"{BASE_URL}/tests/toeic-sw/",
                now,
                "partial",
                "Imported public metadata. Authenticated practice prompts require a valid Study4 session cookie.",
            ),
        )

        for test in tests:
            detail = parse_detail(cache_dir, int(test["study4_test_id"]))
            title = detail.get("title") or test["title"]
            conn.execute(
                """
                INSERT INTO toeic_sw_writing_tests (
                    study4_test_id, test_number, title, slug, url, duration_minutes,
                    part_count, question_count, practice_count, access_status,
                    detail_html_path, public_detail_html, detail_fetched_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(study4_test_id) DO UPDATE SET
                    test_number = excluded.test_number,
                    title = excluded.title,
                    slug = excluded.slug,
                    url = excluded.url,
                    duration_minutes = excluded.duration_minutes,
                    part_count = excluded.part_count,
                    question_count = excluded.question_count,
                    practice_count = excluded.practice_count,
                    access_status = excluded.access_status,
                    detail_html_path = excluded.detail_html_path,
                    public_detail_html = excluded.public_detail_html,
                    detail_fetched_at = excluded.detail_fetched_at
                """,
                (
                    test["study4_test_id"],
                    test["test_number"],
                    title,
                    test["slug"],
                    test["url"],
                    detail.get("duration_minutes"),
                    detail.get("part_count"),
                    detail.get("question_count"),
                    detail.get("practice_count"),
                    detail.get("access_status"),
                    detail.get("detail_html_path"),
                    detail.get("public_detail_html"),
                    now,
                ),
            )

            for part in detail["parts"]:
                conn.execute(
                    """
                    INSERT INTO toeic_sw_writing_parts (
                        study4_part_id, study4_test_id, sort_order, label, question_count
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(study4_part_id) DO UPDATE SET
                        study4_test_id = excluded.study4_test_id,
                        sort_order = excluded.sort_order,
                        label = excluded.label,
                        question_count = excluded.question_count
                    """,
                    (
                        part["study4_part_id"],
                        test["study4_test_id"],
                        part["sort_order"],
                        part["label"],
                        part["question_count"],
                    ),
                )

    return tests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/database.db"))
    parser.add_argument("--cache-dir", type=Path, default=Path("/private/tmp"))
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    imported = import_tests(args.db, args.cache_dir, args.limit)
    print(f"Imported {len(imported)} Study4 TOEIC SW Writing tests into {args.db}")
    for test in imported:
        print(f"- {test['title']} ({test['url']})")


if __name__ == "__main__":
    main()
