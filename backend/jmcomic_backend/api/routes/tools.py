"""工具 API：Waifu2x 超分、DNS 解析、代理测试."""

from __future__ import annotations

import asyncio
import socket
import time
from typing import Any

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from jmcomic_backend.api.deps import AppSettingsDep
from jmcomic_backend.services import waifu2x_service
from jmcomic_backend.services.waifu2x_service import Waifu2xError

router = APIRouter(prefix="/tools", tags=["tools"])

PROXY_TEST_URL = "https://www.google.com/generate_204"


def _guess_image_type(data: bytes, filename: str) -> str:
    """按结果字节魔数识别真实格式；sr_vulkan 输出格式与输入后缀不一定一致."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:2] == b"BM":
        return "image/bmp"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext in ("png", "webp", "bmp", "gif"):
        return f"image/{ext}"
    return "image/png"


@router.get("/waifu2x/status")
async def waifu2x_status() -> dict[str, Any]:
    return {"available": waifu2x_service.available()}


@router.post("/waifu2x/convert")
async def waifu2x_convert(
    file: UploadFile = File(...),
    model: int = Form(default=1),
    scale: int = Form(default=2),
    tile_size: int = Form(default=400),
) -> Response:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty image")
    try:
        result, _tick = await waifu2x_service.convert(
            data, model=model, scale=scale, tile_size=tile_size
        )
    except Waifu2xError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    media_type = _guess_image_type(result, file.filename or "")
    return Response(content=result, media_type=media_type)


class DnsBody(BaseModel):
    host: str
    port: int = 443


@router.post("/dns/resolve")
async def dns_resolve(body: DnsBody) -> dict[str, Any]:
    """解析域名 -> IP 列表（对应原项目 DNS 工具）."""

    async def _resolve() -> list[str]:
        infos = await asyncio.get_running_loop().getaddrinfo(
            body.host, body.port, proto=socket.IPPROTO_TCP
        )
        seen: list[str] = []
        for info in infos:
            ip = info[4][0]
            if ip not in seen:
                seen.append(ip)
        return seen

    try:
        ips = await asyncio.wait_for(_resolve(), timeout=10.0)
    except Exception as exc:
        return {"ok": False, "host": body.host, "ips": [], "error": str(exc)}
    if not ips:
        return {"ok": False, "host": body.host, "ips": [], "error": "未解析到任何 IP"}
    return {"ok": True, "host": body.host, "ips": ips}


@router.get("/proxy/test")
async def proxy_test(
    settings: AppSettingsDep,
    url: str = Query(default=PROXY_TEST_URL),
) -> dict[str, Any]:
    """用当前代理设置测试连通性，返回耗时（对应原项目代理测试）."""
    proxy = settings.proxy
    if not proxy.enabled:
        return {"ok": False, "error": "代理未启用，请先在设置中开启"}
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="仅支持 http(s) 协议的测试地址")

    proxy_url = ""
    for candidate in (proxy.http, proxy.https, proxy.socks5):
        if candidate:
            proxy_url = candidate
            break
    if not proxy_url:
        return {"ok": False, "error": "未配置代理地址"}

    mounts: dict[str, httpx.AsyncHTTPTransport] | None = None
    if proxy_url.startswith(("http://", "https://")):
        mounts = {"http://": httpx.AsyncHTTPTransport(proxy=proxy_url),
                  "https://": httpx.AsyncHTTPTransport(proxy=proxy_url)}
    elif proxy_url.startswith("socks5://") or proxy_url.startswith("socks5h://"):
        mounts = {"http://": httpx.AsyncHTTPTransport(proxy=proxy_url),
                  "https://": httpx.AsyncHTTPTransport(proxy=proxy_url)}
    else:
        return {"ok": False, "error": f"不支持的代理格式: {proxy_url}"}

    client = httpx.AsyncClient(mounts=mounts, timeout=15.0, follow_redirects=True)
    t0 = time.time()
    try:
        resp = await client.get(url)
        elapsed = round(time.time() - t0, 3)
        ok = resp.status_code < 400
        return {"ok": ok, "status": resp.status_code, "elapsed": elapsed,
                "error": "" if ok else f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"ok": False, "elapsed": round(time.time() - t0, 3), "error": str(exc)}
    finally:
        await client.aclose()
