from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - app still supports real environment vars.
    load_dotenv = None


ROOT = Path(__file__).resolve().parents[1]
if load_dotenv:
    load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "data" / "database.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "0"))
DB_POOL_RECYCLE_SECONDS = int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800"))
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
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

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD = 6

if not SESSION_SECRET_KEY:
    SESSION_SECRET_KEY = secrets.token_urlsafe(48)
    print(
        "WARNING: SECRET_KEY is not set. Generated an ephemeral session key. "
        "Sessions will be invalidated on restart. Set SECRET_KEY in .env for production."
    )
