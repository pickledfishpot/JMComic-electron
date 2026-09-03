"""本地图库 API.

扫描 data_dir/downloads 与设置中的 local.dirs，提供书籍列表、章节分页、
本地图片读取与阅读进度（进度复用 read_history 表，book_id 加 local: 前缀）.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from jmcomic_backend.api.deps import (
    AppPathsDep,
    AppSettingsDep,
    HistoryStoreDep,
    LocalLibraryDep,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/local", tags=["local"])

PROGRESS_PREFIX = "local:"


def _all_roots(paths: AppPathsDep, settings: AppSettingsDep) -> list[Path]:
    roots = [paths.download_dir]
    for item in settings.local.dirs:
        p = Path(item).expanduser()
        if p not in roots:
            roots.append(p)
    return roots


@router.post("/scan")
async def scan_local(
    library: LocalLibraryDep,
    paths: AppPathsDep,
    settings: AppSettingsDep,
) -> dict[str, Any]:
    """重新扫描本地目录，返回书籍列表."""
    books = await asyncio.to_thread(library.scan, _all_roots(paths, settings))
    return {"count": len(books), "books": books}


@router.get("/books")
async def list_local(
    library: LocalLibraryDep,
    paths: AppPathsDep,
    settings: AppSettingsDep,
) -> dict[str, Any]:
    """列出本地书籍：未扫描过则先扫描."""
    books = library.list_books()
    if not books:
        books = await asyncio.to_thread(library.scan, _all_roots(paths, settings))
    return {"count": len(books), "books": books}


@router.get("/books/{book_id}")
async def get_local_book(book_id: str, library: LocalLibraryDep) -> dict[str, Any]:
    book = library.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="local book not found")
    return book.to_dict()


@router.get("/books/{book_id}/eps/{eps_index}/pages")
async def get_local_pages(
    book_id: str, eps_index: int, library: LocalLibraryDep
) -> dict[str, Any]:
    result = library.get_eps_pages(book_id, eps_index)
    if result is None:
        raise HTTPException(status_code=404, detail="local book or eps not found")
    return result


@router.get("/images/{book_id}/{eps_index}/{page_index}")
async def get_local_image(
    book_id: str, eps_index: int, page_index: int, library: LocalLibraryDep
) -> Response:
    # zip 解压/磁盘读可能很慢（NAS/大压缩包），放线程池避免阻塞事件循环
    result = await asyncio.to_thread(library.read_page, book_id, eps_index, page_index)
    if result is None:
        raise HTTPException(status_code=404, detail="local image not found")
    data, content_type = result
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "max-age=86400"},
    )


class LocalProgressBody(BaseModel):
    epsIndex: int = Field(ge=0)
    pageIndex: int = Field(ge=0)
    title: str | None = Field(default=None, max_length=500)


@router.get("/books/{book_id}/progress")
async def get_local_progress(
    book_id: str, history: HistoryStoreDep
) -> dict[str, Any]:
    return {
        "bookId": book_id,
        "progress": history.get_progress(PROGRESS_PREFIX + book_id),
    }


@router.put("/books/{book_id}/progress")
async def save_local_progress(
    book_id: str,
    body: LocalProgressBody,
    history: HistoryStoreDep,
) -> dict[str, bool]:
    history.save_progress(
        PROGRESS_PREFIX + book_id, body.epsIndex, body.pageIndex, title=body.title
    )
    return {"ok": True}
