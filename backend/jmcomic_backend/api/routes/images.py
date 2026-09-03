"""图片代理 API.

前端通过 /api/images/{path} 请求图片，后端转发到远端图床并返回.
阅读器图片可带 ?scramble_id= 参数，后端按 JM 规则反分割后返回（结果缓存到磁盘）.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from jmcomic_backend.api.deps import ImageCacheDep
from jmcomic_backend.services.deslice import deslice_image, parse_photo_path
from jmcomic_backend.services.jm_client import JmClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{path:path}")
async def proxy_image(
    path: str,
    cache: ImageCacheDep,
    scramble_id: int | None = Query(default=None, description="JM 反分割参数，阅读器图片必传"),
) -> Response:
    identifier = f"{path}?scramble_id={scramble_id}"
    # 同一图片并发请求只拉取/反分割一次
    async with cache.lock_for(identifier):
        cached = await asyncio.to_thread(cache.get, identifier)
        if cached is not None:
            data, content_type = cached
        else:
            async with JmClient() as client:
                try:
                    data, content_type = await client.fetch_image(path)
                except Exception as exc:
                    raise HTTPException(
                        status_code=502, detail=f"Failed to fetch image: {exc}"
                    ) from exc
            if scramble_id is not None:
                photo = parse_photo_path(path)
                if photo is not None:
                    eps_id, picture_name = photo
                    try:
                        data = await asyncio.to_thread(
                            deslice_image, data, eps_id, scramble_id, picture_name
                        )
                    except Exception as exc:
                        logger.warning("deslice failed for %s: %s", path, exc)
                        raise HTTPException(
                            status_code=502, detail=f"Failed to deslice image: {exc}"
                        ) from exc
            await asyncio.to_thread(cache.set, identifier, data, content_type)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "max-age=86400"},
    )
