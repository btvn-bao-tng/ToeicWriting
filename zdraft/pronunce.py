 
import json
import os
from typing import Any
from urllib.parse import quote

import httpx


BASE_URL = (
    "https://www.dictionaryapi.com"
    "/api/v3/references/learners/json"
)


def create_audio_url(audio_name: str) -> str:
    """
    Convert Merriam-Webster's audio filename into a playable MP3 URL.
    """
    if audio_name.startswith("bix"):
        subdirectory = "bix"
    elif audio_name.startswith("gg"):
        subdirectory = "gg"
    elif not audio_name[0].isalpha():
        subdirectory = "number"
    else:
        subdirectory = audio_name[0].lower()

    return (
        "https://media.merriam-webster.com/audio/prons/"
        f"en/us/mp3/{subdirectory}/{audio_name}.mp3"
    )


async def look_up_word(word: str) -> dict[str, Any]:
    api_key = "DiLSjYHWBx5jcJDNh2Nc1kbN2oUgXjFpnBkt0QmDJU8KabzhJWOXjCWq"
    if not api_key:
        raise RuntimeError(
            "MERRIAM_WEBSTER_KEY is not configured. "
            "Request a Learner's Dictionary key at https://www.dictionaryapi.com/ "
            "and export MERRIAM_WEBSTER_KEY in your environment."
        )

    url = f"{BASE_URL}/{quote(word.strip())}"

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            url,
            params={"key": api_key},
        )
        response.raise_for_status()

        text = response.text or ""
        if not text.strip():
            return {"found": False, "word": word, "suggestions": [], "error": "Empty response"}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {
                "found": False,
                "word": word,
                "suggestions": [],
                "error": "Non-JSON response",
            }

    if not data:
        return {
            "found": False,
            "word": word,
            "suggestions": [],
        }

    # A string list can be handled as spelling suggestions.
    if isinstance(data[0], str):
        return {
            "found": False,
            "word": word,
            "suggestions": data,
        }

    entry = data[0]

    pronunciation = None
    audio_url = None

    pronunciations = entry.get("hwi", {}).get("prs", [])

    if pronunciations:
        pronunciation = pronunciations[0].get("ipa")

        audio_name = (
            pronunciations[0]
            .get("sound", {})
            .get("audio")
        )

        if audio_name:
            audio_url = create_audio_url(audio_name)

    headword = (
        entry.get("hwi", {})
        .get("hw", entry.get("meta", {}).get("id", word))
        .replace("*", "")
    )

    return {
        "found": True,
        "word": headword,
        "part_of_speech": entry.get("fl"),
        "ipa": pronunciation,
        "audio_url": audio_url,
        "definitions": entry.get("shortdef", []),
        "stems": entry.get("meta", {}).get("stems", []),
    }


import asyncio


async def main() -> None:
    result = await look_up_word("pedestrian")
    print(json.dumps(result, indent=2, ensure_ascii=False))


asyncio.run(main())
