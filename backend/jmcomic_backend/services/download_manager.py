"""下载队列管理.

每章一个下载任务，持久化到 SQLite（data_dir/db/app.db 的 download_tasks 表），
异步 worker 依次执行任务；任务内 4 并发拉取图片，逐页反分割后写入
download_dir/{book_id}/{章节序号:03d}/{页序号:04d}.{ext}。
支持暂停 / 恢复 / 重试（已存在的页自动跳过）/ 删除.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import threading
import time
import uuid
from concurrent.futures import Future
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


class DownloadCancelled(Exception):
    """任务被用户删除或应用正在退出."""


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
        # 被 remove() 标记删除的任务：worker 读到后立刻停止写入并退出
        self._cancelled: set[str] = set()
        # remove() 触发的后台目录删除：重建同目录任务时必须等它结束
        self._dir_deleting: dict[Path, Future[None]] = {}
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
            # 给在途任务最多 10 秒收尾；超时直接取消（含在途页面请求）
            try:
                await asyncio.wait_for(asyncio.shield(self._worker), timeout=10)
            except (asyncio.TimeoutError, TimeoutError):
                self._worker.cancel()
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
        # 同一本书同一话去重：已有排队/下载中/暂停的任务直接复用
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM download_tasks "
                "WHERE book_id = ? AND eps_index = ? AND status IN (?, ?, ?)",
                (book_id, eps_index, STATUS_PENDING, STATUS_DOWNLOADING, STATUS_PAUSED),
            ).fetchone()
            if row:
                return row[0]
            task_id = uuid.uuid4().hex[:12]
            now = time.time()
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
        # 只有 worker 正在执行的任务才需要取消标记；pending 任务删行即可，
        # 否则没机会进 _run_task 的 finally，id 会在 _cancelled 里永久泄漏
        if task_id in self._active:
            self._cancelled.add(task_id)
        eps_dir = self._eps_dir(task["book_id"], task["eps_index"])
        # 后台删除文件，不阻塞请求；无事件循环时同步删除。
        # 登记删除 future，重建同目录任务时 _run_task 等它结束，避免边删边写
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._rmtree(eps_dir)
        else:
            future: Future[None] = loop.run_in_executor(None, self._rmtree, eps_dir)
            self._dir_deleting[eps_dir] = future
            future.add_done_callback(
                lambda _f, d=eps_dir: self._dir_deleting.pop(d, None)
            )
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
                # 同目录可能有 remove() 触发的后台删除未完成，等它结束再写入，
                # 否则执行器线程边删、worker 边写，新页可能被事后删掉
                deleting = self._dir_deleting.get(out_dir)
                if deleting is not None:
                    await asyncio.wrap_future(deleting)
                out_dir.mkdir(parents=True, exist_ok=True)

                pending: set[asyncio.Task] = set()
                page_iter = iter(pages)
                try:
                    while True:
                        if self._stopping or task_id in self._cancelled:
                            raise DownloadCancelled()
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
                except BaseException:
                    # 取消/暂停/异常退出时回收在途页任务，避免脱离监管继续写文件
                    for rest in pending:
                        rest.cancel()
                    raise

            # 行已被删除或状态被改写（暂停/恢复竞态）时不覆盖
            if self._get_status(task_id) == STATUS_DOWNLOADING:
                self._set_status(task_id, STATUS_DONE)
        except DownloadCancelled:
            self._cancelled.discard(task_id)
        except DownloadPaused:
            # 仅在仍处于下载链路时落 PAUSED；pause->resume 竞态下保持新状态
            self._set_status(task_id, STATUS_PAUSED, only_from={STATUS_DOWNLOADING})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("download task %s failed: %s", task_id, exc)
            # only_from 防止 pause->resume 后旧 worker 的迟到错误覆盖新状态
            self._set_status(
                task_id, STATUS_ERROR, only_from={STATUS_DOWNLOADING}, error=str(exc)
            )
        finally:
            self._cancelled.discard(task_id)

    def _check_abort(self, task_id: str) -> None:
        """页面级的中断检查：暂停 / 删除 / 退出."""
        if task_id in self._cancelled or self._stopping:
            raise DownloadCancelled()
        if self._get_status(task_id) == STATUS_PAUSED:
            raise DownloadPaused()

    async def _fetch_page(
        self,
        client: JmClient,
        task_id: str,
        out_dir: Path,
        page: dict[str, Any],
        eps_id: str,
        scramble_id: int,
    ) -> None:
        self._check_abort(task_id)
        dest = out_dir / f"{page['index'] + 1:04d}.{page['path'].rsplit('.', 1)[-1]}"
        if dest.exists() and dest.stat().st_size > 0:
            self._increment_done(task_id)
            return
        data, _ = await client.fetch_image(page["path"])
        data = await asyncio.to_thread(
            deslice_image, data, eps_id, scramble_id, page["name"]
        )
        self._check_abort(task_id)
        # 先写临时文件再原子替换，避免进程中断留下截断的页文件
        # （截断文件会被 dest.exists() 当成已完成而永久跳过）
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            await asyncio.to_thread(tmp.write_bytes, data)
            if tmp.stat().st_size == 0:
                raise IOError(f"empty page data for {dest.name}")
            await asyncio.to_thread(os.replace, tmp, dest)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        self._increment_done(task_id)

    # ---------------- 内部工具 ----------------

    def _eps_dir(self, book_id: str, eps_index: int) -> Path:
        return self._download_dir / str(book_id) / f"{eps_index + 1:03d}"

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
