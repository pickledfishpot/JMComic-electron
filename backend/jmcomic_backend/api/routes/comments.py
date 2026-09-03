"""评论 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from jmcomic_backend.services.jm_client import JmClient

router = APIRouter(prefix="/books", tags=["comments"])


@router.get("/{book_id}/comments")
async def get_book_comments(
    book_id: str,
    page: int = 1,
) -> dict[str, Any]:
    async with JmClient() as client:
        try:
            data = await client.get_book_comments(book_id, page=page)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch comments: {exc}") from exc
    return {"bookId": book_id, "page": page, **data}
