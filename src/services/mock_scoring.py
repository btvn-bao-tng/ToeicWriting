from __future__ import annotations

import re
from typing import Any


MAX_SCORES = {
    1: 3,
    2: 3,
    3: 3,
    4: 3,
    5: 3,
    6: 4,
    7: 4,
    8: 5,
}


def parse_score_10(score_text: str) -> float | None:
    """Extract the first 0-10 score from the LLM Markdown output.

    Expected format includes a line like `## Score\n\n7/10`.
    """
    text = score_text or ""
    # Match patterns like "## Score\n\n7/10" or "Score: 7/10" or "7/10"
    match = re.search(r"Score\s*:?\s*\n?\n?\s*(\d+(?:\.5)?)\s*/\s*10", text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    # Fallback: look for any "X/10" near the top
    match = re.search(r"(\d+(?:\.5)?)\s*/\s*10", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def convert_score(question_number: int, score_10: float) -> tuple[float, int]:
    """Convert a 0-10 practice score to the official per-question scale.

    Returns (converted_score, max_score). Half points are preserved.
    """
    max_score = MAX_SCORES.get(question_number, 3)
    ratio = max(0.0, min(10.0, score_10)) / 10.0
    converted = round(ratio * max_score * 2) / 2
    return min(converted, float(max_score)), max_score


def compute_mock_result(
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute raw and scaled scores from a list of mock-exam attempts.

    Each attempt dict should have `question_number` and either
    `converted_score`/`max_score` or `score_text`.
    """
    breakdown: list[dict[str, Any]] = []
    raw_score = 0.0
    max_raw = 0

    for attempt in attempts:
        question_number = attempt["question_number"]
        max_score = MAX_SCORES.get(question_number, 3)
        converted = attempt.get("converted_score")

        if converted is None:
            score_10 = attempt.get("score_10")
            if score_10 is None:
                score_10 = parse_score_10(attempt.get("score_text", ""))
            if score_10 is not None:
                converted, max_score = convert_score(question_number, score_10)
            else:
                converted = 0.0

        raw_score += converted
        max_raw += max_score
        breakdown.append(
            {
                "question_number": question_number,
                "score_10": attempt.get("score_10"),
                "converted_score": converted,
                "max_score": max_score,
                "score_state": attempt.get("score_state", "visible"),
            }
        )

    scaled = round((raw_score / max_raw) * 200) if max_raw else 0
    return {
        "raw_score": raw_score,
        "max_raw": max_raw,
        "scaled_score": scaled,
        "breakdown": breakdown,
    }
