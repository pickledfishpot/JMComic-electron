"""下载队列管理.

每章一个下载任务，持久化到 SQLite（data_dir/db/app.db 的 download_tasks 表），
异步 worker 依次执行任务；任务内 4 并发拉取图片，逐页反分割后写入
download_dir/{book_id}/{章节序号:03d}/{页序号:04d}.{ext}。
支持暂停 / 恢复 / 重试（已存在的页自动跳过）/ 删除.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from jmcomic_backend.services.deslice import deslice_image
from jmcomic_backend.services.jm_client import JmClient

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_DOWNLOADING = "downloading"
STATUS_PAUSED = "paused"
STATUS_DONE = "done"
STATUS_ERROR = "error"

PAGE_CONCURRENCY = 4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS download_tasks (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL,
    book_title TEXT NOT NULL DEFAULT '',
    eps_index INTEGER NOT NULL,
    eps_id TEXT NOT NULL DEFAULT '',
    eps_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    total_pages INTEGER NOT NULL DEFAULT 0,
    done_pages INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
)
"""


class DownloadPaused(Exception):
    """任务被用户暂停."""


class DownloadManager:
    def __init__(self, db_path: Path, download_dir: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()
        self._download_dir = download_dir
        self._download_dir.mkdir(parents=True, exist_ok=True)
        self._wake = asyncio.Event()
        self._worker: asyncio.Task | None = None
        self._stopping = False
        # 正在执行的任务 id，防止 pause->resume 期间被重复领取
        self._active: set[str] = set()
        with self._lock:
            self._conn.execute(_SCHEMA)
            # 上次进程退出时遗留的 downloading 任务重新排队
            self._conn.execute(
                "UPDATE download_tasks SET status = 'pending' WHERE status = 'downloading'"
            )
            self._conn.commit()

    async def start(self) -> None:
        if self._worker is None:
            self._stopping = False
            self._worker = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        self._stopping = True
        self._wake.set()
        if self._worker is not None:
            await asyncio.gather(self._worker, return_exceptions=True)
            self._worker = None

    # ---------------- 任务管理（前端调用） ----------------

    def create_task(
        self,
        book_id: str,
        book_title: str,
        eps_index: int,
        eps_id: str,
        eps_name: str,
    ) -> str:
        task_id = uuid.uuid4().hex[:12]
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO download_tasks "
                "(id, book_id, book_title, eps_index, eps_id, eps_name, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
                (task_id, book_id, book_title, eps_index, eps_id, eps_name, now, now),
            )
            self._conn.commit()
        self._wake.set()
        return task_id

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, book_id, book_title, eps_index, eps_id, eps_name, status, "
                "total_pages, done_pages, error, created_at, updated_at "
                "FROM download_tasks ORDER BY created_at DESC"
            ).fetchall()
        keys = (
            "id", "bookId", "bookTitle", "epsIndex", "epsId", "epsName",
            "status", "totalPages", "donePages", "error", "createdAt", "updatedAt",
        )
        return [dict(zip(keys, row)) for row in rows]

    def pause(self, task_id: str) -> bool:
        return self._set_status(task_id, STATUS_PAUSED, only_from={STATUS_PENDING, STATUS_DOWNLOADING})

    def resume(self, task_id: str) -> bool:
        ok = self._set_status(task_id, STATUS_PENDING, only_from={STATUS_PAUSED})
        if ok:
            self._wake.set()
        return ok

    def retry(self, task_id: str) -> bool:
        ok = self._set_status(task_id, STATUS_PENDING, only_from={STATUS_ERROR})
        if ok:
            self._wake.set()
        return ok

    def remove(self, task_id: str) -> bool:
        task = self._get_task(task_id)
        if not task:
            return False
        with self._lock:
            self._conn.execute(
                "DELETE FROM download_tasks WHERE id = ?", (task_id,)
            )
            self._conn.commit()
        eps_dir = self._eps_dir(task["book_id"], task["eps_index"])
        # 后台删除文件，不阻塞请求；无事件循环时同步删除
        try:
            asyncio.get_running_loop().run_in_executor(None, self._rmtree, eps_dir)
        except RuntimeError:
            self._rmtree(eps_dir)
        return True

    # ---------------- worker ----------------

    async def _worker_loop(self) -> None:
        logger.info("download worker started")
        while not self._stopping:
            task = self._next_pending()
            if task is None:
                self._wake.clear()
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                continue
            self._active.add(task["id"])
            try:
                await self._run_task(task)
            except Exception as exc:
                logger.exception("download task %s crashed: %s", task["id"], exc)
                self._set_status(task["id"], STATUS_ERROR, error=str(exc))
            finally:
                self._active.discard(task["id"])
        logger.info("download worker stopped")

    async def _run_task(self, task: dict[str, Any]) -> None:
        task_id = task["id"]
        book_id = task["book_id"]
        eps_index = task["eps_index"]
        eps_id = task["eps_id"] or book_id
        self._set_status(task_id, STATUS_DOWNLOADING)

        try:
            async with JmClient() as client:
                pages, scramble_id = await asyncio.gather(
                    client.get_chapter_pages(eps_id),
                    client.get_scramble_id(eps_id),
                )
                self._update_task(
                    task_id, total_pages=len(pages), done_pages=0, error=""
                )
                out_dir = self._eps_dir(book_id, eps_index)
                out_dir.mkdir(parents=True, exist_ok=True)

                pending: set[asyncio.Task] = set()
                page_iter = iter(pages)
                while True:
                    while len(pending) < PAGE_CONCURRENCY:
                        page = next(page_iter, None)
                        if page is None:
                            break
                        pending.add(
                            asyncio.create_task(
                                self._fetch_page(
                                    client, task_id, out_dir, page, eps_id, scramble_id
                                )
                            )
                        )
                    if not pending:
                        break
                    done, pending = await asyncio.wait(
                        pending, return_when=asyncio.FIRST_COMPLETED
                    )
                    for item in done:
                        exc = item.exception()
                        if exc is not None:
                            for rest in pending:
                                rest.cancel()
                            raise exc

            if self._get_status(task_id) == STATUS_PAUSED:
                return
            self._set_status(task_id, STATUS_DONE)
        except DownloadPaused:
            self._set_status(task_id, STATUS_PAUSED)
        except Exception as exc:
            logger.warning("download task %s failed: %s", task_id, exc)
            self._set_status(task_id, STATUS_ERROR, error=str(exc))

    async def _fetch_page(
        self,
        client: JmClient,
        task_id: str,
        out_dir: Path,
        page: dict[str, Any],
        eps_id: str,
        scramble_id: int,
    ) -> None:
        if self._get_status(task_id) == STATUS_PAUSED:
            raise DownloadPaused()
        dest = out_dir / f"{page['index'] + 1:04d}.{page['path'].rsplit('.', 1)[-1]}"
        if dest.exists():
            self._increment_done(task_id)
            return
        data, _ = await client.fetch_image(page["path"])
        data = await asyncio.to_thread(
            deslice_image, data, eps_id, scramble_id, page["name"]
        )
        await asyncio.to_thread(dest.write_bytes, data)
        self._increment_done(task_id)

    # ---------------- 内部工具 ----------------

    def _eps_dir(self, book_id: str, eps_index: int) -> Path:
        return self._download_dir / str(book_id) / f"{eps_index + 1:03d}"

    def book_dir(self, book_id: str) -> Path:
        """整本书的下载目录（NAS 上传等场景用）."""
        return self._download_dir / str(book_id)

    def _rmtree(self, path: Path) -> None:
        import shutil

        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def _next_pending(self) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, book_id, eps_index, eps_id FROM download_tasks "
                "WHERE status = 'pending' ORDER BY created_at LIMIT 5"
            ).fetchall()
        for item in row:
            if item[0] not in self._active:
                return {
                    "id": item[0],
                    "book_id": item[1],
                    "eps_index": item[2],
                    "eps_id": item[3],
                }
        return None

    def _get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT book_id, eps_index FROM download_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        if not row:
            return None
        return {"book_id": row[0], "eps_index": row[1]}

    def _get_status(self, task_id: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT status FROM download_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return row[0] if row else None

    def _set_status(
        self,
        task_id: str,
        status: str,
        only_from: set[str] | None = None,
        error: str = "",
    ) -> bool:
        with self._lock:
            if only_from is not None:
                cur = self._conn.execute(
                    "UPDATE download_tasks SET status = ?, error = ?, updated_at = ? "
                    "WHERE id = ? AND status IN (%s)"
                    % ",".join("?" for _ in only_from),
                    (status, error, time.time(), task_id, *sorted(only_from)),
                )
            else:
                cur = self._conn.execute(
                    "UPDATE download_tasks SET status = ?, error = ?, updated_at = ? WHERE id = ?",
                    (status, error, time.time(), task_id),
                )
            self._conn.commit()
            return cur.rowcount > 0

    def _update_task(self, task_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = time.time()
        columns = ", ".join(f"{key} = ?" for key in fields)
        with self._lock:
            self._conn.execute(
                f"UPDATE download_tasks SET {columns} WHERE id = ?",
                (*fields.values(), task_id),
            )
            self._conn.commit()

    def _increment_done(self, task_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE download_tasks SET done_pages = done_pages + 1, updated_at = ? "
                "WHERE id = ?",
                (time.time(), task_id),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
