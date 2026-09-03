"""书籍详情 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from jmcomic_backend.services.jm_client import JmClient

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/{book_id}")
async def get_book_detail(book_id: str) -> dict[str, Any]:
    async with JmClient() as client:
        try:
            data = await client.get_book_detail(book_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch book detail: {exc}") from exc
    return data
