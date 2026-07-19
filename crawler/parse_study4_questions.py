#!/usr/bin/env python3
"""Parse authenticated Study4 practice pages into toeic_sw_writing_questions.

Usage:
  1. Fetch each practice page while logged in to Study4, for example:
     https://study4.com/tests/5984/practice/?part=14964&part=14965&part=14966
  2. Save it as:
     /private/tmp/study4_questions/study4_questions_5984.html
  3. Run this script to import the cached authenticated pages.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


BASE_URL = "https://study4.com"


VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node | str"] = field(default_factory=list)

    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def text(self) -> str:
        chunks: list[str] = []

        def walk(node: Node | str) -> None:
            if isinstance(node, str):
                chunks.append(node)
                return
            for child in node.children:
                walk(child)

        walk(self)
        return re.sub(r"\s+", " ", html.unescape(" ".join(chunks))).strip()

    def outer_html(self) -> str:
        if self.tag == "[document]":
            return "".join(child.outer_html() if isinstance(child, Node) else html.escape(child) for child in self.children)

        attrs = "".join(
            f' {name}="{html.escape(value, quote=True)}"'
            for name, value in self.attrs.items()
        )
        if self.tag in VOID_TAGS:
            return f"<{self.tag}{attrs}>"
        inner = "".join(child.outer_html() if isinstance(child, Node) else html.escape(child) for child in self.children)
        return f"<{self.tag}{attrs}>{inner}</{self.tag}>"

    def find_all(self, predicate) -> list["Node"]:
        matches: list[Node] = []

        def walk(node: Node) -> None:
            if predicate(node):
                matches.append(node)
            for child in node.children:
                if isinstance(child, Node):
                    walk(child)

        walk(self)
        return matches


class TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = Node("[document]")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag.lower(), {name.lower(): value or "" for name, value in attrs})
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)

    def handle_entityref(self, name: str) -> None:
        self.stack[-1].children.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.stack[-1].children.append(f"&#{name};")


def parse_tree(html_text: str) -> Node:
    parser = TreeParser()
    parser.feed(html_text)
    return parser.root


def has_class_fragment(node: Node, fragment: str) -> bool:
    return any(fragment in class_name for class_name in node.classes())


def is_login_page(html_text: str) -> bool:
    return (
        "auth-box-wrapper" in html_text
        or re.search(r"<link[^>]+canonical[^>]+/login/", html_text, re.IGNORECASE) is not None
        or "/oauth/login/" in html_text
    )


def question_nodes(root: Node) -> list[Node]:
    item_wrappers = root.find_all(
        lambda node: (
            "question-item-wrapper" in node.classes()
            or has_class_fragment(node, "question-item-wrapper")
        )
    )
    if item_wrappers:
        return item_wrappers

    candidates = root.find_all(
        lambda node: (
            "question-wrapper" in node.classes()
            or "question-item" in node.classes()
            or has_class_fragment(node, "question-wrapper")
            or ("data-question-id" in node.attrs)
        )
    )
    seen: set[int] = set()
    unique: list[Node] = []
    for node in candidates:
        marker = id(node)
        if marker not in seen:
            seen.add(marker)
            unique.append(node)
    return unique


def first_descendant(node: Node, predicate) -> Node | None:
    for child in node.children:
        if isinstance(child, Node):
            if predicate(child):
                return child
            match = first_descendant(child, predicate)
            if match:
                return match
    return None


def collect_asset_urls(node: Node) -> list[str]:
    urls: list[str] = []
    for asset_node in node.find_all(lambda item: item.tag in {"img", "audio", "source", "video", "a"}):
        for attr in ("src", "data-src", "href"):
            url = asset_node.attrs.get(attr)
            if not url:
                continue
            if url.startswith("#") or url.startswith("javascript:"):
                continue
            if any(piece in url.lower() for piece in ("/media/", "/static/", ".mp3", ".wav", ".ogg", ".jpg", ".jpeg", ".png", ".webp")):
                absolute = urljoin(BASE_URL, html.unescape(url))
                if absolute not in urls:
                    urls.append(absolute)
    return urls


def study4_question_id(node: Node) -> int | None:
    q_node = first_descendant(node, lambda item: "data-qid" in item.attrs)
    if not q_node:
        return None
    try:
        return int(q_node.attrs["data-qid"])
    except ValueError:
        return None


def question_number(node: Node, fallback: int) -> int:
    number_node = first_descendant(
        node,
        lambda item: (
            "question-number" in item.classes()
            or has_class_fragment(item, "question-number")
        ),
    )
    if number_node:
        match = re.search(r"\b(\d+)\b", number_node.text())
        if match:
            return int(match.group(1))

    for source in (node.text(),):
        for pattern in (
            r"\bQuestion\s*(\d+)\b",
            r"\bQuestions?\s*(\d+)\s*[-–]",
            r"\bCâu\s*(\d+)\b",
            r"\bquestion[_-]?number[=:\"'\s-]*(\d+)\b",
        ):
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return int(match.group(1))
    return fallback


def part_for_question(parts: list[sqlite3.Row], number: int) -> int | None:
    current = 1
    for part in parts:
        count = part["question_count"] or 0
        if current <= number < current + count:
            return part["study4_part_id"]
        current += count
    return None


def prompt_fragments(node: Node) -> tuple[str, str]:
    prompt_nodes = node.find_all(
        lambda item: (
            "context-wrapper" in item.classes()
            or has_class_fragment(item, "context-wrapper")
            or "question-content" in item.classes()
            or has_class_fragment(item, "question-content")
        )
    )
    html_parts: list[str] = []
    text_parts: list[str] = []
    for prompt_node in prompt_nodes:
        if (
            "question-content" in prompt_node.classes()
            or has_class_fragment(prompt_node, "question-content")
        ) and first_descendant(
            prompt_node,
            lambda item: (
                "question-answers" in item.classes()
                or has_class_fragment(item, "question-answers")
            ),
        ):
            continue
        text = prompt_node.text()
        if not text:
            continue
        html_value = prompt_node.outer_html()
        if html_value not in html_parts:
            html_parts.append(html_value)
        if text not in text_parts:
            text_parts.append(text)

    if not html_parts:
        return node.outer_html(), node.text()
    return "\n".join(html_parts), "\n\n".join(text_parts)


def parse_questions(html_text: str, parts: list[sqlite3.Row]) -> list[dict[str, object]]:
    if is_login_page(html_text):
        raise RuntimeError("login_required")

    root = parse_tree(html_text)
    nodes = question_nodes(root)
    if not nodes:
        raise RuntimeError("no_question_nodes_found")

    parsed: list[dict[str, object]] = []
    for index, node in enumerate(nodes, start=1):
        number = question_number(node, index)
        prompt_html, prompt_text = prompt_fragments(node)
        parsed.append(
            {
                "question_number": number,
                "study4_question_id": study4_question_id(node),
                "study4_part_id": part_for_question(parts, number),
                "prompt_html": prompt_html,
                "prompt_text": prompt_text,
                "asset_urls": json.dumps(collect_asset_urls(node), ensure_ascii=False),
            }
        )
    return parsed


def ensure_prompt_columns(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS toeic_sw_writing_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study4_test_id INTEGER NOT NULL,
            study4_part_id INTEGER,
            question_number INTEGER,
            study4_question_id INTEGER,
            prompt_html TEXT,
            prompt_text TEXT,
            asset_urls TEXT,
            answer_hint TEXT,
            FOREIGN KEY(study4_test_id) REFERENCES toeic_sw_writing_tests(study4_test_id),
            FOREIGN KEY(study4_part_id) REFERENCES toeic_sw_writing_parts(study4_part_id),
            UNIQUE(study4_test_id, question_number)
        )
        """
    )
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(toeic_sw_writing_questions)").fetchall()
    }
    if "study4_question_id" not in columns:
        conn.execute("ALTER TABLE toeic_sw_writing_questions ADD COLUMN study4_question_id INTEGER")


def import_cached_pages(db_path: Path, cache_dir: Path, only_placeholders: bool = False) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        ensure_prompt_columns(conn)

        placeholder_filter = """
            WHERE EXISTS (
                SELECT 1
                FROM toeic_sw_writing_questions q
                WHERE q.study4_test_id = toeic_sw_writing_tests.study4_test_id
                    AND q.question_number BETWEEN 1 AND 5
                    AND q.prompt_text LIKE 'Image %'
            )
        """ if only_placeholders else ""

        tests = conn.execute(
            f"""
            SELECT study4_test_id, test_number
            FROM toeic_sw_writing_tests
            {placeholder_filter}
            ORDER BY test_number
            """
        ).fetchall()

        imported_count = 0
        for test in tests:
            test_id = test["study4_test_id"]
            path = cache_dir / f"study4_questions_{test_id}.html"
            if not path.exists():
                print(f"missing cache for test {test['test_number']}: {path}")
                continue

            parts = conn.execute(
                """
                SELECT study4_part_id, sort_order, question_count
                FROM toeic_sw_writing_parts
                WHERE study4_test_id = ?
                ORDER BY sort_order
                """,
                (test_id,),
            ).fetchall()

            try:
                questions = parse_questions(path.read_text(encoding="utf-8", errors="replace"), parts)
            except RuntimeError as exc:
                conn.execute(
                    "UPDATE toeic_sw_writing_tests SET access_status = ? WHERE study4_test_id = ?",
                    (str(exc), test_id),
                )
                print(f"skipped test {test['test_number']}: {exc}")
                continue

            for question in questions:
                conn.execute(
                    """
                    INSERT INTO toeic_sw_writing_questions (
                        study4_test_id, study4_part_id, question_number,
                        study4_question_id, prompt_html, prompt_text, asset_urls
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(study4_test_id, question_number) DO UPDATE SET
                        study4_part_id = excluded.study4_part_id,
                        study4_question_id = excluded.study4_question_id,
                        prompt_html = excluded.prompt_html,
                        prompt_text = excluded.prompt_text,
                        asset_urls = excluded.asset_urls
                    """,
                    (
                        test_id,
                        question["study4_part_id"],
                        question["question_number"],
                        question["study4_question_id"],
                        question["prompt_html"],
                        question["prompt_text"],
                        question["asset_urls"],
                    ),
                )
            conn.execute(
                "UPDATE toeic_sw_writing_tests SET access_status = ? WHERE study4_test_id = ?",
                ("questions_crawled", test_id),
            )
            imported_count += len(questions)
            print(f"imported test {test['test_number']}: {len(questions)} questions")

        print(f"Imported {imported_count} questions into {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/database.db"))
    parser.add_argument("--cache-dir", type=Path, default=Path("/private/tmp/study4_questions"))
    parser.add_argument("--only-placeholders", action="store_true")
    args = parser.parse_args()
    import_cached_pages(args.db, args.cache_dir, only_placeholders=args.only_placeholders)


if __name__ == "__main__":
    main()
