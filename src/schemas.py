from __future__ import annotations

from pydantic import BaseModel, Field

from .config import MIN_PASSWORD


class ScoreRequest(BaseModel):
    study4_test_id: int
    question_number: int = Field(ge=1, le=8)
    answer: str = Field(max_length=20000)


class ScoreResponse(BaseModel):
    score_text: str
    model: str
    part: int
    question_number: int
    attempt_id: int


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=MIN_PASSWORD)


class DraftRequest(BaseModel):
    study4_test_id: int
    question_number: int = Field(ge=1, le=8)
    body: str = ""


class MockExamCreate(BaseModel):
    study4_test_id: int
    selected_part: str = Field(pattern=r"^(all|[123])$")


class MockExamResponse(BaseModel):
    id: int
    study4_test_id: int
    selected_part: str
    status: str
    raw_score: float | None
    scaled_score: int | None
    created_at: str
    completed_at: str | None


class MockExamDraftRequest(BaseModel):
    question_number: int = Field(ge=1, le=8)
    body: str = ""


class VocabRequest(BaseModel):
    attempt_id: int | None = None
    study4_test_id: int
    question_number: int = Field(ge=1, le=8)


class VocabDetailRequest(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    topic: str = Field(default="", max_length=80)
    main_image_url: str | None = None
    question_prompt: str = Field(default="", max_length=2000)


class RevisionItemRequest(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    topic: str = Field(default="", max_length=80)
    image: dict | None = None
    part_of_speech: str | None = None
    ipa: str | None = None
    meaning: str | None = None
    example: str | None = None
    vietnamese_meaning: str | None = None
    synonyms: list[str] | None = None


class ReviewStateRequest(BaseModel):
    reviewed: bool = True
