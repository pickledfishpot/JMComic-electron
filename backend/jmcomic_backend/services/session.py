"""用户会话管理.

登录成功后 JM 返回 cookies（AVS 等），后续 API 请求需携带;
会话持久化到 data_dir/session.json，应用重启后保持登录态.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    uid: str
    username: str
    title: str = ""
    level: str = ""
    coin: str = ""
    gender: str = ""
    favorites: str = ""
    favorites_max: str = ""
    exp: int = 0
    next_exp: int = 0
    cookies: dict[str, str] = field(default_factory=dict)

    def public_dict(self) -> dict[str, Any]:
        """对外返回的用户信息（不含 cookies）."""
        data = asdict(self)
        data.pop("cookies", None)
        return data


class SessionManager:
    def __init__(self, session_file: Path) -> None:
        self._file = session_file
        self._session: UserSession | None = None
        self._load()

    def _load(self) -> None:
        try:
            if self._file.exists():
                raw = json.loads(self._file.read_text(encoding="utf-8"))
                self._session = UserSession(**raw)
                logger.info("session loaded, uid=%s", self._session.uid)
        except Exception as exc:
            logger.warning("failed to load session file: %s", exc)
            self._session = None

    def get(self) -> UserSession | None:
        return self._session

    def save(self, session: UserSession) -> None:
        self._session = session
        try:
            self._file.write_text(
                json.dumps(asdict(session), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("failed to persist session: %s", exc)

    def clear(self) -> None:
        self._session = None
        try:
            if self._file.exists():
                self._file.unlink()
        except Exception as exc:
            logger.warning("failed to remove session file: %s", exc)
