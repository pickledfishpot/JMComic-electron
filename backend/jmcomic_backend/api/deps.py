"""FastAPI 依赖注入."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from jmcomic_backend.core.paths import AppPaths
from jmcomic_backend.core.settings import AppSettings


def get_app_paths(request: Request) -> AppPaths:
    return request.app.state.paths


def get_app_settings(request: Request) -> AppSettings:
    return request.app.state.settings


AppPathsDep = Annotated[AppPaths, Depends(get_app_paths)]
AppSettingsDep = Annotated[AppSettings, Depends(get_app_settings)]
