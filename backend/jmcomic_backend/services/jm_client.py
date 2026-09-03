"""JMComic API 客户端，移植自原 JMComic-qt 的 req.py / server.py / tool.py.

去 Qt 化，使用 httpx 进行异步 HTTP 请求，并复用 jmcomic 库的 token 生成与响应解密逻辑.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx
from jmcomic import JmCryptoTool

logger = logging.getLogger(__name__)

# 移植自原项目 config/global_config.py 的默认域名列表
API_BASE_URLS = [
    "https://www.cdnhjk.net",
    "https://www.cdngwc.cc",
    "https://www.cdngwc.net",
    "https://www.cdngwc.club",
]

IMG_BASE_URLS = [
    "https://cdn-msp.jmapiproxy1.cc",
    "https://cdn-msp.jmapiproxy3.cc",
    "https://cdn-msp.jmapinodeudzn.net",
    "https://cdn-msp.jmdanjonproxy.xyz",
]

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
IMG_TIMEOUT = httpx.Timeout(30.0, connect=5.0)

# JM 服务器不稳定，API 请求最多重试 3 次
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0


def _dict_to_url(params: dict[str, Any]) -> str:
    """移植自 tool.py ToolUtil.DictToUrl."""
    parts = []
    for key, value in params.items():
        parts.append(f"{quote(str(key))}={quote(str(value))}")
    return "&".join(parts)


def _build_headers(ts: int | None = None) -> dict[str, str]:
    """使用 jmcomic 的 JmCryptoTool 生成 APP 请求头."""
    now = ts if ts is not None else int(time.time())
    token, tokenparam = JmCryptoTool.token_and_tokenparam(str(now))
    return {
        "tokenparam": tokenparam,
        "token": token,
        "Accept-Encoding": "gzip, deflate",
        "user-agent": (
            "Mozilla/5.0 (Linux; Android 9; V1938CT Build/PQ3A.190705.11211812; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36"
        ),
    }


def _api_url(path: str, params: dict[str, Any] | None = None, index: int = 0) -> str:
    base = API_BASE_URLS[index % len(API_BASE_URLS)]
    url = f"{base}{path}"
    if params:
        query = _dict_to_url(params)
        if query:
            url = f"{url}/?{query}"
    return url


def _img_url(path: str, index: int = 0) -> str:
    base = IMG_BASE_URLS[index % len(IMG_BASE_URLS)]
    if path.startswith("/"):
        return f"{base}{path}"
    return f"{base}/{path}"


def _decode_response(payload: Any, ts: str) -> Any:
    """解密 JM API 响应.

    新版接口返回 {"code": 200, "data": "base64加密字符串"}，
    需要先 base64 再 AES-ECB 解密；解密后可能是对象也可能是数组.
    """
    if isinstance(payload, dict) and "data" in payload:
        encoded = payload.get("data")
        if isinstance(encoded, str) and encoded:
            try:
                decoded_text = JmCryptoTool.decode_resp_data(encoded, ts)
                return json.loads(decoded_text)
            except Exception as exc:
                logger.warning("Failed to decode JM response data: %s", exc)
    return payload


def _parse_book_info(raw: dict[str, Any]) -> dict[str, Any]:
    """移植自 tool.py ToolUtil.ParseBookInfo，精简字段."""
    book_id = raw.get("id")
    category = raw.get("category", {}) or {}
    sub_category = raw.get("category_sub", {}) or {}
    categories: list[str] = []
    if category.get("title"):
        categories.append(category["title"])
    if sub_category.get("title"):
        categories.append(sub_category["title"])

    author = raw.get("author")
    author_list = author if isinstance(author, list) else [author] if author else []

    return {
        "id": book_id,
        "title": raw.get("name"),
        "author": author,
        "authorList": author_list,
        "tags": raw.get("tags", []),
        "categories": categories,
        "coverUrl": f"/api/images/media/albums/{book_id}_3x4.jpg",
        "likes": raw.get("likes"),
        "views": raw.get("total_views"),
    }


def _parse_index(raw: Any) -> dict[str, list[dict[str, Any]]]:
    """移植自 tool.py ToolUtil.ParseIndex2，兼容加密后的数组/对象."""
    result: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(raw, list):
        return result
    for section in raw:
        if isinstance(section, dict):
            title = section.get("title", "未知")
            result[title] = [_parse_book_info(item) for item in section.get("content", [])]
    return result


def _parse_book_detail(raw: dict[str, Any]) -> dict[str, Any]:
    """移植自 tool.py ToolUtil.ParseBookInfo2，增加 eps 列表."""
    book_id = raw.get("id")
    series = raw.get("series", []) or []
    eps: list[dict[str, Any]] = []
    if series:
        for idx, item in enumerate(series):
            eps.append({
                "index": idx,
                "epsId": item.get("id"),
                "name": item.get("name"),
                "sort": int(item.get("sort", 0)),
            })
    else:
        eps.append({
            "index": 0,
            "epsId": book_id,
            "name": "",
            "sort": 0,
        })

    author = raw.get("author")
    author_list = author if isinstance(author, list) else [author] if author else []

    return {
        "id": book_id,
        "title": raw.get("name"),
        "description": raw.get("description"),
        "authorList": author_list,
        "tags": raw.get("tags", []),
        "categories": [c for c in [raw.get("category", {}).get("title"), raw.get("category_sub", {}).get("title")] if c],
        "coverUrl": f"/api/images/media/albums/{book_id}_3x4.jpg",
        "likes": raw.get("likes"),
        "views": raw.get("total_views"),
        "commentTotal": int(raw.get("comment_total", 0)),
        "isFavorite": raw.get("is_favorite"),
        "eps": eps,
    }


def _parse_search(raw: dict[str, Any]) -> dict[str, Any]:
    """移植自 tool.py ToolUtil.ParseSearch2."""
    return {
        "total": int(raw.get("total", 0)),
        "books": [_parse_book_info(item) for item in raw.get("content", [])],
    }


def _parse_categories(raw: dict[str, Any]) -> dict[str, Any]:
    """移植自 tool.py ToolUtil.ParseCategory2."""
    categories: list[dict[str, Any]] = []
    for item in raw.get("categories", []):
        categories.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "slug": item.get("slug"),
            "type": item.get("type"),
            "total": int(item.get("total_albums", 0)),
        })
    blocks: dict[str, Any] = {}
    for block in raw.get("blocks", []):
        blocks[block.get("title", "未知")] = block.get("content", [])
    return {"categories": categories, "blocks": blocks}


def _parse_comment(raw: dict[str, Any]) -> dict[str, Any]:
    """移植自 tool.py ToolUtil.ParseBookComment."""
    comments: list[dict[str, Any]] = []
    for item in raw.get("list", []):
        photo = item.get("photo")
        head_url = ""
        if photo and photo not in ("nopic-Male.gif", "nopic-Female.gif"):
            head_url = f"/api/images/media/users/{photo}"
        sub_comments: list[dict[str, Any]] = []
        for sub in item.get("replys", []):
            sub_photo = sub.get("photo")
            sub_head_url = ""
            if sub_photo and sub_photo not in ("nopic-Male.gif", "nopic-Female.gif"):
                sub_head_url = f"/api/images/media/users/{sub_photo}"
            sub_comments.append({
                "id": sub.get("CID"),
                "uid": sub.get("UID"),
                "name": sub.get("username"),
                "title": sub.get("expinfo", {}).get("level_name"),
                "level": sub.get("expinfo", {}).get("level"),
                "content": sub.get("content"),
                "headUrl": sub_head_url,
                "like": sub.get("likes"),
                "date": sub.get("addtime"),
                "linkBookName": sub.get("name"),
                "linkBookId": sub.get("AID"),
            })
        comments.append({
            "id": item.get("CID"),
            "uid": item.get("UID"),
            "name": item.get("username"),
            "title": item.get("expinfo", {}).get("level_name"),
            "level": item.get("expinfo", {}).get("level"),
            "content": item.get("content"),
            "headUrl": head_url,
            "like": item.get("likes"),
            "date": item.get("addtime"),
            "linkBookName": item.get("name"),
            "linkBookId": item.get("AID"),
            "subComments": sub_comments,
        })
    return {"total": int(raw.get("total", 0)), "comments": comments}


class JmClient:
    """JMComic 异步 HTTP 客户端."""

    def __init__(self, api_index: int = 0, img_index: int = 0) -> None:
        self.api_index = api_index
        self.img_index = img_index
        self._client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """带重试的 HTTP 请求，最多 MAX_RETRIES 次.

        JM 服务器不太稳定，超时或网络抖动时自动重试；
        若连续失败则抛出最后一次异常，由上层返回 502 并知会用户.
        """
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                logger.warning("JM request failed (attempt %d/%d): %s -> %s", attempt, MAX_RETRIES, url, exc)
                if attempt < MAX_RETRIES:
                    await self._sleep(RETRY_DELAY_SECONDS)
        raise last_exc or RuntimeError("unknown request error")

    async def _sleep(self, seconds: float) -> None:
        """独立方法，便于测试时 monkeypatch 跳过等待."""
        await asyncio.sleep(seconds)

    async def get_index(self, page: str = "0") -> dict[str, list[dict[str, Any]]]:
        """获取首页推荐."""
        ts = str(int(time.time()))
        url = _api_url("/promote", {"page": page}, self.api_index)
        headers = _build_headers(int(ts))
        logger.debug("GET %s", url)
        response = await self._request_with_retry("GET", url, headers=headers)
        payload = _decode_response(response.json(), ts)
        return _parse_index(payload)

    async def get_book_detail(self, book_id: str | int) -> dict[str, Any]:
        """获取书籍详情."""
        ts = str(int(time.time()))
        url = _api_url("/album", {"comicName": "", "id": str(book_id)}, self.api_index)
        headers = _build_headers(int(ts))
        logger.debug("GET %s", url)
        response = await self._request_with_retry("GET", url, headers=headers)
        payload = _decode_response(response.json(), ts)
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected album response type: {type(payload)}")
        return _parse_book_detail(payload)

    async def search(self, query: str, page: int = 1, sort: str = "mr") -> dict[str, Any]:
        """搜索本子.

        sort 可选值: mr(最新), mv(最多点击), mp(最多图片), tf(最多爱心).
        """
        ts = str(int(time.time()))
        params: dict[str, Any] = {"search_query": query}
        if page > 1:
            params["page"] = str(page)
        if sort:
            params["o"] = sort
        url = _api_url("/search", params, self.api_index)
        headers = _build_headers(int(ts))
        logger.debug("GET %s", url)
        response = await self._request_with_retry("GET", url, headers=headers)
        payload = _decode_response(response.json(), ts)
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected search response type: {type(payload)}")
        return _parse_search(payload)

    async def get_categories(self) -> dict[str, Any]:
        """获取分类列表与推荐区块."""
        ts = str(int(time.time()))
        url = _api_url("/categories", {}, self.api_index)
        headers = _build_headers(int(ts))
        logger.debug("GET %s", url)
        response = await self._request_with_retry("GET", url, headers=headers)
        payload = _decode_response(response.json(), ts)
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected categories response type: {type(payload)}")
        return _parse_categories(payload)

    async def get_category_books(self, category: str = "0", page: int = 1, sort: str = "mr") -> dict[str, Any]:
        """按分类筛选本子.

        category 可选值: 0(全部), doujin, single, short, another, hanman, meiman, doujin_cosplay, 3D.
        sort 可选值: mr, mv, mv_m, mv_w, mv_t, mp, tf.
        """
        ts = str(int(time.time()))
        params: dict[str, Any] = {}
        if page > 1:
            params["page"] = str(page)
        if sort:
            params["o"] = sort
        if category:
            params["c"] = category
        url = _api_url("/categories/filter", params, self.api_index)
        headers = _build_headers(int(ts))
        logger.debug("GET %s", url)
        response = await self._request_with_retry("GET", url, headers=headers)
        payload = _decode_response(response.json(), ts)
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected category books response type: {type(payload)}")
        return _parse_search(payload)

    async def get_book_comments(self, book_id: str | int, page: int = 1) -> dict[str, Any]:
        """获取书籍评论."""
        ts = str(int(time.time()))
        params: dict[str, Any] = {"mode": "manhua", "aid": str(book_id), "page": str(page)}
        url = _api_url("/forum", params, self.api_index)
        headers = _build_headers(int(ts))
        logger.debug("GET %s", url)
        response = await self._request_with_retry("GET", url, headers=headers)
        payload = _decode_response(response.json(), ts)
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected comments response type: {type(payload)}")
        return _parse_comment(payload)

    async def fetch_image(self, path: str) -> tuple[bytes, str]:
        """拉取远端图片，返回 (bytes, content_type)."""
        url = _img_url(path, self.img_index)
        headers = {
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "user-agent": (
                "Mozilla/5.0 (Linux; Android 9; V1938CT Build/PQ3A.190705.11211812; wv) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36"
            ),
        }
        logger.debug("GET image %s", url)
        response = await self._request_with_retry("GET", url, headers=headers, timeout=IMG_TIMEOUT)
        return response.content, response.headers.get("content-type", "image/jpeg")

    async def __aenter__(self) -> "JmClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
