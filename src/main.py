from __future__ import annotations

import base64
import datetime as dt
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import bcrypt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

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
MAX_IMAGE_ATTACHMENTS = int(os.getenv("MAX_IMAGE_ATTACHMENTS", "3"))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))

SESSION_SECRET_KEY = os.getenv("SECRET_KEY", "")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "tw_session")
ALLOW_SIGNUP = os.getenv("ALLOW_SIGNUP", "true").strip().lower() in ("1", "true", "yes", "on")

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
_MIN_PASSWORD = 6

if not SESSION_SECRET_KEY:
    SESSION_SECRET_KEY = secrets.token_urlsafe(48)
    print(
        "WARNING: SECRET_KEY is not set. Generated an ephemeral session key. "
        "Sessions will be invalidated on restart. Set SECRET_KEY in .env for production."
    )

app = FastAPI(title="TOEIC SW Writing Browser")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie=SESSION_COOKIE_NAME,
    same_site="lax",
)
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


def _now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


class ScoreRequest(BaseModel):
    study4_test_id: int
    question_number: int = Field(ge=1, le=8)
    answer: str


class ScoreResponse(BaseModel):
    score_text: str
    model: str
    part: int
    question_number: int
    attempt_id: int


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=_MIN_PASSWORD)


class DraftRequest(BaseModel):
    study4_test_id: int
    question_number: int = Field(ge=1, le=8)
    body: str = ""


def db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def ensure_user_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            study4_test_id INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, study4_test_id, question_number)
        );

        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            study4_test_id INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            answer TEXT NOT NULL,
            score_text TEXT NOT NULL DEFAULT '',
            score_state TEXT NOT NULL DEFAULT 'streaming',
            model TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_attempts_user_test_q
            ON attempts(user_id, study4_test_id, question_number, id);
        """
    )


@app.on_event("startup")
def _startup() -> None:
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        ensure_user_schema(conn)


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def current_user(request: Request) -> dict[str, Any] | None:
    uid = request.session.get("uid")
    if not uid:
        return None
    with db() as conn:
        row = conn.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (uid,),
        ).fetchone()
    return row_to_dict(row) if row else None


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


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


def ai_chat(system_prompt: str, user_content: Any) -> str:
    if not AI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AI_API_KEY is not set. Start the server with AI_API_KEY in the environment.",
        )

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
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


def ai_chat_stream(system_prompt: str, user_content: Any):
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
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


def guess_image_mime(url: str, content_type: str | None) -> str:
    if content_type:
        mime = content_type.split(";", 1)[0].strip().lower()
        if mime.startswith("image/"):
            return mime

    mime, _encoding = mimetypes.guess_type(url)
    return mime if mime and mime.startswith("image/") else "image/png"


def fetch_image_as_data_url(url: str) -> tuple[str | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 TOEICWriting/1.0",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type")
            content_length = response.headers.get("Content-Length")
            try:
                if content_length and int(content_length) > MAX_IMAGE_BYTES:
                    return None, f"{url} was larger than {MAX_IMAGE_BYTES} bytes"
            except ValueError:
                pass

            image_bytes = response.read(MAX_IMAGE_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"{url} could not be fetched: {exc}"

    if len(image_bytes) > MAX_IMAGE_BYTES:
        return None, f"{url} was larger than {MAX_IMAGE_BYTES} bytes"
    if not image_bytes:
        return None, f"{url} returned an empty image"

    mime = guess_image_mime(url, content_type)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{encoded}", None


def build_user_content(prompt_text: str, asset_urls: list[str]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt_text}]
    failures = []

    for index, url in enumerate(asset_urls[:MAX_IMAGE_ATTACHMENTS], start=1):
        data_url, error = fetch_image_as_data_url(url)
        if error:
            failures.append(error)
            continue

        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url,
                    "detail": "high",
                },
            }
        )
        content.append({"type": "text", "text": f"Attached image {index}: {url}"})

    if len(asset_urls) > MAX_IMAGE_ATTACHMENTS:
        failures.append(f"{len(asset_urls) - MAX_IMAGE_ATTACHMENTS} image(s) were skipped by MAX_IMAGE_ATTACHMENTS")
    if failures:
        content.append({"type": "text", "text": "Image fetch notes:\n" + "\n".join(f"- {failure}" for failure in failures)})

    return content


def score_context(request: ScoreRequest) -> tuple[int, int, str, Any]:
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
            "If image attachments are present, use them as the primary visual evidence for evaluating the answer.",
            f"User answer:\n{answer}",
        ]
    )
    return part_order, int(row["question_number"]), system_prompt_for_part(part_order), build_user_content(user_prompt, assets)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_PATH, headers={"Cache-Control": "no-store"})


@app.get("/api/tests")
def list_tests(user: dict[str, Any] = Depends(require_user)) -> list[dict[str, Any]]:
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
def get_test(study4_test_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
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


def _normalize_streaming_attempts(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute(
        """
        UPDATE attempts
        SET score_state = 'error',
            score_text = COALESCE(NULLIF(score_text, ''), 'Scoring was interrupted.'),
            updated_at = ?
        WHERE user_id = ?
            AND score_state = 'streaming'
            AND score_text = ''
        """,
        (_now(), user_id),
    )


@app.post("/api/auth/register")
def register(body: AuthRequest, request: Request) -> dict[str, Any]:
    if not ALLOW_SIGNUP:
        raise HTTPException(status_code=403, detail="Sign-up is disabled on this server.")
    if not _USERNAME_RE.match(body.username):
        raise HTTPException(status_code=400, detail="Username must be 3-32 chars (A-Z, a-z, 0-9, ., _, -).")

    password_hash = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    now = _now()
    with db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (body.username, password_hash, now),
            )
            conn.commit()
            uid = cursor.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="That username is already taken.")

    request.session["uid"] = uid
    return {"id": uid, "username": body.username}


@app.post("/api/auth/login")
def login(body: AuthRequest, request: Request) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (body.username,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    try:
        ok = bcrypt.checkpw(body.password.encode("utf-8"), row["password_hash"].encode("ascii"))
    except ValueError:
        ok = False
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    request.session["uid"] = row["id"]
    return {"id": row["id"], "username": row["username"]}


@app.post("/api/auth/logout")
def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user["id"], "username": user["username"]}


@app.get("/api/progress")
def get_progress(study4_test_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    with db() as conn:
        _normalize_streaming_attempts(conn, user["id"])
        draft_rows = conn.execute(
            """
            SELECT question_number, body
            FROM drafts
            WHERE user_id = ? AND study4_test_id = ?
            """,
            (user["id"], study4_test_id),
        ).fetchall()
        attempt_rows = conn.execute(
            """
            SELECT id, question_number, answer, score_text, score_state, model, created_at
            FROM attempts
            WHERE user_id = ? AND study4_test_id = ?
            ORDER BY question_number, id
            """,
            (user["id"], study4_test_id),
        ).fetchall()

    return {
        "drafts": [
            {"question_number": r["question_number"], "body": r["body"]}
            for r in draft_rows
        ],
        "attempts": [row_to_dict(r) for r in attempt_rows],
    }


@app.put("/api/draft")
def put_draft(body: DraftRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, bool]:
    now = _now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO drafts (user_id, study4_test_id, question_number, body, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, study4_test_id, question_number) DO UPDATE SET
                body = excluded.body,
                updated_at = excluded.updated_at
            """,
            (user["id"], body.study4_test_id, body.question_number, body.body, now),
        )
        conn.commit()
    return {"ok": True}


@app.delete("/api/progress")
def delete_progress(
    study4_test_id: int,
    question_number: int,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, bool]:
    with db() as conn:
        conn.execute(
            "DELETE FROM drafts WHERE user_id = ? AND study4_test_id = ? AND question_number = ?",
            (user["id"], study4_test_id, question_number),
        )
        conn.execute(
            "DELETE FROM attempts WHERE user_id = ? AND study4_test_id = ? AND question_number = ?",
            (user["id"], study4_test_id, question_number),
        )
        conn.commit()
    return {"ok": True}


@app.post("/api/score", response_model=ScoreResponse)
def score_answer(
    request: ScoreRequest,
    user: dict[str, Any] = Depends(require_user),
) -> ScoreResponse:
    part_order, question_number, system_prompt, user_prompt = score_context(request)
    score_text = ai_chat(system_prompt, user_prompt)
    now = _now()
    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO attempts (
                user_id, study4_test_id, question_number, answer,
                score_text, score_state, model, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'visible', ?, ?, ?)
            """,
            (user["id"], request.study4_test_id, request.question_number, request.answer,
             score_text, AI_MODEL, now, now),
        )
        conn.commit()
        attempt_id = cursor.lastrowid
    return ScoreResponse(
        score_text=score_text,
        model=AI_MODEL,
        part=part_order,
        question_number=question_number,
        attempt_id=attempt_id,
    )


@app.post("/api/score/stream")
def score_answer_stream(
    request: ScoreRequest,
    user: dict[str, Any] = Depends(require_user),
) -> StreamingResponse:
    if not AI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AI_API_KEY is not set. Start the server with AI_API_KEY in the environment.",
        )

    _part_order, _question_number, system_prompt, user_prompt = score_context(request)

    def stream_and_persist():
        now = _now()
        with db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO attempts (
                    user_id, study4_test_id, question_number, answer,
                    score_text, score_state, model, created_at, updated_at
                ) VALUES (?, ?, ?, ?, '', 'streaming', ?, ?, ?)
                """,
                (user["id"], request.study4_test_id, request.question_number,
                 request.answer, AI_MODEL, now, now),
            )
            conn.commit()
            attempt_id = cursor.lastrowid

        yield sse_event("start", {"attempt_id": attempt_id})

        full_text = ""
        for event in ai_chat_stream(system_prompt, user_prompt):
            if "event: done" in event:
                continue
            if "event: error" in event:
                try:
                    data_line = event.split("data:", 1)[1].strip()
                    detail = json.loads(data_line).get("detail", "Scoring failed.")
                except (IndexError, json.JSONDecodeError):
                    detail = "Scoring failed."
                with db() as conn:
                    conn.execute(
                        """
                        UPDATE attempts
                        SET score_state = 'error',
                            score_text = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (detail, _now(), attempt_id),
                    )
                    conn.commit()
                yield sse_event("error", {"detail": detail, "attempt_id": attempt_id})
                return
            if "event: delta" in event:
                try:
                    data_line = event.split("data:", 1)[1].strip()
                    full_text += json.loads(data_line).get("content", "")
                except (IndexError, json.JSONDecodeError):
                    pass
            yield event

        with db() as conn:
            conn.execute(
                """
                UPDATE attempts
                SET score_text = ?, score_state = 'visible', updated_at = ?
                WHERE id = ?
                """,
                (full_text, _now(), attempt_id),
            )
            conn.commit()
        yield sse_event("done", {"attempt_id": attempt_id})

    return StreamingResponse(
        stream_and_persist(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": str(DB_PATH)}
