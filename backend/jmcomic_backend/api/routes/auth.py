"""认证 API：登录 / 登出 / 当前用户 / 验证码 / 注册."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from jmcomic_backend.services.jm_client import JmApiError, JmClient
from jmcomic_backend.services.session import UserSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# 注册/验证码走 web 主站（原项目 GlobalConfig.Url）
WEB_BASE_URL = "https://comic18j-oomi.net"

_WEB_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.43"
    ),
}


class LoginBody(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterBody(BaseModel):
    username: str = Field(min_length=2)
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)
    passwordConfirm: str = Field(min_length=1)
    gender: str = "Male"
    verification: str = Field(min_length=1)


@router.post("/login")
async def login(body: LoginBody, request: Request) -> dict[str, Any]:
    session_mgr = request.app.state.session
    async with JmClient() as client:
        try:
            user, cookies = await client.login(body.username, body.password)
        except JmApiError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to login: {exc}") from exc
    session = UserSession(**user, cookies=cookies)
    session_mgr.save(session)
    from jmcomic_backend.services.jm_client import set_default_cookies

    set_default_cookies(cookies)
    return {"user": session.public_dict()}


@router.post("/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.app.state.session.clear()
    from jmcomic_backend.services.jm_client import set_default_cookies

    set_default_cookies({})
    return {"ok": True}


@router.get("/me")
async def get_me(request: Request) -> dict[str, Any]:
    session = request.app.state.session.get()
    return {"user": session.public_dict() if session else None}


@router.get("/captcha")
async def get_captcha(request: Request) -> Any:
    """代理 web 主站验证码图片，同时暂存验证码 cookie 供注册使用."""
    import httpx
    from fastapi.responses import Response

    session_mgr = request.app.state.session
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            resp = await client.get(
                f"{WEB_BASE_URL}/captcha", headers={**_WEB_HEADERS, "Referer": f"{WEB_BASE_URL}/signup"}
            )
            resp.raise_for_status()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch captcha: {exc}") from exc
    pending = session_mgr.get()
    cookies = dict(resp.cookies)
    if pending is None:
        session_mgr.save(UserSession(uid="", username="", cookies=cookies))
    else:
        pending.cookies.update(cookies)
        session_mgr.save(pending)
    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "image/jpeg"),
    )


@router.post("/register")
async def register(body: RegisterBody, request: Request) -> dict[str, Any]:
    """移植自原项目 RegisterReq：POST web 主站 /signup，解析 toastr 提示."""
    import httpx

    session_mgr = request.app.state.session
    pending = session_mgr.get()
    cookies = pending.cookies if pending else {}

    data = {
        "username": body.username,
        "password": body.password,
        "email": body.email,
        "verification": body.verification,
        "password_confirm": body.passwordConfirm,
        "gender": body.gender,
        "age": "on",
        "terms": "on",
        "submit_signup": "",
    }
    headers = {**_WEB_HEADERS, "referer": f"{WEB_BASE_URL}/signup"}
    async with httpx.AsyncClient(
        timeout=20.0, follow_redirects=True, cookies=cookies
    ) as client:
        try:
            resp = await client.post(
                f"{WEB_BASE_URL}/signup",
                headers=headers,
                data=data,
            )
            resp.raise_for_status()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to register: {exc}") from exc

    html = resp.text
    errors = re.findall(r"(?<=toastr\['error'\]\(\").*", html)
    if errors:
        return {"ok": False, "message": "\n".join(errors)}
    match = re.search(r"(?<=toastr\['success'\]\(\")[^\"]*", html)
    if match:
        return {"ok": True, "message": match.group()}
    return {"ok": False, "message": "注册结果未知，请稍后尝试登录"}
