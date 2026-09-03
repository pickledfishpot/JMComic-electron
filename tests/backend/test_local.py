"""本地图库测试：目录本/压缩本扫描、分页、图片读取、阅读进度."""

import base64
import zipfile

from fastapi.testclient import TestClient

from jmcomic_backend.main import create_app


def _png_bytes() -> bytes:
    """最小合法 PNG（1x1）."""
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def _make_download_book(root, book_id="123456", chapters=2, pages=3):
    """模拟下载产物：downloads/{book_id}/{001..}/{0001..}.jpg."""
    book_dir = root / "downloads" / book_id
    for ch in range(chapters):
        eps_dir = book_dir / f"{ch + 1:03d}"
        eps_dir.mkdir(parents=True)
        for pg in range(pages):
            (eps_dir / f"{pg + 1:04d}.jpg").write_bytes(_png_bytes())
    return book_dir


def _make_zip_book(root, name="zipbook.zip", pages=3):
    path = root / "downloads" / name
    with zipfile.ZipFile(path, "w") as zf:
        for pg in range(pages):
            zf.writestr(f"chapter1/{pg + 1:03d}.png", _png_bytes())
    return path


def test_scan_download_layout(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        _make_download_book(tmp_path, chapters=2, pages=3)
        resp = client.post("/api/local/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        book = data["books"][0]
        assert book["title"] == "123456"
        assert len(book["eps"]) == 2
        assert all(ep["pageCount"] == 3 for ep in book["eps"])
        assert book["pageCount"] == 6


def test_scan_zip_book(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        _make_zip_book(tmp_path)
        books = client.post("/api/local/scan").json()["books"]
        assert len(books) == 1
        assert books[0]["isZip"] is True
        assert books[0]["title"] == "zipbook"
        assert books[0]["pageCount"] == 3


def test_pages_and_image_read(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        _make_download_book(tmp_path, pages=2)
        book_id = client.post("/api/local/scan").json()["books"][0]["id"]

        pages = client.get(f"/api/local/books/{book_id}/eps/1/pages").json()
        assert len(pages["pages"]) == 2
        assert pages["epsIndex"] == 1
        assert pages["pages"][0]["url"].startswith("/api/local/images/")

        img = client.get(pages["pages"][0]["url"])
        assert img.status_code == 200
        assert img.headers["content-type"].startswith("image/")
        assert img.content == _png_bytes()


def test_zip_image_read(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        _make_zip_book(tmp_path)
        book_id = client.post("/api/local/scan").json()["books"][0]["id"]
        img = client.get(f"/api/local/images/{book_id}/0/0")
        assert img.status_code == 200
        assert img.content == _png_bytes()


def test_local_progress(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        _make_download_book(tmp_path, pages=2)
        book_id = client.post("/api/local/scan").json()["books"][0]["id"]

        assert client.get(f"/api/local/books/{book_id}/progress").json()["progress"] is None
        client.put(
            f"/api/local/books/{book_id}/progress",
            json={"epsIndex": 1, "pageIndex": 1, "title": "123456"},
        )
        progress = client.get(f"/api/local/books/{book_id}/progress").json()["progress"]
        assert progress["epsIndex"] == 1
        assert progress["pageIndex"] == 1

        # local: 前缀不污染普通历史
        history = client.get("/api/history").json()
        assert all(not item["bookId"].startswith("local:") for item in history["items"])


def test_missing_returns_404(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/local/books/nope").status_code == 404
        assert client.get("/api/local/books/nope/eps/0/pages").status_code == 404
        assert client.get("/api/local/images/nope/0/0").status_code == 404


def test_extra_dirs_setting(tmp_path):
    """settings.local.dirs 中的额外目录也被扫描."""
    extra = tmp_path / "extra"
    book_dir = extra / "manga"
    book_dir.mkdir(parents=True)
    (book_dir / "001.png").write_bytes(_png_bytes())
    (book_dir / "002.png").write_bytes(_png_bytes())

    app = create_app(tmp_path)
    with TestClient(app) as client:
        settings = client.get("/api/settings").json()
        settings["local"]["dirs"] = [str(extra)]
        client.put("/api/settings", json=settings)
        books = client.post("/api/local/scan").json()["books"]
        assert any(b["title"] == "manga" for b in books)


def test_natural_sort():
    from jmcomic_backend.services.local_library import _natural_key

    names = ["page10.png", "page2.png", "page1.png"]
    assert sorted(names, key=_natural_key) == [
        "page1.png",
        "page2.png",
        "page10.png",
    ]
