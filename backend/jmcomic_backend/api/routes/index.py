"""首页推荐 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from jmcomic_backend.services.jm_client import JmClient, JmApiError

router = APIRouter(prefix="/index", tags=["index"])


@router.get("")
async def get_index(page: str = "0") -> dict[str, Any]:
    try:
        async with JmClient() as client:
            data = await client.get_index(page)
    except JmApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch index: {exc}") from exc
    return {"page": page, "sections": data}
