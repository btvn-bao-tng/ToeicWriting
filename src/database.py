from __future__ import annotations

import json
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
    google_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
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


class VocabTable(Base):
    __tablename__ = "vocab_tables"
    __table_args__ = (
        UniqueConstraint("user_id", "study4_test_id", "question_number"),
        Index("idx_vocab_tables_user", "user_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    study4_test_id: Mapped[int] = mapped_column(nullable=False)
    question_number: Mapped[int] = mapped_column(nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    model: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class VocabCategory(Base):
    __tablename__ = "vocab_categories"
    __table_args__ = (
        Index("idx_vocab_categories_table", "vocab_table_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vocab_table_id: Mapped[int] = mapped_column(
        ForeignKey("vocab_tables.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )


class VocabTerm(Base):
    __tablename__ = "vocab_terms"
    __table_args__ = (
        Index("idx_vocab_terms_table", "vocab_table_id", "sort_order"),
        Index("idx_vocab_terms_category", "vocab_category_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vocab_category_id: Mapped[int] = mapped_column(
        ForeignKey("vocab_categories.id", ondelete="CASCADE"), nullable=False
    )
    vocab_table_id: Mapped[int] = mapped_column(
        ForeignKey("vocab_tables.id", ondelete="CASCADE"), nullable=False
    )
    term: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    image_url: Mapped[str | None] = mapped_column(Text)
    image_page_url: Mapped[str | None] = mapped_column(Text)
    image_photographer: Mapped[str | None] = mapped_column(Text)
    image_alt: Mapped[str | None] = mapped_column(Text)
    part_of_speech: Mapped[str | None] = mapped_column(Text)
    ipa: Mapped[str | None] = mapped_column(Text)
    meaning: Mapped[str | None] = mapped_column(Text)
    example: Mapped[str | None] = mapped_column(Text)
    vietnamese_meaning: Mapped[str | None] = mapped_column(Text)
    synonyms: Mapped[str | None] = mapped_column(Text)


def _existing_columns(conn: Session, table_name: str) -> set[str]:
    if IS_SQLITE:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}
    rows = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def _migrate() -> None:
    additions = {
        "users": [
            ("google_id", "VARCHAR UNIQUE"),
            ("email", "VARCHAR"),
        ],
        "vocab_terms": [
            ("part_of_speech", "TEXT"),
            ("ipa", "TEXT"),
            ("meaning", "TEXT"),
            ("example", "TEXT"),
            ("vietnamese_meaning", "TEXT"),
            ("synonyms", "TEXT"),
        ],
    }
    for table_name, columns in additions.items():
        with engine.begin() as conn:
            existing = _existing_columns(conn, table_name)
            for col_name, col_ddl in columns:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_ddl}"))


def _insert_normalized_vocab(conn, vocab_id: int, data: dict[str, Any]) -> None:
    categories = data.get("categories") or []
    for cat_idx, category in enumerate(categories):
        if not isinstance(category, dict):
            continue
        name = str(category.get("name") or "").strip()
        if not name:
            continue
        result = conn.execute(
            text(
                "INSERT INTO vocab_categories (vocab_table_id, name, sort_order) "
                "VALUES (:v, :n, :s) RETURNING id"
            ),
            {"v": vocab_id, "n": name, "s": cat_idx},
        )
        cat_id = result.scalar()
        items = category.get("items") or []
        for term_idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            if not term:
                continue
            image = item.get("image") if isinstance(item.get("image"), dict) else None
            conn.execute(
                text(
                    "INSERT INTO vocab_terms "
                    "(vocab_category_id, vocab_table_id, term, sort_order, "
                    "image_url, image_page_url, image_photographer, image_alt) "
                    "VALUES (:c, :v, :t, :s, :iu, :ip, :iph, :ia)"
                ),
                {
                    "c": cat_id,
                    "v": vocab_id,
                    "t": term,
                    "s": term_idx,
                    "iu": image.get("url") if image else None,
                    "ip": image.get("page_url") if image else None,
                    "iph": image.get("photographer") if image else None,
                    "ia": image.get("alt") if image else None,
                },
            )


def _migrate_vocab_payload() -> None:
    with engine.begin() as conn:
        if not _existing_columns(conn, "vocab_tables"):
            return
        cols = _existing_columns(conn, "vocab_tables")
        if "payload" not in cols:
            return
        rows = conn.execute(text("SELECT id, payload FROM vocab_tables")).all()
        for vid, payload_json in rows:
            if not payload_json:
                continue
            already = conn.execute(
                text(
                    "SELECT 1 FROM vocab_categories WHERE vocab_table_id = :v LIMIT 1"
                ),
                {"v": vid},
            ).first()
            if already:
                continue
            try:
                data = json.loads(payload_json)
            except (json.JSONDecodeError, TypeError):
                continue
            _insert_normalized_vocab(conn, vid, data)
        try:
            conn.execute(text("ALTER TABLE vocab_tables DROP COLUMN payload"))
        except Exception:
            pass


def _migrate_vocab_attempt_optional() -> None:
    if IS_SQLITE:
        return
    with engine.begin() as conn:
        if not _existing_columns(conn, "vocab_tables"):
            return
        cols = _existing_columns(conn, "vocab_tables")

        dupes = conn.execute(
            text(
                "SELECT user_id, study4_test_id, question_number, max(id) AS keep_id "
                "FROM vocab_tables GROUP BY user_id, study4_test_id, question_number "
                "HAVING count(*) > 1"
            )
        ).all()
        for user_id, test_id, q_number, keep_id in dupes:
            stale = conn.execute(
                text(
                    "SELECT id FROM vocab_tables WHERE user_id = :u "
                    "AND study4_test_id = :t AND question_number = :q AND id <> :k"
                ),
                {"u": user_id, "t": test_id, "q": q_number, "k": keep_id},
            ).all()
            stale_ids = [row[0] for row in stale]
            if stale_ids:
                conn.execute(
                    text("DELETE FROM vocab_terms WHERE vocab_table_id = ANY(:ids)"),
                    {"ids": stale_ids},
                )
                conn.execute(
                    text("DELETE FROM vocab_categories WHERE vocab_table_id = ANY(:ids)"),
                    {"ids": stale_ids},
                )
                conn.execute(text("DELETE FROM vocab_tables WHERE id = ANY(:ids)"), {"ids": stale_ids})

        if "attempt_id" in cols:
            conn.execute(text("ALTER TABLE vocab_tables ALTER COLUMN attempt_id DROP NOT NULL"))

        old_constraint = conn.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'vocab_tables'::regclass "
                "AND contype = 'u' AND conname = 'vocab_tables_attempt_id_key'"
            )
        ).first()
        if old_constraint:
            conn.execute(text("ALTER TABLE vocab_tables DROP CONSTRAINT vocab_tables_attempt_id_key"))

        new_constraint = conn.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'vocab_tables'::regclass "
                "AND contype = 'u' AND conname = 'vocab_tables_uq_user_test_q'"
            )
        ).first()
        if not new_constraint:
            conn.execute(
                text(
                    "ALTER TABLE vocab_tables ADD CONSTRAINT vocab_tables_uq_user_test_q "
                    "UNIQUE (user_id, study4_test_id, question_number)"
                )
            )


def init_db() -> None:
    if IS_SQLITE:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode = WAL")
    Base.metadata.create_all(bind=engine)
    _migrate()
    _migrate_vocab_payload()
    _migrate_vocab_attempt_optional()


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
