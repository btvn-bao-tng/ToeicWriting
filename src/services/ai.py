from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException

from ..config import AI_API_KEY, AI_BASE_URL, AI_MODEL


def sse_event(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }


async def ai_chat(system_prompt: str, user_content: Any) -> str:
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

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{AI_BASE_URL}/chat/completions",
                json=payload,
                headers=_headers(),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not reach AI server: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"AI server error: {response.text}",
        )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail=f"Unexpected AI response: {response.text}"
        ) from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected AI response: {data}") from exc


async def ai_chat_stream(system_prompt: str, user_content: Any):
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{AI_BASE_URL}/chat/completions",
                json=payload,
                headers=_headers(),
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    yield sse_event(
                        "error",
                        {
                            "detail": "AI server error: "
                            + body.decode("utf-8", errors="replace")
                        },
                    )
                    return

                async for raw_line in response.aiter_lines():
                    line = raw_line.strip()
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
    except httpx.HTTPError as exc:
        yield sse_event("error", {"detail": f"Could not reach AI server: {exc}"})
