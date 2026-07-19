#!/usr/bin/env python3
"""Import datamd Markdown files into the TOEIC SW SQLite database.

This migration keeps authenticated Study4 crawl data where it exists, adds raw
Markdown/source fields, and fills missing tests/questions from datamd.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path


BASE_URL = "https://study4.com"
PARTS = (
    (1, "Questions 1-5 (5 cau hoi)", 5),
    (2, "Questions 6-7 (2 cau hoi)", 2),
    (3, "Question 8 (1 cau hoi)", 1),
)


@dataclass
class MarkdownQuestion:
    question_number: int
    part_order: int
    heading: str
    text: str
    html_value: str
    assets: list[str]


@dataclass
class MarkdownTest:
    test_number: int
    study4_test_id: int
    path: Path
    raw_markdown: str
    questions: list[MarkdownQuestion]


def read_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    if not exists:
        return []
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]


def first_group(pattern: str, text: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def markdown_image_html(url: str, alt: str) -> str:
    return f'<p><img alt="{html.escape(alt, quote=True)}" src="{html.escape(url, quote=True)}"></p>'


def markdown_text_html(text: str) -> str:
    paragraphs = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]
    return "\n".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs)


def parse_markdown_file(path: Path) -> MarkdownTest:
    match = re.search(r"sw-writing-test-(\d+)-id_(\d+)\.md$", path.name)
    if not match:
        raise ValueError(f"Unexpected datamd filename: {path}")

    test_number = int(match.group(1))
    study4_test_id = int(match.group(2))
    raw = path.read_text(encoding="utf-8", errors="replace")
    questions: list[MarkdownQuestion] = []

    image_matches = re.findall(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)", raw)
    for index, (alt, url) in enumerate(image_matches[:5], start=1):
        questions.append(
            MarkdownQuestion(
                question_number=index,
                part_order=1,
                heading=f"Image {index}",
                text=alt or f"Image {index}",
                html_value=markdown_image_html(url, alt or f"Image {index}"),
                assets=[url],
            )
        )

    request_blocks = re.findall(
        r"\*\*Request\s+(\d+)\*\*\s*```text\s*(.*?)\s*```",
        raw,
        re.DOTALL | re.IGNORECASE,
    )
    for request_number, text in request_blocks[:2]:
        qnum = 5 + int(request_number)
        questions.append(
            MarkdownQuestion(
                question_number=qnum,
                part_order=2,
                heading=f"Request {request_number}",
                text=text.strip(),
                html_value=markdown_text_html(text.strip()),
                assets=[],
            )
        )

    essay_section = first_group(
        r"##\s*3\.\s*Write an opinion essay\s*(.*)$",
        raw,
        re.DOTALL | re.IGNORECASE,
    )
    essay_lines = []
    for line in essay_section.splitlines():
        line = line.strip()
        if line.startswith(">"):
            essay_lines.append(line.lstrip("> "))
    essay = "\n".join(essay_lines).strip()
    if essay:
        questions.append(
            MarkdownQuestion(
                question_number=8,
                part_order=3,
                heading="Opinion essay",
                text=essay,
                html_value=markdown_text_html(essay),
                assets=[],
            )
        )

    if len(questions) != 8:
        raise ValueError(f"Expected 8 questions in {path}, found {len(questions)}")

    return MarkdownTest(
        test_number=test_number,
        study4_test_id=study4_test_id,
        path=path,
        raw_markdown=raw,
        questions=sorted(questions, key=lambda question: question.question_number),
    )


def synthetic_part_id(study4_test_id: int, sort_order: int) -> int:
    return -(study4_test_id * 10 + sort_order)


def create_clean_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS toeic_sw_writing_questions;
        DROP TABLE IF EXISTS toeic_sw_writing_parts;
        DROP TABLE IF EXISTS toeic_sw_writing_tests;
        DROP TABLE IF EXISTS crawl_runs;

        CREATE TABLE crawl_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT NOT NULL,
            crawled_at TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT
        );

        CREATE TABLE toeic_sw_writing_tests (
            study4_test_id INTEGER PRIMARY KEY,
            test_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            slug TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            part_count INTEGER NOT NULL DEFAULT 3,
            question_count INTEGER NOT NULL DEFAULT 8,
            practice_count INTEGER,
            access_status TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'datamd',
            detail_html_path TEXT,
            public_detail_html TEXT,
            detail_fetched_at TEXT,
            markdown_path TEXT,
            markdown_content TEXT,
            markdown_imported_at TEXT
        );

        CREATE TABLE toeic_sw_writing_parts (
            study4_part_id INTEGER PRIMARY KEY,
            study4_test_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL,
            label TEXT NOT NULL,
            question_count INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'datamd',
            FOREIGN KEY(study4_test_id) REFERENCES toeic_sw_writing_tests(study4_test_id)
        );

        CREATE TABLE toeic_sw_writing_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study4_test_id INTEGER NOT NULL,
            study4_part_id INTEGER,
            study4_question_id INTEGER,
            question_number INTEGER NOT NULL,
            prompt_html TEXT,
            prompt_text TEXT,
            asset_urls TEXT,
            answer_hint TEXT,
            source TEXT NOT NULL DEFAULT 'datamd',
            markdown_heading TEXT,
            markdown_text TEXT,
            markdown_html TEXT,
            markdown_source_path TEXT,
            FOREIGN KEY(study4_test_id) REFERENCES toeic_sw_writing_tests(study4_test_id),
            FOREIGN KEY(study4_part_id) REFERENCES toeic_sw_writing_parts(study4_part_id),
            UNIQUE(study4_test_id, question_number)
        );

        CREATE INDEX idx_toeic_sw_writing_questions_test
            ON toeic_sw_writing_questions(study4_test_id, question_number);
        CREATE INDEX idx_toeic_sw_writing_parts_test
            ON toeic_sw_writing_parts(study4_test_id, sort_order);
        """
    )


def restore_existing_data(
    conn: sqlite3.Connection,
    tests: list[dict],
    parts: list[dict],
    questions: list[dict],
    runs: list[dict],
) -> None:
    for row in runs:
        conn.execute(
            """
            INSERT INTO crawl_runs (source_url, crawled_at, status, note)
            VALUES (?, ?, ?, ?)
            """,
            (
                row.get("source_url"),
                row.get("crawled_at"),
                row.get("status"),
                row.get("note"),
            ),
        )

    for row in tests:
        conn.execute(
            """
            INSERT OR REPLACE INTO toeic_sw_writing_tests (
                study4_test_id, test_number, title, slug, url, duration_minutes,
                part_count, question_count, practice_count, access_status, source,
                detail_html_path, public_detail_html, detail_fetched_at,
                markdown_path, markdown_content, markdown_imported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("study4_test_id"),
                row.get("test_number"),
                row.get("title"),
                row.get("slug"),
                row.get("url"),
                row.get("duration_minutes") or 60,
                row.get("part_count") or 3,
                row.get("question_count") or 8,
                row.get("practice_count"),
                row.get("access_status") or "questions_crawled",
                row.get("source") or "study4_authenticated",
                row.get("detail_html_path"),
                row.get("public_detail_html"),
                row.get("detail_fetched_at"),
                row.get("markdown_path"),
                row.get("markdown_content"),
                row.get("markdown_imported_at"),
            ),
        )

    for row in parts:
        conn.execute(
            """
            INSERT OR REPLACE INTO toeic_sw_writing_parts (
                study4_part_id, study4_test_id, sort_order, label, question_count, source
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("study4_part_id"),
                row.get("study4_test_id"),
                row.get("sort_order"),
                row.get("label"),
                row.get("question_count") or 0,
                row.get("source") or "study4_authenticated",
            ),
        )

    for row in questions:
        conn.execute(
            """
            INSERT OR REPLACE INTO toeic_sw_writing_questions (
                id, study4_test_id, study4_part_id, study4_question_id,
                question_number, prompt_html, prompt_text, asset_urls,
                answer_hint, source, markdown_heading, markdown_text,
                markdown_html, markdown_source_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("id"),
                row.get("study4_test_id"),
                row.get("study4_part_id"),
                row.get("study4_question_id"),
                row.get("question_number"),
                row.get("prompt_html"),
                row.get("prompt_text"),
                row.get("asset_urls"),
                row.get("answer_hint"),
                row.get("source") or "study4_authenticated",
                row.get("markdown_heading"),
                row.get("markdown_text"),
                row.get("markdown_html"),
                row.get("markdown_source_path"),
            ),
        )


def import_markdown(conn: sqlite3.Connection, markdown_tests: list[MarkdownTest]) -> None:
    imported_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    for md_test in markdown_tests:
        slug = f"toeic-sw-writing-test-{md_test.test_number}"
        existing = conn.execute(
            """
            SELECT access_status, practice_count, detail_html_path, public_detail_html, detail_fetched_at
            FROM toeic_sw_writing_tests
            WHERE study4_test_id = ?
            """,
            (md_test.study4_test_id,),
        ).fetchone()

        access_status = "datamd_imported"
        source = "datamd"
        if existing:
            access_status = existing["access_status"] or "questions_crawled"
            source = "study4_authenticated+datamd" if access_status == "questions_crawled" else "datamd"

        conn.execute(
            """
            INSERT INTO toeic_sw_writing_tests (
                study4_test_id, test_number, title, slug, url, duration_minutes,
                part_count, question_count, practice_count, access_status, source,
                detail_html_path, public_detail_html, detail_fetched_at,
                markdown_path, markdown_content, markdown_imported_at
            )
            VALUES (?, ?, ?, ?, ?, 60, 3, 8, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(study4_test_id) DO UPDATE SET
                test_number = excluded.test_number,
                title = excluded.title,
                slug = excluded.slug,
                url = excluded.url,
                duration_minutes = excluded.duration_minutes,
                part_count = excluded.part_count,
                question_count = excluded.question_count,
                source = excluded.source,
                markdown_path = excluded.markdown_path,
                markdown_content = excluded.markdown_content,
                markdown_imported_at = excluded.markdown_imported_at
            """,
            (
                md_test.study4_test_id,
                md_test.test_number,
                f"TOEIC SW Writing Test {md_test.test_number}",
                slug,
                f"{BASE_URL}/tests/{md_test.study4_test_id}/{slug}/",
                existing["practice_count"] if existing else None,
                access_status,
                source,
                existing["detail_html_path"] if existing else None,
                existing["public_detail_html"] if existing else None,
                existing["detail_fetched_at"] if existing else None,
                str(md_test.path),
                md_test.raw_markdown,
                imported_at,
            ),
        )

        for sort_order, label, count in PARTS:
            existing_part = conn.execute(
                """
                SELECT study4_part_id
                FROM toeic_sw_writing_parts
                WHERE study4_test_id = ? AND sort_order = ?
                """,
                (md_test.study4_test_id, sort_order),
            ).fetchone()
            part_id = (
                existing_part["study4_part_id"]
                if existing_part
                else synthetic_part_id(md_test.study4_test_id, sort_order)
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
                    source = CASE
                        WHEN toeic_sw_writing_parts.source LIKE 'study4%' THEN 'study4_authenticated+datamd'
                        ELSE excluded.source
                    END
                """,
                (
                    part_id,
                    md_test.study4_test_id,
                    sort_order,
                    label,
                    count,
                    "datamd",
                ),
            )

        part_by_order = {
            row["sort_order"]: row["study4_part_id"]
            for row in conn.execute(
                """
                SELECT sort_order, study4_part_id
                FROM toeic_sw_writing_parts
                WHERE study4_test_id = ?
                """,
                (md_test.study4_test_id,),
            ).fetchall()
        }

        for question in md_test.questions:
            part_id = part_by_order[question.part_order]
            existing_question = conn.execute(
                """
                SELECT prompt_html, prompt_text, asset_urls, source
                FROM toeic_sw_writing_questions
                WHERE study4_test_id = ? AND question_number = ?
                """,
                (md_test.study4_test_id, question.question_number),
            ).fetchone()
            prompt_html = question.html_value
            prompt_text = question.text
            asset_urls = json.dumps(question.assets, ensure_ascii=False)
            source = "datamd"
            if existing_question:
                prompt_html = existing_question["prompt_html"] or prompt_html
                prompt_text = existing_question["prompt_text"] or prompt_text
                asset_urls = existing_question["asset_urls"] or asset_urls
                source = (
                    "study4_authenticated+datamd"
                    if (existing_question["source"] or "").startswith("study4")
                    else "datamd"
                )

            conn.execute(
                """
                INSERT INTO toeic_sw_writing_questions (
                    study4_test_id, study4_part_id, question_number,
                    prompt_html, prompt_text, asset_urls, source,
                    markdown_heading, markdown_text, markdown_html, markdown_source_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(study4_test_id, question_number) DO UPDATE SET
                    study4_part_id = excluded.study4_part_id,
                    prompt_html = excluded.prompt_html,
                    prompt_text = excluded.prompt_text,
                    asset_urls = excluded.asset_urls,
                    source = excluded.source,
                    markdown_heading = excluded.markdown_heading,
                    markdown_text = excluded.markdown_text,
                    markdown_html = excluded.markdown_html,
                    markdown_source_path = excluded.markdown_source_path
                """,
                (
                    md_test.study4_test_id,
                    part_id,
                    question.question_number,
                    prompt_html,
                    prompt_text,
                    asset_urls,
                    source,
                    question.heading,
                    question.text,
                    question.html_value,
                    str(md_test.path),
                ),
            )

    conn.execute(
        """
        INSERT INTO crawl_runs (source_url, crawled_at, status, note)
        VALUES (?, ?, ?, ?)
        """,
        (
            "datamd",
            imported_at,
            "complete",
            f"Imported {len(markdown_tests)} Markdown files from datamd.",
        ),
    )


def migrate(db_path: Path, datamd_dir: Path, make_backup: bool) -> Path | None:
    backup_path = None
    if make_backup:
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = db_path.with_suffix(f".backup-{timestamp}.db")
        shutil.copy2(db_path, backup_path)

    markdown_tests = sorted(
        (parse_markdown_file(path) for path in datamd_dir.glob("sw-writing-test-*-id_*.md")),
        key=lambda item: item.test_number,
    )
    if not markdown_tests:
        raise RuntimeError(f"No Markdown files found in {datamd_dir}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = OFF")
        existing_runs = read_rows(conn, "crawl_runs")
        existing_tests = read_rows(conn, "toeic_sw_writing_tests")
        existing_parts = read_rows(conn, "toeic_sw_writing_parts")
        existing_questions = read_rows(conn, "toeic_sw_writing_questions")

        conn.execute("BEGIN")
        create_clean_schema(conn)
        restore_existing_data(
            conn,
            existing_tests,
            existing_parts,
            existing_questions,
            existing_runs,
        )
        import_markdown(conn, markdown_tests)
        conn.execute("PRAGMA foreign_keys = ON")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        conn.commit()

    return backup_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/database.db"))
    parser.add_argument("--datamd", type=Path, default=Path("datamd"))
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    backup = migrate(args.db, args.datamd, make_backup=not args.no_backup)
    print(f"Imported Markdown from {args.datamd} into {args.db}")
    if backup:
        print(f"Backup created at {backup}")


if __name__ == "__main__":
    main()
