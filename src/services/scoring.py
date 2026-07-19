from __future__ import annotations

import base64
import mimetypes
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any

from fastapi import HTTPException

from ..config import MAX_IMAGE_ATTACHMENTS, MAX_IMAGE_BYTES, SYSTEM_PROMPT_DIR
from ..schemas import ScoreRequest
from ..utils import decode_assets
from . import content as content_service


@lru_cache(maxsize=3)
def system_prompt_for_part(part_order: int) -> str:
    prompt_path = SYSTEM_PROMPT_DIR / f"part{part_order}.md"
    prompt = (
        prompt_path.read_text(encoding="utf-8", errors="replace").strip()
        if prompt_path.exists()
        else ""
    )
    if prompt:
        return prompt

    return (
        f"You are an expert TOEIC Writing Part {part_order} examiner and coach. "
        "Evaluate the user's answer for the given TOEIC Writing prompt. "
        "Give a score, explain strengths and errors, provide a corrected response, "
        "and include concise improvement advice."
    )


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
        failures.append(
            f"{len(asset_urls) - MAX_IMAGE_ATTACHMENTS} image(s) were skipped by MAX_IMAGE_ATTACHMENTS"
        )
    if failures:
        content.append(
            {
                "type": "text",
                "text": "Image fetch notes:\n" + "\n".join(f"- {failure}" for failure in failures),
            }
        )

    return content


def score_context(request: ScoreRequest) -> tuple[int, int, str, Any]:
    answer = request.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Answer is empty")

    row = content_service.find_question(request.study4_test_id, request.question_number)

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
    return (
        part_order,
        int(row["question_number"]),
        system_prompt_for_part(part_order),
        build_user_content(user_prompt, assets),
    )
