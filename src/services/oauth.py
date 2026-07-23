from __future__ import annotations

import json
import secrets
import urllib.parse
from typing import Any

import httpx
from fastapi import HTTPException, Request

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


async def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                data=data,
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Google token exchange failed: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Google token exchange failed: {response.text}",
        )
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail=f"Google token exchange failed: {exc}"
        ) from exc


async def _get_json(url: str, bearer: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {bearer}", "Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Google userinfo request failed: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Google userinfo request failed: {response.text}",
        )
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail=f"Google userinfo request failed: {exc}"
        ) from exc


async def exchange_code(code: str, redirect_uri: str) -> dict[str, Any]:
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    return await _post_form(GOOGLE_TOKEN_URL, data)


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    return await _get_json(GOOGLE_USERINFO_URL, access_token)
