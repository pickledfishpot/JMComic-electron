"""健康检查路由."""

from __future__ import annotations

from fastapi import APIRouter

from jmcomic_backend.api.deps import AppPathsDep
from jmcomic_backend.core.config import VERSION

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(paths: AppPathsDep) -> dict[str, str]:
    return {
        "status": "ok",
        "version": VERSION,
        "dataDir": str(paths.data_dir),
    }
