from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - app still supports real environment vars.
    load_dotenv = None


ROOT = Path(__file__).resolve().parents[1]
if load_dotenv:
    load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "data" / "database.db"
INDEX_PATH = Path(__file__).resolve().parent / "index.html"
STATIC_PATH = Path(__file__).resolve().parent / "static"
SYSTEM_PROMPT_DIR = ROOT / "data" / "system_prompt"
AI_BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:20128/v1").rstrip("/")
AI_MODEL = os.getenv("AI_MODEL", "cx/gpt-5.4")
AI_API_KEY = os.getenv("AI_API_KEY", "")

app = FastAPI(title="TOEIC SW Writing Browser")
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


class ScoreRequest(BaseModel):
    study4_test_id: int
    question_number: int = Field(ge=1, le=8)
    answer: str


class ScoreResponse(BaseModel):
    score_text: str
    model: str
    part: int
    question_number: int


def db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def decode_assets(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def system_prompt_for_part(part_order: int) -> str:
    prompt_path = SYSTEM_PROMPT_DIR / f"part{part_order}.md"
    prompt = prompt_path.read_text(encoding="utf-8", errors="replace").strip() if prompt_path.exists() else ""
    if prompt:
        return prompt

    return (
        f"You are an expert TOEIC Writing Part {part_order} examiner and coach. "
        "Evaluate the user's answer for the given TOEIC Writing prompt. "
        "Give a score, explain strengths and errors, provide a corrected response, "
        "and include concise improvement advice."
    )


def ai_chat(system_prompt: str, user_prompt: str) -> str:
    if not AI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AI_API_KEY is not set. Start the server with AI_API_KEY in the environment.",
        )

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        f"{AI_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"AI server error: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach AI server: {exc.reason}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected AI response: {data}") from exc


def sse_event(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def ai_chat_stream(system_prompt: str, user_prompt: str):
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "stream": True,
    }
    request = urllib.request.Request(
        f"{AI_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue

                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    yield sse_event("done", {})
                    return

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choice = (chunk.get("choices") or [{}])[0]
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    yield sse_event("delta", {"content": content})

            yield sse_event("done", {})
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        yield sse_event("error", {"detail": f"AI server error: {detail}"})
    except urllib.error.URLError as exc:
        yield sse_event("error", {"detail": f"Could not reach AI server: {exc.reason}"})


def score_context(request: ScoreRequest) -> tuple[int, int, str, str]:
    answer = request.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Answer is empty")

    with db() as conn:
        row = conn.execute(
            """
            SELECT
                t.title,
                q.question_number,
                q.prompt_text,
                q.prompt_html,
                q.asset_urls,
                p.sort_order AS part_order,
                p.label AS part_label
            FROM toeic_sw_writing_questions q
            JOIN toeic_sw_writing_tests t
                ON t.study4_test_id = q.study4_test_id
            LEFT JOIN toeic_sw_writing_parts p
                ON p.study4_part_id = q.study4_part_id
            WHERE q.study4_test_id = ?
                AND q.question_number = ?
            """,
            (request.study4_test_id, request.question_number),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Question not found")

    part_order = int(row["part_order"] or 1)
    assets = decode_assets(row["asset_urls"])
    user_prompt = "\n\n".join(
        [
            f"Test: {row['title']}",
            f"Part: {part_order} ({row['part_label'] or 'Unknown part'})",
            f"Question number: {row['question_number']}",
            f"Prompt text:\n{row['prompt_text'] or ''}",
            f"Prompt HTML:\n{row['prompt_html'] or ''}",
            "Image or asset URLs:\n" + ("\n".join(assets) if assets else "None"),
            f"User answer:\n{answer}",
        ]
    )
    return part_order, int(row["question_number"]), system_prompt_for_part(part_order), user_prompt


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_PATH, headers={"Cache-Control": "no-store"})


@app.get("/api/tests")
def list_tests() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                t.study4_test_id,
                t.test_number,
                t.title,
                t.url,
                t.duration_minutes,
                t.part_count,
                t.question_count,
                t.practice_count,
                t.access_status,
                COUNT(q.id) AS crawled_question_count
            FROM toeic_sw_writing_tests t
            LEFT JOIN toeic_sw_writing_questions q
                ON q.study4_test_id = t.study4_test_id
            GROUP BY t.study4_test_id
            ORDER BY t.test_number DESC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


@app.get("/api/tests/{study4_test_id}")
def get_test(study4_test_id: int) -> dict[str, Any]:
    with db() as conn:
        test = conn.execute(
            """
            SELECT
                study4_test_id,
                test_number,
                title,
                slug,
                url,
                duration_minutes,
                part_count,
                question_count,
                practice_count,
                access_status
            FROM toeic_sw_writing_tests
            WHERE study4_test_id = ?
            """,
            (study4_test_id,),
        ).fetchone()
        if test is None:
            raise HTTPException(status_code=404, detail="Test not found")

        parts = conn.execute(
            """
            SELECT study4_part_id, sort_order, label, question_count
            FROM toeic_sw_writing_parts
            WHERE study4_test_id = ?
            ORDER BY sort_order
            """,
            (study4_test_id,),
        ).fetchall()

        questions = conn.execute(
            """
            SELECT
                id,
                study4_test_id,
                study4_part_id,
                study4_question_id,
                question_number,
                prompt_html,
                prompt_text,
                asset_urls
            FROM toeic_sw_writing_questions
            WHERE study4_test_id = ?
            ORDER BY question_number
            """,
            (study4_test_id,),
        ).fetchall()

    question_dicts = []
    for row in questions:
        item = row_to_dict(row)
        item["asset_urls"] = decode_assets(item.get("asset_urls"))
        question_dicts.append(item)

    return {
        "test": row_to_dict(test),
        "parts": [row_to_dict(row) for row in parts],
        "questions": question_dicts,
    }


@app.post("/api/score", response_model=ScoreResponse)
def score_answer(request: ScoreRequest) -> ScoreResponse:
    part_order, question_number, system_prompt, user_prompt = score_context(request)
    score_text = ai_chat(system_prompt, user_prompt)
    return ScoreResponse(
        score_text=score_text,
        model=AI_MODEL,
        part=part_order,
        question_number=question_number,
    )


@app.post("/api/score/stream")
def score_answer_stream(request: ScoreRequest) -> StreamingResponse:
    if not AI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AI_API_KEY is not set. Start the server with AI_API_KEY in the environment.",
        )

    _part_order, _question_number, system_prompt, user_prompt = score_context(request)
    return StreamingResponse(
        ai_chat_stream(system_prompt, user_prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": str(DB_PATH)}
