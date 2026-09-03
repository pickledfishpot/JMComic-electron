"""本地图库扫描与图片读取，移植自原 JMComic-qt 的 task_local.py.

支持三种形态：
1. 目录本：目录内直接是图片（单章节），或子目录各含图片（多章节）
2. 压缩本：.zip / .cbz 文件，内部图片按目录分组取图片数最多的一组
3. 下载产物：download_dir/{book_id}/{章节:03d}/{页:04d}.{ext} 天然符合目录本规则

扫描结果只保留在内存（id = 路径 md5），图片按需提供原始字节.
"""

from __future__ import annotations

import hashlib
import logging
import re
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ALL_PICTURE_FORMATS = ("jpg", "jpeg", "webp", "gif", "apng", "png", "bmp")
ARCHIVE_FORMATS = ("zip", "cbz")

_PICTURE_RE = re.compile(r"\.(\w+)$")


def _natural_key(name: str) -> list[Any]:
    """自然排序键：数字段按数值比较，替代原项目的 natsort 依赖."""
    parts = re.split(r"(\d+)", name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def _is_picture(name: str) -> bool:
    mo = _PICTURE_RE.search(name)
    return bool(mo) and mo.group(1).lower() in ALL_PICTURE_FORMATS


class LocalBook:
    """一本本地漫画：含若干章节，每章是图片路径列表."""

    def __init__(self, book_id: str, title: str, root: Path) -> None:
        self.id = book_id
        self.title = title
        self.root = root
        self.is_zip = root.suffix.lower().lstrip(".") in ARCHIVE_FORMATS
        # eps: [{"index": 0, "name": str, "files": [str, ...]}]
        # files 对目录本是相对 root 的路径，对 zip 是压缩包内名
        self.eps: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "isZip": self.is_zip,
            "path": str(self.root),
            "eps": [
                {"index": ep["index"], "name": ep["name"], "pageCount": len(ep["files"])}
                for ep in self.eps
            ],
            "pageCount": sum(len(ep["files"]) for ep in self.eps),
        }


class LocalLibrary:
    """本地图库：扫描目录建立索引，按 id 提供分页与图片字节."""

    def __init__(self) -> None:
        self._books: dict[str, LocalBook] = {}

    def scan(self, roots: list[Path]) -> list[dict[str, Any]]:
        """扫描给定目录列表，返回书籍列表（自然排序）."""
        self._books = {}
        for root in roots:
            root = root.expanduser()
            if not root.is_dir():
                logger.warning("local library root not a dir: %s", root)
                continue
            try:
                for book in self._scan_root(root):
                    self._books[book.id] = book
            except Exception as exc:
                logger.error("scan local library %s failed: %s", root, exc)
        return self.list_books()

    def list_books(self) -> list[dict[str, Any]]:
        books = [book.to_dict() for book in self._books.values()]
        books.sort(key=lambda item: item["title"].lower())
        return books

    def get_book(self, book_id: str) -> LocalBook | None:
        return self._books.get(book_id)

    def get_eps_pages(self, book_id: str, eps_index: int) -> dict[str, Any] | None:
        """返回与远端 /eps/{idx}/pages 兼容的分页结构（url 指向本地图片接口）."""
        book = self._books.get(book_id)
        if book is None or eps_index < 0 or eps_index >= len(book.eps):
            return None
        ep = book.eps[eps_index]
        pages = [
            {
                "index": idx,
                "name": Path(name).stem,
                "url": f"/api/local/images/{book_id}/{eps_index}/{idx}",
            }
            for idx, name in enumerate(ep["files"])
        ]
        return {"bookId": book_id, "epsIndex": eps_index, "pages": pages}

    def read_page(self, book_id: str, eps_index: int, page_index: int) -> tuple[bytes, str] | None:
        """读取单页图片字节，返回 (data, content_type)."""
        book = self._books.get(book_id)
        if book is None or eps_index < 0 or eps_index >= len(book.eps):
            return None
        files = book.eps[eps_index]["files"]
        if page_index < 0 or page_index >= len(files):
            return None
        name = files[page_index]
        ext = name.rsplit(".", 1)[-1].lower()
        content_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        try:
            if book.is_zip:
                with zipfile.ZipFile(book.root, "r") as zf:
                    return zf.read(name), content_type
            return (book.root / name).read_bytes(), content_type
        except Exception as exc:
            logger.error("read local page %s/%s/%s failed: %s", book_id, eps_index, page_index, exc)
            return None

    # ---------------- 扫描逻辑（移植自 task_local.py） ----------------

    def _scan_root(self, root: Path) -> list[LocalBook]:
        """扫描一个根目录：压缩包直接成书，子目录各解析成书（多章节目录合并为一本）."""
        books: list[LocalBook] = []
        try:
            entries = sorted(root.iterdir(), key=lambda p: _natural_key(p.name))
        except OSError as exc:
            logger.error("list dir %s failed: %s", root, exc)
            return books
        for entry in entries:
            try:
                if entry.is_file() and entry.suffix.lower().lstrip(".") in ARCHIVE_FORMATS:
                    book = self._parse_zip(entry)
                    if book is not None:
                        books.append(book)
                elif entry.is_dir():
                    book = self._parse_dir_as_book(entry)
                    if book is not None:
                        books.append(book)
            except Exception as exc:
                logger.error("parse local entry %s failed: %s", entry, exc)
        return books

    def _parse_dir_as_book(self, path: Path) -> LocalBook | None:
        """把一个目录解析成一本书.

        目录本身图片多 -> 单章本书（扁平）；否则逐子目录解析，
        每个含图片的子目录作为一话合并为一本（对应下载产物 书/001/页 布局）.
        """
        pics = self._direct_pictures(path)
        if len(pics) > 1:
            book = self._new_book(path)
            book.eps.append({"index": 0, "name": "", "files": pics})
            return book

        try:
            sub_dirs = sorted(
                (e for e in path.iterdir() if e.is_dir()),
                key=lambda p: _natural_key(p.name),
            )
        except OSError as exc:
            logger.error("list dir %s failed: %s", path, exc)
            return None

        eps: list[dict[str, Any]] = []
        eps.extend(self._collect_eps(sub_dirs, path))
        # 深层兜底：子目录没有图片时继续向下找（如 书/卷/话/页 结构）
        if not eps:
            for sub in sub_dirs:
                book = self._parse_dir_as_book(sub)
                if book is not None:
                    return book
            return None
        book = self._new_book(path)
        book.eps = eps
        return book

    def _collect_eps(self, dirs: list[Path], book_root: Path) -> list[dict[str, Any]]:
        """一组同级目录各成一话，files 统一为相对 book_root 的路径."""
        eps: list[dict[str, Any]] = []
        for sub in dirs:
            pics = self._direct_pictures(sub)
            if pics:
                eps.append({
                    "index": len(eps),
                    "name": sub.name,
                    "files": [f"{sub.name}/{name}" for name in pics],
                })
                continue
            try:
                nested = sorted(
                    (e for e in sub.iterdir() if e.is_dir()),
                    key=lambda p: _natural_key(p.name),
                )
            except OSError:
                continue
            eps.extend(self._collect_eps(nested, book_root))
        return eps

    @staticmethod
    def _direct_pictures(path: Path) -> list[str]:
        try:
            return sorted(
                (e.name for e in path.iterdir() if e.is_file() and _is_picture(e.name)),
                key=_natural_key,
            )
        except OSError as exc:
            logger.error("list dir %s failed: %s", path, exc)
            return []

    def _parse_zip(self, path: Path) -> LocalBook | None:
        """压缩本：内部图片按目录分组，取图片数最多的一组（移植 ParseBookInfoByFile）."""
        if not zipfile.is_zipfile(path):
            return None
        try:
            with zipfile.ZipFile(path, "r") as zf:
                groups: dict[str, list[str]] = {}
                for info in zf.infolist():
                    if info.is_dir() or not _is_picture(info.filename):
                        continue
                    # 统一为 posix 风格，zipfile 读入也用同一格式
                    groups.setdefault(str(Path(info.filename).parent), []).append(
                        info.filename
                    )
        except (zipfile.BadZipFile, RuntimeError) as exc:
            logger.warning("bad zip %s: %s", path, exc)
            return None
        best: list[str] = []
        inner_dir = ""
        for dir_name, names in groups.items():
            if len(names) > len(best):
                inner_dir = dir_name
                best = names
        if len(best) <= 1:
            return None
        best.sort(key=_natural_key)
        book = self._new_book(path)
        title = path.name
        for suffix in (".zip", ".cbz"):
            if title.lower().endswith(suffix):
                title = title[: -len(suffix)]
        book.title = title
        book.eps.append({"index": 0, "name": "", "files": best})
        return book

    @staticmethod
    def _new_book(path: Path) -> LocalBook:
        book_id = hashlib.md5(str(path.resolve()).encode("utf-8")).hexdigest()
        return LocalBook(book_id, path.name, path)
