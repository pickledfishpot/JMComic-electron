"""设置路由."""

from __future__ import annotations

from fastapi import APIRouter, Request

from jmcomic_backend.api.deps import AppPathsDep, AppSettingsDep
from jmcomic_backend.core.settings import AppSettings
from jmcomic_backend.services.jm_client import set_default_proxy

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(settings: AppSettingsDep) -> AppSettings:
    return settings


@router.put("")
async def update_settings(
    request: Request,
    new_settings: AppSettings,
    settings: AppSettingsDep,
    paths: AppPathsDep,
) -> AppSettings:
    new_settings.save_to_file(paths.config_file)
    request.app.state.settings = new_settings
    set_default_proxy(
        new_settings.proxy.effective_url() if new_settings.proxy.enabled else ""
    )
    return new_settings
