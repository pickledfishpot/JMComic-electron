"""图片磁盘缓存.

反分割后的图片按请求标识（路径 + scramble_id）缓存到 data_dir/cache/images，
避免翻页/重进阅读器时重复下载与 PIL 运算。文件名为 sha1(identifier)，
同目录 .meta 文件记录 content-type.
"""

from __future__ import annotations

import asyncio
import hashlib
import threading
from pathlib import Path


class ImageDiskCache:
    def __init__(self, cache_dir: Path) -> None:
        self._dir = cache_dir / "images"
        self._dir.mkdir(parents=True, exist_ok=True)
        # 磁盘 IO 走线程池，磁盘文件操作加锁保护
        self._io_lock = threading.Lock()
        # 同一图片并发请求时只拉取一次（如预加载与当前页同时命中）
        self._async_locks: dict[str, asyncio.Lock] = {}
        self._async_locks_guard = threading.Lock()

    def _key(self, identifier: str) -> str:
        return hashlib.sha1(identifier.encode()).hexdigest()

    def lock_for(self, identifier: str) -> asyncio.Lock:
        """返回该图片的异步锁，调用方需持有锁后再 get/set."""
        key = self._key(identifier)
        with self._async_locks_guard:
            lock = self._async_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._async_locks[key] = lock
            return lock

    def get(self, identifier: str) -> tuple[bytes, str] | None:
        key = self._key(identifier)
        data_file = self._dir / f"{key}.bin"
        meta_file = self._dir / f"{key}.meta"
        with self._io_lock:
            if not data_file.exists():
                return None
            data = data_file.read_bytes()
            content_type = (
                meta_file.read_text(encoding="utf-8").strip() if meta_file.exists() else "image/jpeg"
            )
        return data, content_type

    def set(self, identifier: str, data: bytes, content_type: str) -> None:
        key = self._key(identifier)
        with self._io_lock:
            (self._dir / f"{key}.bin").write_bytes(data)
            (self._dir / f"{key}.meta").write_text(content_type, encoding="utf-8")
