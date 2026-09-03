"""JMComic API 客户端，移植自原 JMComic-qt 的 req.py / server.py / tool.py.

去 Qt 化，使用 httpx 进行异步 HTTP 请求，并复用 jmcomic 库的 token 生成与响应解密逻辑.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import time
from typing import Any
from urllib.parse import quote

import httpx
from jmcomic import JmCryptoTool

from jmcomic_backend.services.deslice import DEFAULT_SCRAMBLE_ID

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

# 登录态 cookies：单用户桌面应用，登录后由 SessionManager 写入默认 cookies
_default_cookies: dict[str, str] = {}

# 代理：由设置页配置后写入，新建的 JmClient 自动携带
_default_proxy: str = ""


def set_default_cookies(cookies: dict[str, str]) -> None:
    """设置全局默认 cookies，新建的 JmClient 自动携带."""
    global _default_cookies
    _default_cookies = dict(cookies)


def set_default_proxy(proxy_url: str) -> None:
    """设置全局默认代理（http(s):// 或 socks5(h)://），空串表示直连."""
    global _default_proxy
    _default_proxy = proxy_url.strip()


class JmApiError(Exception):
    """JM API 返回业务错误（code != 200 等）."""


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


def _parse_chapter_pages(raw: dict[str, Any], eps_id: str) -> list[dict[str, Any]]:
    """移植自 tool.py ToolUtil.ParseBookEpsInfo2：按文件名数字排序生成页列表.

    文件名中的数字即真实页码，需排序后连续编号；path 为图片代理用的相对路径.
    """
    named: list[tuple[int, str]] = []
    for name in raw.get("images", []):
        mo = re.search(r"\d+", name)
        if not mo:
            continue
        named.append((int(mo.group()), name))
    named.sort(key=lambda item: item[0])
    return [
        {
            "index": idx,
            "name": name.rsplit(".", 1)[0],
            "path": f"media/photos/{eps_id}/{name}",
        }
        for idx, (_, name) in enumerate(named)
    ]


def _parse_scramble_id(html: str) -> int:
    """移植自 tool.py ToolUtil.ParseBookEpsScramble：从 chapter_view_template HTML 提取."""
    mo = re.search(r"(?<=var scramble_id = )\w+", html)
    if not mo:
        logger.warning("scramble_id not found in chapter_view_template, fallback to %s", DEFAULT_SCRAMBLE_ID)
        return DEFAULT_SCRAMBLE_ID
    return int(mo.group())


def _parse_login(raw: dict[str, Any]) -> dict[str, Any]:
    """移植自 tool.py ToolUtil.ParseLogin2."""
    return {
        "uid": str(raw.get("uid", "")),
        "username": raw.get("username", ""),
        "title": raw.get("level_name", ""),
        "level": str(raw.get("level", "")),
        "coin": str(raw.get("coin", "")),
        "gender": raw.get("gender", ""),
        "favorites": str(raw.get("album_favorites", "")),
        "favorites_max": str(raw.get("album_favorites_max", "")),
        "exp": int(raw.get("exp", 0)),
        "next_exp": int(raw.get("nextLevelExp", 0)),
    }


def _parse_favorites(raw: dict[str, Any]) -> dict[str, Any]:
    """移植自 tool.py ToolUtil.ParseFavoritesReq2."""
    folders = [
        {"id": str(item.get("FID", "")), "name": item.get("name", "")}
        for item in raw.get("folder_list", [])
    ]
    return {
        "total": int(raw.get("total", 0)),
        "count": int(raw.get("count", 0)),
        "books": [_parse_book_info(item) for item in raw.get("list", [])],
        "folders": folders,
    }


def _parse_msg(raw: Any) -> dict[str, Any]:
    """移植自 tool.py ToolUtil.ParseMsgReq2：{status: ok, msg}."""
    if isinstance(raw, dict):
        return {"ok": raw.get("status") == "ok", "message": raw.get("msg", "")}
    return {"ok": False, "message": ""}


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

    def __init__(
        self,
        api_index: int = 0,
        img_index: int = 0,
        cookies: dict[str, str] | None = None,
    ) -> None:
        self.api_index = api_index
        self.img_index = img_index
        self._cookies = dict(cookies) if cookies is not None else dict(_default_cookies)
        mounts: dict[str, httpx.AsyncHTTPTransport] | None = None
        if _default_proxy:
            transport = httpx.AsyncHTTPTransport(proxy=_default_proxy)
            mounts = {"http://": transport, "https://": transport}
        self._client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            mounts=mounts,
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
        if self._cookies and kwargs.get("headers") is not None:
            headers = dict(kwargs["headers"])
            headers["Cookie"] = "; ".join(
                f"{key}={value}" for key, value in self._cookies.items()
            )
            kwargs["headers"] = headers
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

    async def _get_api_decoded(self, path: str, params: dict[str, Any]) -> Any:
        """GET JM API 并解密 data 字段，code != 200 抛 JmApiError."""
        ts = str(int(time.time()))
        url = _api_url(path, params, self.api_index)
        headers = _build_headers(int(ts))
        response = await self._request_with_retry("GET", url, headers=headers)
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code") != 200:
            raise JmApiError(
                str(payload.get("errorMsg") or payload.get("message") or f"code={payload.get('code')}")
            )
        return _decode_response(payload, ts)

    async def _post_api_decoded(self, path: str, params: dict[str, Any]) -> Any:
        """POST 表单到 JM API 并解密 data 字段，code != 200 抛 JmApiError."""
        ts = str(int(time.time()))
        url = _api_url(path, {}, self.api_index)
        headers = _build_headers(int(ts))
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = await self._request_with_retry(
            "POST", url, headers=headers, content=_dict_to_url(params)
        )
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code") != 200:
            raise JmApiError(
                str(payload.get("errorMsg") or payload.get("message") or f"code={payload.get('code')}")
            )
        return _decode_response(payload, ts)

    async def login(self, username: str, password: str) -> tuple[dict[str, Any], dict[str, str]]:
        """登录，返回 (用户信息, cookies)."""
        ts = str(int(time.time()))
        url = _api_url("/login", {}, self.api_index)
        headers = _build_headers(int(ts))
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = _dict_to_url({"username": username, "password": password})
        response = await self._request_with_retry("POST", url, headers=headers, content=body)
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("code") != 200:
            raise JmApiError(
                str(
                    (payload or {}).get("errorMsg")
                    or (payload or {}).get("message")
                    or "登录失败，请检查用户名或密码"
                )
            )
        data = _decode_response(payload, ts)
        if not isinstance(data, dict):
            raise JmApiError("unexpected login response")
        return _parse_login(data), dict(response.cookies)

    async def get_favorites(
        self, page: int = 1, sort: str = "mr", folder_id: str = "0"
    ) -> dict[str, Any]:
        """获取收藏列表，移植自 GetFavoritesReq2."""
        data = await self._get_api_decoded(
            "/favorite", {"page": str(page), "folder_id": folder_id, "o": sort}
        )
        if not isinstance(data, dict):
            raise ValueError(f"unexpected favorites response type: {type(data)}")
        return _parse_favorites(data)

    async def toggle_favorite(self, book_id: str | int) -> dict[str, Any]:
        """添加/取消收藏（同一接口切换），移植自 AddAndDelFavoritesReq2."""
        data = await self._post_api_decoded("/favorite", {"aid": str(book_id)})
        return _parse_msg(data)

    async def add_favorite_folder(self, name: str) -> dict[str, Any]:
        data = await self._post_api_decoded(
            "/favorite_folder", {"folder_name": name, "type": "add"}
        )
        return _parse_msg(data)

    async def delete_favorite_folder(self, folder_id: str | int) -> dict[str, Any]:
        data = await self._post_api_decoded(
            "/favorite_folder", {"folder_id": str(folder_id), "type": "del"}
        )
        return _parse_msg(data)

    async def move_favorite_folder(
        self, book_id: str | int, folder_id: str | int
    ) -> dict[str, Any]:
        data = await self._post_api_decoded(
            "/favorite_folder",
            {"folder_id": str(folder_id), "type": "move", "aid": str(book_id)},
        )
        return _parse_msg(data)

    async def get_watch_history(self, page: int = 1) -> dict[str, Any]:
        """获取 JM 服务器观看记录，移植自 GetHistoryReq2."""
        data = await self._get_api_decoded("/watch_list", {"page": str(page)})
        if not isinstance(data, dict):
            raise ValueError(f"unexpected watch_list response type: {type(data)}")
        return {
            "total": int(data.get("total", 0)),
            "books": [_parse_book_info(item) for item in data.get("list", [])],
        }

    async def get_chapter_pages(self, eps_id: str | int) -> list[dict[str, Any]]:
        """获取章节图片列表，返回按页码排序的 [{index, name, path}]."""
        ts = str(int(time.time()))
        url = _api_url("/chapter", {"comicName": "", "skip": "", "id": str(eps_id)}, self.api_index)
        headers = _build_headers(int(ts))
        logger.debug("GET %s", url)
        response = await self._request_with_retry("GET", url, headers=headers)
        payload = _decode_response(response.json(), ts)
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected chapter response type: {type(payload)}")
        return _parse_chapter_pages(payload, str(eps_id))

    async def get_scramble_id(self, eps_id: str | int) -> int:
        """获取章节反分割参数 scramble_id（chapter_view_template 返回 HTML）."""
        url = _api_url(
            "/chapter_view_template",
            {"id": str(eps_id), "mode": "vertical", "page": "0", "app_img_shunt": "NaN"},
            self.api_index,
        )
        headers = _build_headers()
        logger.debug("GET %s", url)
        response = await self._request_with_retry("GET", url, headers=headers)
        return _parse_scramble_id(response.text)

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
