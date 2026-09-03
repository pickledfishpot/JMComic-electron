"""首页推荐 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from jmcomic_backend.services.jm_client import JmClient

router = APIRouter(prefix="/index", tags=["index"])


@router.get("")
async def get_index(page: str = "0") -> dict[str, Any]:
    async with JmClient() as client:
        data = await client.get_index(page)
    return {"page": page, "sections": data}
