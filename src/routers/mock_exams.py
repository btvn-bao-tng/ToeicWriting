from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import AI_API_KEY, AI_MODEL
from ..database import db
from ..deps import db_session, require_user_with_db
from ..repositories import mock_exams as mock_exams_repo
from ..schemas import MockExamCreate, MockExamDraftRequest, MockExamResponse, ScoreRequest
from ..services import ai as ai_service
from ..services import content as content_service
from ..services import scoring as scoring_service
from ..services.mock_scoring import MAX_SCORES, compute_mock_result, convert_score, parse_score_10

router = APIRouter()


def _visible_questions(payload: dict[str, Any], selected_part: str) -> list[dict[str, Any]]:
    questions = payload.get("questions") or []
    if selected_part == "all":
        return questions
    parts = payload.get("parts") or []
    target = str(selected_part)
    part = next(
        (p for p in parts if str(p.get("sort_order")) == target), None
    )
    if part is None:
        return []
    return [q for q in questions if q.get("study4_part_id") == part.get("study4_part_id")]


@router.post("/api/mock-exams", response_model=MockExamResponse)
async def create_mock_exam(
    request: MockExamCreate,
    user: dict[str, Any] = Depends(require_user_with_db),
    conn: Session = Depends(db_session),
) -> MockExamResponse:
    payload = await run_in_threadpool(content_service.get_test_payload, request.study4_test_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Test not found")

    def _create() -> dict[str, Any] | None:
        exam_id = mock_exams_repo.insert_exam(
            conn, user["id"], request.study4_test_id, request.selected_part
        )
        conn.commit()
        return mock_exams_repo.get_exam(conn, user["id"], exam_id)

    exam = await run_in_threadpool(_create)
    if exam is None:
        raise HTTPException(status_code=500, detail="Failed to create mock exam")
    return exam


@router.get("/api/mock-exams")
async def list_mock_exams(
    user: dict[str, Any] = Depends(require_user_with_db),
    conn: Session = Depends(db_session),
) -> list[dict[str, Any]]:
    def _list() -> list[dict[str, Any]]:
        exams = mock_exams_repo.list_exams(conn, user["id"])
        tests = {t["study4_test_id"]: t for t in content_service.list_tests()}
        for exam in exams:
            test = tests.get(exam["study4_test_id"], {})
            exam["test_title"] = test.get("title", "")
            exam["duration_minutes"] = test.get("duration_minutes")
        return exams

    return await run_in_threadpool(_list)


@router.get("/api/mock-exams/{mock_exam_id}")
async def get_mock_exam(
    mock_exam_id: int,
    user: dict[str, Any] = Depends(require_user_with_db),
    conn: Session = Depends(db_session),
) -> dict[str, Any]:
    exam = await run_in_threadpool(mock_exams_repo.get_exam, conn, user["id"], mock_exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Mock exam not found")

    payload = await run_in_threadpool(content_service.get_test_payload, exam["study4_test_id"])
    if payload is None:
        raise HTTPException(status_code=404, detail="Test not found")

    def _assemble() -> dict[str, Any]:
        mock_exams_repo.normalize_streaming(conn, mock_exam_id)
        drafts = mock_exams_repo.list_drafts(conn, mock_exam_id)
        attempts = mock_exams_repo.list_attempts(conn, mock_exam_id)
        result = compute_mock_result(attempts)

        visible = _visible_questions(payload, exam["selected_part"])
        draft_map = {d["question_number"]: d["body"] for d in drafts}
        attempt_map = {a["question_number"]: a for a in attempts}

        questions_out = []
        for question in visible:
            number = question["question_number"]
            attempt = attempt_map.get(number)
            questions_out.append(
                {
                    **question,
                    "draft": draft_map.get(number, ""),
                    "attempt": attempt,
                    "converted_score": attempt.get("converted_score") if attempt else None,
                    "max_score": attempt.get("max_score") if attempt else None,
                }
            )

        test = payload.get("test", {})
        parts = payload.get("parts", [])
        selected_part_label = (
            "Entire test" if exam["selected_part"] == "all" else f"Part {exam['selected_part']}"
        )

        return {
            "exam": exam,
            "test": test,
            "parts": parts,
            "selected_part_label": selected_part_label,
            "questions": questions_out,
            "drafts": drafts,
            "attempts": attempts,
            "result": result,
        }

    return await run_in_threadpool(_assemble)


@router.put("/api/mock-exams/{mock_exam_id}/draft")
async def save_mock_exam_draft(
    mock_exam_id: int,
    body: MockExamDraftRequest,
    user: dict[str, Any] = Depends(require_user_with_db),
    conn: Session = Depends(db_session),
) -> dict[str, bool]:
    exam = await run_in_threadpool(mock_exams_repo.get_exam, conn, user["id"], mock_exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Mock exam not found")
    if exam["status"] == "completed":
        raise HTTPException(status_code=400, detail="Mock exam is already completed")

    await run_in_threadpool(
        mock_exams_repo.upsert_draft, conn, mock_exam_id, body.question_number, body.body
    )
    return {"ok": True}


@router.post("/api/mock-exams/{mock_exam_id}/submit")
async def submit_mock_exam(
    mock_exam_id: int,
    user: dict[str, Any] = Depends(require_user_with_db),
    conn: Session = Depends(db_session),
) -> StreamingResponse:
    if not AI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AI_API_KEY is not set. Start the server with AI_API_KEY in the environment.",
        )

    exam = await run_in_threadpool(mock_exams_repo.get_exam, conn, user["id"], mock_exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Mock exam not found")
    if exam["status"] == "completed":
        raise HTTPException(status_code=400, detail="Mock exam is already completed")

    payload = await run_in_threadpool(content_service.get_test_payload, exam["study4_test_id"])
    if payload is None:
        raise HTTPException(status_code=404, detail="Test not found")

    visible = _visible_questions(payload, exam["selected_part"])
    if not visible:
        raise HTTPException(status_code=400, detail="No questions in selected scope")

    total_questions = len(visible)
    study4_test_id = exam["study4_test_id"]
    selected_part = exam["selected_part"]

    def stream_score():
        with db() as score_conn:
            drafts = mock_exams_repo.list_drafts(score_conn, mock_exam_id)
            draft_map = {d["question_number"]: d["body"] for d in drafts}

        errors: list[dict[str, Any]] = []

        yield ai_service.sse_event(
            "start", {"mock_exam_id": mock_exam_id, "total_questions": total_questions}
        )

        for question in visible:
            number = question["question_number"]
            answer = draft_map.get(number, "").strip()
            max_score = MAX_SCORES.get(number, 3)

            with db() as score_conn:
                attempt_id = mock_exams_repo.insert_attempt(
                    score_conn, mock_exam_id, number, answer, "streaming", AI_MODEL
                )
                score_conn.commit()

            yield ai_service.sse_event("question_start", {"question_number": number})

            if not answer:
                detail = "Answer is empty"
                with db() as score_conn:
                    mock_exams_repo.mark_error(score_conn, attempt_id, detail, max_score)
                    score_conn.commit()
                errors.append({"question_number": number, "detail": detail})
                yield ai_service.sse_event(
                    "question_error",
                    {
                        "question_number": number,
                        "detail": detail,
                        "converted_score": 0.0,
                        "max_score": max_score,
                    },
                )
                continue

            try:
                _part_order, _question_number, system_prompt, user_prompt = scoring_service.score_context(
                    ScoreRequest(
                        study4_test_id=study4_test_id,
                        question_number=number,
                        answer=answer,
                    )
                )

                full_text = ""
                for event in ai_service.ai_chat_stream(system_prompt, user_prompt):
                    if "event: done" in event:
                        continue
                    if "event: error" in event:
                        try:
                            data_line = event.split("data:", 1)[1].strip()
                            detail = json.loads(data_line).get("detail", "Scoring failed.")
                        except (IndexError, json.JSONDecodeError):
                            detail = "Scoring failed."
                        raise RuntimeError(detail)
                    if "event: delta" in event:
                        try:
                            data_line = event.split("data:", 1)[1].strip()
                            delta = json.loads(data_line).get("content", "")
                        except (IndexError, json.JSONDecodeError):
                            delta = ""
                        full_text += delta
                        yield ai_service.sse_event(
                            "delta", {"question_number": number, "content": delta}
                        )

                score_text = full_text
                score_10 = parse_score_10(score_text)
                converted_score: float | None = None
                computed_max_score = max_score
                if score_10 is not None:
                    converted_score, computed_max_score = convert_score(number, score_10)

                with db() as score_conn:
                    mock_exams_repo.mark_visible(
                        score_conn,
                        attempt_id,
                        score_text,
                        score_10,
                        converted_score,
                        computed_max_score,
                    )
                    score_conn.commit()
                yield ai_service.sse_event(
                    "question_done",
                    {
                        "question_number": number,
                        "score_10": score_10,
                        "converted_score": converted_score,
                        "max_score": computed_max_score,
                    },
                )
            except Exception as exc:
                detail = str(exc)
                with db() as score_conn:
                    mock_exams_repo.mark_error(score_conn, attempt_id, detail, max_score)
                    score_conn.commit()
                errors.append({"question_number": number, "detail": detail})
                yield ai_service.sse_event(
                    "question_error",
                    {
                        "question_number": number,
                        "detail": detail,
                        "converted_score": 0.0,
                        "max_score": max_score,
                    },
                )

        with db() as score_conn:
            persisted_attempts = mock_exams_repo.list_attempts(score_conn, mock_exam_id)
            result = compute_mock_result(persisted_attempts)
            mock_exams_repo.complete_exam(
                score_conn, mock_exam_id, result["raw_score"], result["scaled_score"]
            )
            score_conn.commit()
            exam_result = mock_exams_repo.get_exam(score_conn, user["id"], mock_exam_id)

        yield ai_service.sse_event(
            "complete",
            {
                "exam": exam_result,
                "result": result,
                "errors": errors,
            },
        )
        yield ai_service.sse_event("done", {})

    return StreamingResponse(
        stream_score(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
