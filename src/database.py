from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import (
    DATABASE_URL,
    DB_MAX_OVERFLOW,
    DB_PATH,
    DB_POOL_PRE_PING,
    DB_POOL_RECYCLE_SECONDS,
    DB_POOL_SIZE,
)


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


SQLALCHEMY_DATABASE_URL = _normalize_database_url(DATABASE_URL)
IS_SQLITE = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine_args: dict[str, Any] = {"pool_pre_ping": DB_POOL_PRE_PING}
if IS_SQLITE:
    engine_args["connect_args"] = {"check_same_thread": False, "timeout": 10}
else:
    engine_args.update(
        {
            "pool_size": DB_POOL_SIZE,
            "max_overflow": DB_MAX_OVERFLOW,
            "pool_recycle": DB_POOL_RECYCLE_SECONDS,
        }
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA busy_timeout = 5000")
        cursor.close()


class Base(DeclarativeBase):
    pass


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    crawled_at: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class ToeicWritingTest(Base):
    __tablename__ = "toeic_sw_writing_tests"

    study4_test_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    test_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    duration_minutes: Mapped[int] = mapped_column(
        nullable=False, default=60, server_default="60"
    )
    part_count: Mapped[int] = mapped_column(
        nullable=False, default=3, server_default="3"
    )
    question_count: Mapped[int] = mapped_column(
        nullable=False, default=8, server_default="8"
    )
    practice_count: Mapped[int | None]
    access_status: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(
        String, nullable=False, default="datamd", server_default="datamd"
    )
    detail_html_path: Mapped[str | None] = mapped_column(Text)
    public_detail_html: Mapped[str | None] = mapped_column(Text)
    detail_fetched_at: Mapped[str | None] = mapped_column(String)
    markdown_path: Mapped[str | None] = mapped_column(Text)
    markdown_content: Mapped[str | None] = mapped_column(Text)
    markdown_imported_at: Mapped[str | None] = mapped_column(String)


class ToeicWritingPart(Base):
    __tablename__ = "toeic_sw_writing_parts"
    __table_args__ = (
        Index("idx_toeic_sw_writing_parts_test", "study4_test_id", "sort_order"),
    )

    study4_part_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    study4_test_id: Mapped[int] = mapped_column(
        ForeignKey("toeic_sw_writing_tests.study4_test_id"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    question_count: Mapped[int] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(
        String, nullable=False, default="datamd", server_default="datamd"
    )


class ToeicWritingQuestion(Base):
    __tablename__ = "toeic_sw_writing_questions"
    __table_args__ = (
        UniqueConstraint("study4_test_id", "question_number"),
        Index("idx_toeic_sw_writing_questions_test", "study4_test_id", "question_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    study4_test_id: Mapped[int] = mapped_column(
        ForeignKey("toeic_sw_writing_tests.study4_test_id"), nullable=False
    )
    study4_part_id: Mapped[int | None] = mapped_column(
        ForeignKey("toeic_sw_writing_parts.study4_part_id")
    )
    study4_question_id: Mapped[int | None]
    question_number: Mapped[int] = mapped_column(nullable=False)
    prompt_html: Mapped[str | None] = mapped_column(Text)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    asset_urls: Mapped[str | None] = mapped_column(Text)
    answer_hint: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        String, nullable=False, default="datamd", server_default="datamd"
    )
    markdown_heading: Mapped[str | None] = mapped_column(Text)
    markdown_text: Mapped[str | None] = mapped_column(Text)
    markdown_html: Mapped[str | None] = mapped_column(Text)
    markdown_source_path: Mapped[str | None] = mapped_column(Text)


class ToeicWritingSampleAnswer(Base):
    __tablename__ = "toeic_sw_writing_sample_answers"
    __table_args__ = (
        UniqueConstraint("study4_test_id", "question_number", "sample_number"),
        Index(
            "idx_toeic_sw_writing_sample_answers_question",
            "study4_test_id",
            "question_number",
            "sample_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("toeic_sw_writing_questions.id"), nullable=False
    )
    study4_test_id: Mapped[int] = mapped_column(
        ForeignKey("toeic_sw_writing_tests.study4_test_id"), nullable=False
    )
    question_number: Mapped[int] = mapped_column(nullable=False)
    sample_number: Mapped[int] = mapped_column(nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String, nullable=False, default="seed", server_default="seed"
    )
    created_at: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Draft(Base):
    __tablename__ = "drafts"
    __table_args__ = (
        UniqueConstraint("user_id", "study4_test_id", "question_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    study4_test_id: Mapped[int] = mapped_column(nullable=False)
    question_number: Mapped[int] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        Index(
            "idx_attempts_user_test_q",
            "user_id",
            "study4_test_id",
            "question_number",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    study4_test_id: Mapped[int] = mapped_column(nullable=False)
    question_number: Mapped[int] = mapped_column(nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    score_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    score_state: Mapped[str] = mapped_column(
        String, nullable=False, default="streaming", server_default="streaming"
    )
    model: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class MockExam(Base):
    __tablename__ = "mock_exams"
    __table_args__ = (
        Index("idx_mock_exams_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    study4_test_id: Mapped[int] = mapped_column(nullable=False)
    selected_part: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="in_progress", server_default="in_progress"
    )
    raw_score: Mapped[float | None] = mapped_column(nullable=True)
    scaled_score: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(nullable=True)


class MockExamDraft(Base):
    __tablename__ = "mock_exam_drafts"
    __table_args__ = (
        UniqueConstraint("mock_exam_id", "question_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mock_exam_id: Mapped[int] = mapped_column(
        ForeignKey("mock_exams.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[int] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class MockExamAttempt(Base):
    __tablename__ = "mock_exam_attempts"
    __table_args__ = (
        Index(
            "idx_mock_exam_attempts_exam_q",
            "mock_exam_id",
            "question_number",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mock_exam_id: Mapped[int] = mapped_column(
        ForeignKey("mock_exams.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[int] = mapped_column(nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    score_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    score_state: Mapped[str] = mapped_column(
        String, nullable=False, default="streaming", server_default="streaming"
    )
    score_10: Mapped[float | None] = mapped_column(nullable=True)
    converted_score: Mapped[float | None] = mapped_column(nullable=True)
    max_score: Mapped[int | None] = mapped_column(nullable=True)
    model: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


def init_db() -> None:
    if IS_SQLITE:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode = WAL")
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


db = contextmanager(get_db)
