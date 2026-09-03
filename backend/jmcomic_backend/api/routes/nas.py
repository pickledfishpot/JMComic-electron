"""NAS 配置与上传 API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jmcomic_backend.api.deps import DownloadManagerDep, NasManagerDep
from jmcomic_backend.services.nas_manager import NasError

router = APIRouter(prefix="/nas", tags=["nas"])


class NasConfigBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    protocol: str = "webdav"
    address: str = ""
    port: int = Field(default=0, ge=0, le=65535)
    username: str = ""
    password: str = ""
    remote_path: str = ""


class NasUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    protocol: str | None = None
    address: str | None = None
    port: int | None = Field(default=None, ge=0, le=65535)
    username: str | None = None
    password: str | None = None
    remote_path: str | None = None


class UploadBody(BaseModel):
    bookId: str = Field(min_length=1)
    bookTitle: str = ""


def _get_or_404(manager: NasManagerDep, nas_id: str) -> dict[str, Any]:
    config = manager.get_config(nas_id)
    if config is None:
        raise HTTPException(status_code=404, detail="nas config not found")
    return config


@router.get("")
async def list_nas(manager: NasManagerDep) -> dict[str, Any]:
    configs = manager.list_configs()
    # 前端列表不暴露密码
    for item in configs:
        if item["password"]:
            item["password"] = "******"
    return {"configs": configs}


@router.post("")
async def add_nas(body: NasConfigBody, manager: NasManagerDep) -> dict[str, Any]:
    try:
        config = manager.add_config(**body.model_dump())
    except NasError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return config


@router.put("/{nas_id}")
async def update_nas(
    nas_id: str, body: NasUpdateBody, manager: NasManagerDep
) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    # 密码保持掩码时不更新
    if fields.get("password") == "******":
        fields.pop("password")
    try:
        config = manager.update_config(nas_id, **fields)
    except NasError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if config is None:
        raise HTTPException(status_code=404, detail="nas config not found")
    if config["password"]:
        config["password"] = "******"
    return config


@router.delete("/{nas_id}")
async def delete_nas(nas_id: str, manager: NasManagerDep) -> dict[str, bool]:
    if not manager.delete_config(nas_id):
        raise HTTPException(status_code=404, detail="nas config not found")
    return {"ok": True}


@router.post("/{nas_id}/test")
async def test_nas(nas_id: str, manager: NasManagerDep) -> dict[str, Any]:
    config = _get_or_404(manager, nas_id)
    try:
        return await manager.test(config)
    except NasError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/{nas_id}/upload")
async def upload_book(
    nas_id: str,
    body: UploadBody,
    manager: NasManagerDep,
    downloads: DownloadManagerDep,
) -> dict[str, Any]:
    config = _get_or_404(manager, nas_id)
    book_dir = downloads.book_dir(body.bookId)
    if not book_dir.is_dir():
        raise HTTPException(status_code=404, detail="本地未找到该书的下载目录")
    try:
        return await manager.upload_book(config, book_dir, body.bookTitle or body.bookId)
    except NasError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
