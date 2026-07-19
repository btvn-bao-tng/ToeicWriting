from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError

from ..database import db
from ..deps import clear_user_cache, current_user, remember_user
from ..repositories import users as users_repo
from ..schemas import AuthRequest
from ..services import auth as auth_service
from ..services import oauth as oauth_service

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

OAUTH_REDIRECT_TARGET = "/#/tests"


def _require_google_enabled() -> None:
    if not oauth_service.google_oauth_enabled():
        raise HTTPException(
            status_code=503,
            detail="Username/password login is disabled. Google login is not configured on this server.",
        )


@router.post("/api/auth/register")
def register(body: AuthRequest, request: Request) -> dict[str, Any]:
    _require_google_enabled()
    user = auth_service.register_user(body.username, body.password)
    remember_user(request, user)
    return user


@router.post("/api/auth/login")
def login(body: AuthRequest, request: Request) -> dict[str, Any]:
    _require_google_enabled()
    user = auth_service.authenticate_user(body.username, body.password)
    remember_user(request, user)
    return user


@router.post("/api/auth/logout")
def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@router.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user["id"], "username": user["username"]}


@router.get("/api/auth/providers")
def auth_providers() -> dict[str, Any]:
    return {"google": oauth_service.google_oauth_enabled()}


@router.get("/api/auth/google/login")
def google_login(request: Request) -> RedirectResponse:
    if not oauth_service.google_oauth_enabled():
        raise HTTPException(
            status_code=503, detail="Google OAuth is not configured on this server."
        )
    state = oauth_service.new_state()
    request.session["oauth_state"] = state
    redirect_uri = oauth_service.resolve_redirect_uri(request)
    auth_url = oauth_service.build_auth_url(state, redirect_uri)
    logger.info("Google OAuth login: redirect_uri=%s", redirect_uri)
    return RedirectResponse(url=auth_url)


@router.get("/api/auth/google/callback")
def google_callback(request: Request) -> RedirectResponse:
    if not oauth_service.google_oauth_enabled():
        raise HTTPException(
            status_code=503, detail="Google OAuth is not configured on this server."
        )

    error = request.query_params.get("error")
    if error:
        raise HTTPException(status_code=400, detail=f"Google login failed: {error}")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    saved_state = request.session.pop("oauth_state", None)
    if not code or not state or state != saved_state:
        raise HTTPException(
            status_code=400, detail="Invalid OAuth state. Please try logging in again."
        )

    redirect_uri = oauth_service.resolve_redirect_uri(request)
    tokens = oauth_service.exchange_code(code, redirect_uri)
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="Google did not return an access token.")

    info = oauth_service.fetch_userinfo(access_token)
    google_id = info.get("sub")
    email = info.get("email")
    email_verified = info.get("email_verified")
    if not google_id or not email:
        raise HTTPException(
            status_code=502, detail="Google did not return a verified email."
        )
    if email_verified is False:
        raise HTTPException(
            status_code=400, detail="Your Google email is not verified."
        )

    user = None
    with db() as conn:
        user = users_repo.find_user_by_google_id(conn, google_id)
        if user:
            if user.get("email") != email:
                users_repo.update_user_email(conn, user["id"], email)
        else:
            existing = users_repo.find_user_by_email(conn, email)
            if existing:
                users_repo.link_google_id(conn, existing["id"], google_id)
                user = existing
            else:
                try:
                    uid = users_repo.insert_google_user(conn, google_id, email, email)
                    conn.commit()
                    user = users_repo.find_user_by_id(conn, uid)
                except IntegrityError:
                    conn.rollback()
                    raise HTTPException(
                        status_code=409,
                        detail="Could not create an account from this Google login.",
                    )

    if not user:
        raise HTTPException(status_code=500, detail="Google login failed.")

    clear_user_cache()
    remember_user(request, {"id": user["id"], "username": user["username"]})
    return RedirectResponse(url=OAUTH_REDIRECT_TARGET)
