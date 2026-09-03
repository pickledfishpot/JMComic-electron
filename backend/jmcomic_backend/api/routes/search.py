"""搜索 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from jmcomic_backend.services.jm_client import JmClient

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_books(
    q: str,
    page: int = 1,
    sort: str = "mr",
) -> dict[str, Any]:
    async with JmClient() as client:
        try:
            data = await client.search(q, page=page, sort=sort)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to search: {exc}") from exc
    return {"query": q, "page": page, "sort": sort, **data}
