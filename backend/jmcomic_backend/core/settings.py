"""Pydantic Settings，替代原 Qt 项目的 QSettings.

支持从 data_dir/config.yaml 读取用户设置，未配置时使用默认值.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from .config import PROJECT_NAME


class ProxySettings(BaseModel):
    enabled: bool = False
    select_index: int = 0
    http: str = ""
    https: str = ""
    socks5: str = ""


class NetworkSettings(BaseModel):
    api_timeout: int = Field(default=10, ge=1, le=300)
    img_timeout: int = Field(default=30, ge=1, le=600)
    thread_num: int = Field(default=5, ge=1, le=50)
    download_thread_num: int = Field(default=5, ge=1, le=50)
    pre_loading: int = Field(default=10, ge=0, le=100)


class ReaderSettings(BaseModel):
    look_model_name: str = ""
    look_scale: int = Field(default=2, ge=1, le=4)


class AppSettings(BaseModel):
    theme: Literal["system", "light", "dark"] = "system"
    language: str = "zh-CN"
    proxy: ProxySettings = ProxySettings()
    network: NetworkSettings = NetworkSettings()
    reader: ReaderSettings = ReaderSettings()

    @classmethod
    def load_from_file(cls, path: Path) -> "AppSettings":
        if not path.exists():
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls.model_validate(data)
        except Exception:
            return cls()

    def save_to_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.model_dump(), f, allow_unicode=True, sort_keys=False)
