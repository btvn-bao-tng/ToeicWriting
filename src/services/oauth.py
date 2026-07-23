from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from ..config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPES = "openid email profile"


def google_oauth_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def new_state() -> str:
    return secrets.token_urlsafe(32)


def resolve_redirect_uri(request: Request) -> str:
    if GOOGLE_REDIRECT_URI:
        return GOOGLE_REDIRECT_URI
    base = str(request.base_url)
    if not base.endswith("/"):
        base += "/"
    return f"{base}api/auth/google/callback"


def warn_redirect_uri() -> str | None:
    if google_oauth_enabled() and not GOOGLE_REDIRECT_URI:
        return (
            "GOOGLE_REDIRECT_URI is not set. The callback URL will be derived from "
            "the request Host header, which is unreliable behind a reverse proxy. "
            "Set GOOGLE_REDIRECT_URI explicitly in production."
        )
    return None


def build_auth_url(state: str, redirect_uri: str) -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise HTTPException(
            status_code=502, detail=f"Google token exchange failed: {detail}"
        )
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=502, detail=f"Google token exchange failed: {exc.reason}"
        )


def _get_json(url: str, bearer: str) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {bearer}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise HTTPException(
            status_code=502, detail=f"Google userinfo request failed: {detail}"
        )
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=502, detail=f"Google userinfo request failed: {exc.reason}"
        )


async def exchange_code(code: str, redirect_uri: str) -> dict[str, Any]:
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    return await run_in_threadpool(_post_form, GOOGLE_TOKEN_URL, data)


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    return await run_in_threadpool(_get_json, GOOGLE_USERINFO_URL, access_token)
