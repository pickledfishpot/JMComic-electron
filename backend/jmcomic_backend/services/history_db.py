"""阅读历史 SQLite 存储.

记录每本书的阅读进度（章节序号 + 页码 + 标题），进入阅读器时恢复上次进度，
历史页按 updated_at 倒序展示.
表结构刻意简单：单表 upsert，按 book_id 主键覆盖.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS read_history (
    book_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    eps_index INTEGER NOT NULL,
    page_index INTEGER NOT NULL,
    updated_at REAL NOT NULL
)
"""


class HistoryStore:
    """阅读历史存取，线程安全（sqlite3 连接跨线程使用）."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(_SCHEMA)
            self._migrate_locked()
            self._conn.commit()

    def _migrate_locked(self) -> None:
        """为旧库补充 title 列（sqlite 不支持 IF NOT EXISTS 加列）."""
        columns = {
            row[1] for row in self._conn.execute("PRAGMA table_info(read_history)")
        }
        if "title" not in columns:
            self._conn.execute(
                "ALTER TABLE read_history ADD COLUMN title TEXT NOT NULL DEFAULT ''"
            )

    def get_progress(self, book_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT eps_index, page_index, updated_at FROM read_history WHERE book_id = ?",
                (book_id,),
            ).fetchone()
        if not row:
            return None
        return {"epsIndex": row[0], "pageIndex": row[1], "updatedAt": row[2]}

    def save_progress(
        self,
        book_id: str,
        eps_index: int,
        page_index: int,
        title: str | None = None,
    ) -> None:
        with self._lock:
            if title:
                self._conn.execute(
                    "INSERT INTO read_history (book_id, title, eps_index, page_index, updated_at) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(book_id) DO UPDATE SET "
                    "title = excluded.title, "
                    "eps_index = excluded.eps_index, "
                    "page_index = excluded.page_index, "
                    "updated_at = excluded.updated_at",
                    (book_id, title, eps_index, page_index, time.time()),
                )
            else:
                self._conn.execute(
                    "INSERT INTO read_history (book_id, title, eps_index, page_index, updated_at) "
                    "VALUES (?, '', ?, ?, ?) "
                    "ON CONFLICT(book_id) DO UPDATE SET "
                    "eps_index = excluded.eps_index, "
                    "page_index = excluded.page_index, "
                    "updated_at = excluded.updated_at",
                    (book_id, eps_index, page_index, time.time()),
                )
            self._conn.commit()

    def list_history(
        self, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """按最近阅读时间倒序返回历史条目（不含 local: 前缀的本地图库进度）."""
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM read_history WHERE book_id NOT LIKE 'local:%'"
            ).fetchone()[0]
            rows = self._conn.execute(
                "SELECT book_id, title, eps_index, page_index, updated_at "
                "FROM read_history WHERE book_id NOT LIKE 'local:%' "
                "ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return {
            "total": total,
            "items": [
                {
                    "bookId": row[0],
                    "title": row[1],
                    "epsIndex": row[2],
                    "pageIndex": row[3],
                    "updatedAt": row[4],
                }
                for row in rows
            ],
        }

    def remove(self, book_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM read_history WHERE book_id = ?", (book_id,)
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
