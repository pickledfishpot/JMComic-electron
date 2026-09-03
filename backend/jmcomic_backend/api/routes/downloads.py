"""下载队列 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jmcomic_backend.api.deps import DownloadManagerDep
from jmcomic_backend.services.jm_client import JmClient

router = APIRouter(prefix="/downloads", tags=["downloads"])


class StartDownloadBody(BaseModel):
    bookId: str = Field(min_length=1)
    epsIndexes: list[int] | None = None
    bookTitle: str = ""


@router.get("")
async def list_downloads(manager: DownloadManagerDep) -> dict[str, Any]:
    return {"tasks": manager.list_tasks()}


@router.post("/start")
async def start_download(body: StartDownloadBody, manager: DownloadManagerDep) -> dict[str, Any]:
    """创建下载任务；epsIndexes 为空表示下载全部章节，每章一个任务."""
    async with JmClient() as client:
        try:
            detail = await client.get_book_detail(body.bookId)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch book detail: {exc}") from exc

    eps_list = detail.get("eps", []) or []
    if not eps_list:
        raise HTTPException(status_code=404, detail="book has no eps")
    wanted = (
        eps_list
        if body.epsIndexes is None
        else [e for e in eps_list if int(e.get("index", -1)) in set(body.epsIndexes)]
    )
    if not wanted:
        raise HTTPException(status_code=404, detail="no matching eps")

    title = body.bookTitle or detail.get("title") or body.bookId
    task_ids = [
        manager.create_task(
            book_id=str(detail["id"]),
            book_title=title,
            eps_index=int(eps["index"]),
            eps_id=str(eps["epsId"]),
            eps_name=eps.get("name") or "",
        )
        for eps in wanted
    ]
    return {"taskIds": task_ids}


@router.post("/{task_id}/pause")
async def pause_download(task_id: str, manager: DownloadManagerDep) -> dict[str, bool]:
    return {"ok": manager.pause(task_id)}


@router.post("/{task_id}/resume")
async def resume_download(task_id: str, manager: DownloadManagerDep) -> dict[str, bool]:
    return {"ok": manager.resume(task_id)}


@router.post("/{task_id}/retry")
async def retry_download(task_id: str, manager: DownloadManagerDep) -> dict[str, bool]:
    return {"ok": manager.retry(task_id)}


@router.delete("/{task_id}")
async def remove_download(task_id: str, manager: DownloadManagerDep) -> dict[str, bool]:
    return {"ok": manager.remove(task_id)}
