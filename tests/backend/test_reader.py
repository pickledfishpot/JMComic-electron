"""阅读器相关测试：反分割算法、章节分页、阅读进度、图片反分割代理."""

import hashlib
import io
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image, ImageChops

from jmcomic_backend.main import create_app
from jmcomic_backend.services.deslice import (
    deslice_image,
    get_segmentation_num,
    parse_photo_path,
)


def _make_test_image(width: int = 64, height: int = 103) -> bytes:
    """生成渐变测试图，保证每个像素行不同，便于校验顺序."""
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=95)
    return out.getvalue()


def _scramble(img_data: bytes, num: int) -> bytes:
    """按 JM 服务器规则正向切分图片：条带倒序堆叠，第一条带含高度余数.

    与 deslice_image 互为逆操作（strip 边界为 (0, ch+rem, ch+rem+ch, ...)）.
    """
    import math

    src_img = Image.open(io.BytesIO(img_data))
    width, height = src_img.size
    des_img = Image.new(src_img.mode, (width, height))

    rem = height % num
    copy_height = math.floor(height / num)
    blocks = []
    total_h = 0
    for i in range(num):
        h = copy_height * (i + 1)
        if i == num - 1:
            h += rem
        blocks.append((total_h, h))
        total_h = h

    # 反分割的逆：游标在源图上正序推进，贴到目标图的倒序条带位置
    h = 0
    for start, end in reversed(blocks):
        co_h = end - start
        des_img.paste(src_img.crop((0, h, width, h + co_h)), (0, start))
        h += co_h

    out = io.BytesIO()
    des_img.save(out, "JPEG", quality=95)
    return out.getvalue()


class TestSegmentationNum:
    def test_below_scramble_id(self):
        # epsId < scramble_id 时未分割
        assert get_segmentation_num(100, 220980, "00001") == 0

    def test_legacy_range_fixed_10(self):
        # scramble_id <= epsId < 268850 时固定 10 条
        assert get_segmentation_num(230000, 220980, "00001") == 10

    def test_mid_range_md5(self):
        # 268850 <= epsId <= 421926 时按 md5 %10 计算
        eps_id = 300000
        name = "00001"
        digest = hashlib.md5(f"{eps_id}{name}".encode()).hexdigest()
        expected = (ord(digest[-1]) % 10) * 2 + 2
        assert get_segmentation_num(eps_id, 1, name) == expected

    def test_high_range_md5(self):
        # epsId > 421926 时按 md5 %8 计算
        eps_id = 500000
        name = "00012"
        digest = hashlib.md5(f"{eps_id}{name}".encode()).hexdigest()
        expected = (ord(digest[-1]) % 8) * 2 + 2
        assert get_segmentation_num(eps_id, 1, name) == expected

    def test_legacy_high_range_md5(self):
        # 421926 及以前的高段为 %10
        eps_id = 400000
        name = "00003"
        digest = hashlib.md5(f"{eps_id}{name}".encode()).hexdigest()
        expected = (ord(digest[-1]) % 10) * 2 + 2
        assert get_segmentation_num(eps_id, 1, name) == expected


class TestDeslice:
    def test_roundtrip(self):
        # 打乱 -> 反分割应还原像素；分割数以生产函数为准
        eps_id, scramble_id, name = 300000, 1, "00001"
        num = get_segmentation_num(eps_id, scramble_id, name)
        assert num > 1
        original = _make_test_image()
        scrambled = _scramble(original, num=num)
        restored = deslice_image(scrambled, eps_id, scramble_id, name)

        img_a = Image.open(io.BytesIO(original)).convert("RGB")
        img_b = Image.open(io.BytesIO(restored)).convert("RGB")
        assert img_a.size == img_b.size
        diff = ImageChops.difference(img_a, img_b)
        # JPEG 重压缩两次允许微小误差，取 diff 最大值
        assert max(diff.getextrema(), key=lambda e: e[1])[1] <= 24

    def test_no_deslice_when_num_zero(self):
        data = _make_test_image()
        assert deslice_image(data, 100, 220980, "00001") == data

    def test_parse_photo_path(self):
        assert parse_photo_path("media/photos/123456/00001.jpg") == ("123456", "00001")
        assert parse_photo_path("media/albums/123456_3x4.jpg") is None


SAMPLE_PAGES = [
    {"index": 0, "name": "00001", "path": "media/photos/555/00001.jpg"},
    {"index": 1, "name": "00002", "path": "media/photos/555/00002.jpg"},
]

SAMPLE_DETAIL = {
    "id": "123456",
    "title": "测试漫画",
    "eps": [
        {"index": 0, "epsId": "555", "name": "第1话", "sort": 0},
        {"index": 1, "epsId": "556", "name": "第2话", "sort": 1},
    ],
}


def test_get_eps_pages(client):
    with patch("jmcomic_backend.api.routes.books.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.get_book_detail = AsyncMock(return_value=SAMPLE_DETAIL)
        instance.get_chapter_pages = AsyncMock(return_value=[p.copy() for p in SAMPLE_PAGES])
        instance.get_scramble_id = AsyncMock(return_value=421927)
        response = client.get("/api/books/123456/eps/0/pages")
    assert response.status_code == 200
    data = response.json()
    assert data["epsId"] == "555"
    assert data["scrambleId"] == 421927
    assert data["pages"][0]["url"] == "/api/images/media/photos/555/00001.jpg?scramble_id=421927"


def test_get_eps_pages_not_found(client):
    with patch("jmcomic_backend.api.routes.books.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.get_book_detail = AsyncMock(return_value=SAMPLE_DETAIL)
        response = client.get("/api/books/123456/eps/9/pages")
    assert response.status_code == 404


def test_progress_roundtrip(client):

    response = client.get("/api/books/123456/progress")
    assert response.status_code == 200
    assert response.json()["progress"] is None

    response = client.put(
        "/api/books/123456/progress", json={"epsIndex": 1, "pageIndex": 12}
    )
    assert response.status_code == 200

    response = client.get("/api/books/123456/progress")
    progress = response.json()["progress"]
    assert progress["epsIndex"] == 1
    assert progress["pageIndex"] == 12


def test_proxy_image_desliced(client):
    """带 scramble_id 的代理请求应返回反分割后的图片."""

    original = _make_test_image()
    # 与生产反分割使用同一分割数，保证打乱/还原配对
    num = get_segmentation_num(300000, 1, "00001")
    scrambled = _scramble(original, num=num)
    with patch("jmcomic_backend.api.routes.images.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.fetch_image = AsyncMock(return_value=(scrambled, "image/jpeg"))
        response = client.get("/api/images/media/photos/300000/00001.jpg?scramble_id=1")
    assert response.status_code == 200

    img_a = Image.open(io.BytesIO(original)).convert("RGB")
    img_b = Image.open(io.BytesIO(response.content)).convert("RGB")
    diff = ImageChops.difference(img_a, img_b)
    assert max(diff.getextrema(), key=lambda e: e[1])[1] <= 24


def test_proxy_image_cached(client):
    """第二次请求应命中磁盘缓存，不再访问远端."""

    with patch("jmcomic_backend.api.routes.images.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.fetch_image = AsyncMock(return_value=(b"fake-image-data", "image/jpeg"))
        response1 = client.get("/api/images/media/albums/123456_3x4.jpg")
        response2 = client.get("/api/images/media/albums/123456_3x4.jpg")
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response2.content == b"fake-image-data"
    assert instance.fetch_image.call_count == 1
