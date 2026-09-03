"""本地阅读历史 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from jmcomic_backend.api.deps import HistoryStoreDep

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def list_history(
    history: HistoryStoreDep,
    page: int = 1,
    pageSize: int = 50,
) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(pageSize, 1), 200)
    result = history.list_history(limit=page_size, offset=(page - 1) * page_size)
    result["page"] = page
    result["pageSize"] = page_size
    return result


@router.delete("/{book_id}")
async def remove_history(book_id: str, history: HistoryStoreDep) -> dict[str, bool]:
    history.remove(book_id)
    return {"ok": True}
