"""收藏 API：列表 / 切换收藏 / 收藏夹管理."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from jmcomic_backend.services.jm_client import JmClient, JmApiError

router = APIRouter(prefix="/favorites", tags=["favorites"])


class ToggleFavoriteBody(BaseModel):
    bookId: str = Field(min_length=1)


class AddFolderBody(BaseModel):
    name: str = Field(min_length=1)


class MoveFolderBody(BaseModel):
    bookId: str = Field(min_length=1)
    folderId: str = Field(min_length=1)


def _require_session(request: Request) -> None:
    if request.app.state.session.get() is None:
        raise HTTPException(status_code=401, detail="请先登录")


def _wrap(exc: Exception, action: str) -> HTTPException:
    """JM 业务层返回的未登录错误映射为 401，其余上游错误为 502，
    让前端能区分「需要重新登录」与「服务器故障」."""
    if isinstance(exc, JmApiError) and exc.is_auth_error:
        return HTTPException(status_code=401, detail=str(exc))
    return HTTPException(status_code=502, detail=f"Failed to {action}: {exc}")


@router.get("")
async def get_favorites(
    request: Request,
    page: int = 1,
    sort: str = "mr",
    folderId: str = "0",
) -> dict[str, Any]:
    _require_session(request)
    async with JmClient() as client:
        try:
            data = await client.get_favorites(page=page, sort=sort, folder_id=folderId)
        except Exception as exc:
            raise _wrap(exc, "fetch favorites") from exc
    data["page"] = page
    data["sort"] = sort
    data["folderId"] = folderId
    return data


@router.post("")
async def toggle_favorite(body: ToggleFavoriteBody, request: Request) -> dict[str, Any]:
    _require_session(request)
    async with JmClient() as client:
        try:
            return await client.toggle_favorite(body.bookId)
        except Exception as exc:
            raise _wrap(exc, "toggle favorite") from exc


@router.post("/folders")
async def add_folder(body: AddFolderBody, request: Request) -> dict[str, Any]:
    _require_session(request)
    async with JmClient() as client:
        try:
            return await client.add_favorite_folder(body.name)
        except Exception as exc:
            raise _wrap(exc, "add folder") from exc


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, request: Request) -> dict[str, Any]:
    _require_session(request)
    async with JmClient() as client:
        try:
            return await client.delete_favorite_folder(folder_id)
        except Exception as exc:
            raise _wrap(exc, "delete folder") from exc


@router.post("/move")
async def move_to_folder(body: MoveFolderBody, request: Request) -> dict[str, Any]:
    _require_session(request)
    async with JmClient() as client:
        try:
            return await client.move_favorite_folder(body.bookId, body.folderId)
        except Exception as exc:
            raise _wrap(exc, "move favorite") from exc
