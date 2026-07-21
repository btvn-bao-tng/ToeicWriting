from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

import edge_tts

from ..config import ROOT

logger = logging.getLogger("uvicorn.error")

VOICES = {
    "us": "en-US-AriaNeural",
    "uk": "en-GB-LibbyNeural",
}

DEFAULT_ACCENT = "us"
MAX_TEXT_LENGTH = 500

CACHE_DIR = ROOT / "data" / "tts_cache"


def resolve_accent(accent: str | None) -> str:
    return accent if accent in VOICES else DEFAULT_ACCENT


def resolve_voice(accent: str | None) -> str:
    return VOICES[resolve_accent(accent)]


def cache_path_for(accent: str, text: str) -> Path:
    key = hashlib.sha1(f"{accent}|{text}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.mp3"


async def _synthesize(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            chunks.append(chunk["data"])
    if not chunks:
        raise RuntimeError("Edge TTS returned no audio")
    return b"".join(chunks)


def _cache_or_synthesize(accent: str, text: str) -> tuple[bytes, Path, bool]:
    cache_file = cache_path_for(accent, text)
    if cache_file.exists():
        return cache_file.read_bytes(), cache_file, True
    return b"", cache_file, False


async def synthesize_async(text: str, accent: str | None = None) -> bytes:
    """Return cached MP3 bytes for the text/accent, synthesizing on first use."""
    accent = resolve_accent(accent)
    cached, cache_file, hit = _cache_or_synthesize(accent, text)
    if hit:
        return cached

    voice = VOICES[accent]
    data = await _synthesize(text, voice)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(data)
    except OSError as error:
        logger.warning("Could not cache TTS audio: %s", error)
    return data


def synthesize(text: str, accent: str | None = None) -> bytes:
    """Sync wrapper for CLI/non-async use."""
    return asyncio.run(synthesize_async(text, accent))
