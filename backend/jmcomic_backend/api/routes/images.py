"""图片代理 API.

前端通过 /api/images/{path} 请求图片，后端转发到远端图床并返回.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from jmcomic_backend.services.jm_client import JmClient

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{path:path}")
async def proxy_image(path: str) -> Response:
    async with JmClient() as client:
        try:
            data, content_type = await client.fetch_image(path)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch image: {exc}") from exc
    return Response(content=data, media_type=content_type)
