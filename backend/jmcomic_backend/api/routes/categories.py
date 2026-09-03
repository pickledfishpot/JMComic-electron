"""分类 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from jmcomic_backend.services.jm_client import JmClient

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def get_categories() -> dict[str, Any]:
    async with JmClient() as client:
        try:
            data = await client.get_categories()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch categories: {exc}") from exc
    return data


@router.get("/{slug}/books")
async def get_category_books(
    slug: str,
    page: int = 1,
    sort: str = "mr",
) -> dict[str, Any]:
    async with JmClient() as client:
        try:
            data = await client.get_category_books(category=slug, page=page, sort=sort)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch category books: {exc}") from exc
    return {"slug": slug, "page": page, "sort": sort, **data}
