from __future__ import annotations

import datetime as dt
import json


def now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def decode_assets(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []
