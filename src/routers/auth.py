from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..deps import current_user
from ..schemas import AuthRequest
from ..services import auth as auth_service

router = APIRouter()


@router.post("/api/auth/register")
def register(body: AuthRequest, request: Request) -> dict[str, Any]:
    user = auth_service.register_user(body.username, body.password)
    request.session["uid"] = user["id"]
    return user


@router.post("/api/auth/login")
def login(body: AuthRequest, request: Request) -> dict[str, Any]:
    user = auth_service.authenticate_user(body.username, body.password)
    request.session["uid"] = user["id"]
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
