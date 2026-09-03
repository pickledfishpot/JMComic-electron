"""NAS 配置存储与上传服务，移植自原 JMComic-qt 的 task_upload.py / upload_*.py.

配置持久化到 SQLite（nas_configs 表）。支持三种协议：
- webdav：httpx 原生实现 MKCOL/PUT，避免额外依赖
- smb：依赖 smbprotocol 库（懒加载），未安装时明确报错
- local：拷贝到本地目录（可当作"备份到指定文件夹"使用）
"""

from __future__ import annotations

import asyncio
import base64
import logging
import shutil
import sqlite3
import threading
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS nas_configs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    protocol TEXT NOT NULL DEFAULT 'webdav',
    address TEXT NOT NULL DEFAULT '',
    port INTEGER NOT NULL DEFAULT 0,
    username TEXT NOT NULL DEFAULT '',
    password TEXT NOT NULL DEFAULT '',
    remote_path TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
)
"""

PROTOCOLS = ("webdav", "smb", "local")


class NasError(Exception):
    """NAS 操作失败，message 面向用户."""


class NasManager:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(SCHEMA)
            self._conn.commit()

    # ---------------- 配置 CRUD ----------------

    def list_configs(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, name, protocol, address, port, username, password, "
                "remote_path, created_at, updated_at FROM nas_configs ORDER BY created_at"
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_config(self, nas_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, name, protocol, address, port, username, password, "
                "remote_path, created_at, updated_at FROM nas_configs WHERE id = ?",
                (nas_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def add_config(
        self,
        name: str,
        protocol: str,
        address: str = "",
        port: int = 0,
        username: str = "",
        password: str = "",
        remote_path: str = "",
    ) -> dict[str, Any]:
        if protocol not in PROTOCOLS:
            raise NasError(f"不支持的协议: {protocol}")
        nas_id = uuid.uuid4().hex[:12]
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO nas_configs "
                "(id, name, protocol, address, port, username, password, remote_path, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (nas_id, name, protocol, address, port, username, password, remote_path, now, now),
            )
            self._conn.commit()
        return self.get_config(nas_id)

    def update_config(self, nas_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {"name", "protocol", "address", "port", "username", "password", "remote_path"}
        fields = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not fields:
            return self.get_config(nas_id)
        if "protocol" in fields and fields["protocol"] not in PROTOCOLS:
            raise NasError(f"不支持的协议: {fields['protocol']}")
        fields["updated_at"] = time.time()
        columns = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            cur = self._conn.execute(
                f"UPDATE nas_configs SET {columns} WHERE id = ?",
                (*fields.values(), nas_id),
            )
            self._conn.commit()
        if cur.rowcount == 0:
            return None
        return self.get_config(nas_id)

    def delete_config(self, nas_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM nas_configs WHERE id = ?", (nas_id,))
            self._conn.commit()
        return cur.rowcount > 0

    # ---------------- 连接测试与上传 ----------------

    @staticmethod
    def _snake(config: dict[str, Any]) -> dict[str, Any]:
        """API 输出的 camelCase 配置转内部 snake_case."""
        mapping = {"remotePath": "remote_path", "createdAt": "created_at", "updatedAt": "updated_at"}
        return {mapping.get(k, k): v for k, v in config.items()}

    async def test(self, config: dict[str, Any]) -> dict[str, Any]:
        config = self._snake(config)
        try:
            if config["protocol"] == "webdav":
                await asyncio.to_thread(self._webdav_test, config)
            elif config["protocol"] == "smb":
                await asyncio.to_thread(self._smb_test, config)
            else:
                await asyncio.to_thread(self._local_test, config)
        except NasError:
            raise
        except Exception as exc:
            logger.warning("nas test failed: %s", exc)
            raise NasError(f"连接失败: {exc}") from exc
        return {"ok": True}

    async def upload_book(
        self, config: dict[str, Any], book_dir: Path, book_title: str
    ) -> dict[str, Any]:
        """把已下载的书籍目录整体上传到 NAS 的 remote_path/{书名}/ 下."""
        config = self._snake(config)
        if not book_dir.is_dir():
            raise NasError(f"本地书籍目录不存在: {book_dir}")
        files = sorted(p for p in book_dir.rglob("*") if p.is_file())
        if not files:
            raise NasError("书籍目录为空，没有可上传的文件")

        def _do_upload() -> None:
            target_root = self._remote_book_dir(config, book_title)
            for local in files:
                rel = local.relative_to(book_dir).as_posix()
                if config["protocol"] == "webdav":
                    self._webdav_upload(config, target_root, rel, local)
                elif config["protocol"] == "smb":
                    self._smb_upload(config, target_root, rel, local)
                else:
                    self._local_upload(config, target_root, rel, local)

        try:
            await asyncio.to_thread(_do_upload)
        except NasError:
            raise
        except Exception as exc:
            logger.warning("nas upload failed: %s", exc)
            raise NasError(f"上传失败: {exc}") from exc
        return {"ok": True, "files": len(files)}

    # ---------------- webdav（httpx 原生） ----------------

    @staticmethod
    def _webdav_base(config: dict[str, Any]) -> str:
        address = (config["address"] or "").rstrip("/")
        if not address:
            raise NasError("WebDAV 地址不能为空")
        if config["port"]:
            # 在 host 后补端口
            rest = address.split("://", 1)
            if len(rest) == 2:
                scheme, hostpart = rest
                hostpart = hostpart.split("/", 1)
                host = hostpart[0]
                path = hostpart[1] if len(hostpart) > 1 else ""
                address = f"{scheme}://{host}:{config['port']}/{path}"
        return address.rstrip("/")

    def _webdav_headers(self, config: dict[str, Any]) -> dict[str, str]:
        headers: dict[str, str] = {}
        if config["username"] or config["password"]:
            raw = f"{config['username']}:{config['password']}".encode()
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode()
        return headers

    def _webdav_test(self, config: dict[str, Any]) -> None:
        base = self._webdav_base(config)
        remote = config["remote_path"].strip("/")
        url = f"{base}/{quote(remote)}" if remote else base
        try:
            resp = httpx.request(
                "PROPFIND", url, headers=self._webdav_headers(config),
                timeout=10.0, verify=False,
            )
        except httpx.HTTPError as exc:
            raise NasError(f"连接失败: {exc}") from exc
        if resp.status_code in (401, 403):
            raise NasError("用户名或密码错误")
        if resp.status_code >= 400 and resp.status_code != 404:
            raise NasError(f"服务器返回错误: HTTP {resp.status_code}")

    def _webdav_mkcol(self, config: dict[str, Any], base: str, remote_dir: str) -> None:
        if not remote_dir:
            return
        # 逐级建目录，已存在(405)忽略
        parts = PurePosixPath(remote_dir).parts
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            url = f"{base}/{quote(current)}"
            try:
                resp = httpx.request(
                    "MKCOL", url, headers=self._webdav_headers(config),
                    timeout=30.0, verify=False,
                )
                if resp.status_code >= 400 and resp.status_code not in (405, 409):
                    raise NasError(f"创建远程目录失败 {current}: HTTP {resp.status_code}")
            except httpx.HTTPError as exc:
                raise NasError(f"创建远程目录失败 {current}: {exc}") from exc

    def _webdav_upload(
        self, config: dict[str, Any], target_root: str, rel_path: str, local: Path
    ) -> None:
        base = self._webdav_base(config)
        root = config["remote_path"].strip("/")
        target_root = f"{root}/{target_root}" if root else target_root
        remote_dir = str(PurePosixPath(target_root) / PurePosixPath(rel_path).parent)
        if remote_dir == ".":
            remote_dir = target_root
        self._webdav_mkcol(config, base, remote_dir)
        url = f"{base}/{quote(str(PurePosixPath(target_root) / rel_path))}"
        try:
            with open(local, "rb") as f:
                resp = httpx.put(
                    url, content=f.read(), headers=self._webdav_headers(config),
                    timeout=300.0, verify=False,
                )
            if resp.status_code >= 400:
                raise NasError(f"上传 {rel_path} 失败: HTTP {resp.status_code}")
        except httpx.HTTPError as exc:
            raise NasError(f"上传 {rel_path} 失败: {exc}") from exc

    # ---------------- smb（懒加载 smbprotocol） ----------------

    def _smb_client(self, config: dict[str, Any]) -> Any:
        try:
            from smbprotocol.tree import TreeConnect  # noqa: F401
        except ImportError as exc:
            raise NasError("未安装 smbprotocol 库，无法使用 SMB 协议") from exc

    def _smb_test(self, config: dict[str, Any]) -> None:
        self._smb_client(config)
        raise NasError("SMB 协议暂未实现（需要 smbprotocol 环境）")

    def _smb_upload(self, config: dict[str, Any], target_root: str, rel_path: str, local: Path) -> None:
        self._smb_client(config)
        raise NasError("SMB 协议暂未实现（需要 smbprotocol 环境）")

    # ---------------- local ----------------

    def _local_test(self, config: dict[str, Any]) -> None:
        if not config["remote_path"]:
            raise NasError("目标目录不能为空")
        path = Path(config["remote_path"]).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise NasError(f"目标目录不可写: {exc}") from exc

    def _local_upload(
        self, config: dict[str, Any], target_root: str, rel_path: str, local: Path
    ) -> None:
        dest = Path(config["remote_path"]).expanduser() / target_root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, dest)

    # ---------------- 内部工具 ----------------

    @staticmethod
    def _remote_book_dir(config: dict[str, Any], book_title: str) -> str:
        """书籍在 NAS 上的目标目录（相对 NAS 根，remote_path 由各协议自行拼接）."""
        return book_title.strip() or "unknown"

    @staticmethod
    def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
        keys = (
            "id", "name", "protocol", "address", "port", "username",
            "password", "remotePath", "createdAt", "updatedAt",
        )
        return dict(zip(keys, row))

    def close(self) -> None:
        with self._lock:
            self._conn.close()
