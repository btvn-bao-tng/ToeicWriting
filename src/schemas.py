from __future__ import annotations

from pydantic import BaseModel, Field

from .config import MIN_PASSWORD


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
    password: str = Field(min_length=MIN_PASSWORD)


class DraftRequest(BaseModel):
    study4_test_id: int
    question_number: int = Field(ge=1, le=8)
    body: str = ""
