"""书籍详情、章节分页与阅读进度 API."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jmcomic_backend.api.deps import HistoryStoreDep
from jmcomic_backend.services.jm_client import JmClient

router = APIRouter(prefix="/books", tags=["books"])


class ProgressBody(BaseModel):
    epsIndex: int = Field(ge=0)
    pageIndex: int = Field(ge=0)
    title: str | None = Field(default=None, max_length=500)


@router.get("/{book_id}")
async def get_book_detail(book_id: str) -> dict[str, Any]:
    async with JmClient() as client:
        try:
            data = await client.get_book_detail(book_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch book detail: {exc}") from exc
    return data


@router.get("/{book_id}/eps/{eps_index}/pages")
async def get_eps_pages(book_id: str, eps_index: int) -> dict[str, Any]:
    """获取章节分页：先取书籍详情映射 epsIndex -> epsId，再并行拉分页与反分割参数."""
    async with JmClient() as client:
        try:
            detail = await client.get_book_detail(book_id)
            eps_list = detail.get("eps", []) or []
            eps = next((e for e in eps_list if int(e.get("index", -1)) == eps_index), None)
            if eps is None:
                raise HTTPException(status_code=404, detail=f"eps index {eps_index} not found")
            eps_id = str(eps["epsId"])
            pages, scramble_id = await asyncio.gather(
                client.get_chapter_pages(eps_id),
                client.get_scramble_id(eps_id),
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch eps pages: {exc}") from exc

    for page in pages:
        page["url"] = f"/api/images/{page.pop('path')}?scramble_id={scramble_id}"
    return {
        "bookId": book_id,
        "epsIndex": eps_index,
        "epsId": eps_id,
        "scrambleId": scramble_id,
        "pages": pages,
    }


@router.get("/{book_id}/progress")
async def get_reading_progress(book_id: str, history: HistoryStoreDep) -> dict[str, Any]:
    """读取阅读进度，无记录时 progress 为 null."""
    return {"bookId": book_id, "progress": history.get_progress(book_id)}


@router.put("/{book_id}/progress")
async def save_reading_progress(
    book_id: str,
    body: ProgressBody,
    history: HistoryStoreDep,
) -> dict[str, bool]:
    history.save_progress(book_id, body.epsIndex, body.pageIndex, title=body.title)
    return {"ok": True}
