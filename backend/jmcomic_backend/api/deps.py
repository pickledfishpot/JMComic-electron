"""FastAPI 依赖注入."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from jmcomic_backend.core.paths import AppPaths
from jmcomic_backend.core.settings import AppSettings
from jmcomic_backend.services.download_manager import DownloadManager
from jmcomic_backend.services.history_db import HistoryStore
from jmcomic_backend.services.image_cache import ImageDiskCache
from jmcomic_backend.services.local_library import LocalLibrary
from jmcomic_backend.services.session import SessionManager


def get_app_paths(request: Request) -> AppPaths:
    return request.app.state.paths


def get_app_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def get_history_store(request: Request) -> HistoryStore:
    return request.app.state.history


def get_image_cache(request: Request) -> ImageDiskCache:
    return request.app.state.image_cache


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session


def get_download_manager(request: Request) -> DownloadManager:
    return request.app.state.downloads


def get_local_library(request: Request) -> LocalLibrary:
    return request.app.state.local_library


AppPathsDep = Annotated[AppPaths, Depends(get_app_paths)]
AppSettingsDep = Annotated[AppSettings, Depends(get_app_settings)]
HistoryStoreDep = Annotated[HistoryStore, Depends(get_history_store)]
ImageCacheDep = Annotated[ImageDiskCache, Depends(get_image_cache)]
SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]
DownloadManagerDep = Annotated[DownloadManager, Depends(get_download_manager)]
LocalLibraryDep = Annotated[LocalLibrary, Depends(get_local_library)]
