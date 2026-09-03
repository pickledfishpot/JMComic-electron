"""设置路由."""

from __future__ import annotations

from fastapi import APIRouter

from jmcomic_backend.api.deps import AppPathsDep, AppSettingsDep
from jmcomic_backend.core.settings import AppSettings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(settings: AppSettingsDep) -> AppSettings:
    return settings


@router.put("")
async def update_settings(
    new_settings: AppSettings,
    settings: AppSettingsDep,
    paths: AppPathsDep,
) -> AppSettings:
    new_settings.save_to_file(paths.config_file)
    return new_settings
