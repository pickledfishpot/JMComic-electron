"""NAS 与工具 API 测试."""

import base64

from fastapi.testclient import TestClient

from jmcomic_backend.main import create_app


def _png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def test_nas_crud(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        resp = client.post(
            "/api/nas",
            json={
                "name": "我的网盘",
                "protocol": "webdav",
                "address": "https://dav.example.com",
                "username": "u",
                "password": "p",
                "remote_path": "/comics",
            },
        )
        assert resp.status_code == 200
        nas_id = resp.json()["id"]

        configs = client.get("/api/nas").json()["configs"]
        assert len(configs) == 1
        assert configs[0]["password"] == "******"  # 列表不回显明文密码

        resp = client.put(f"/api/nas/{nas_id}", json={"name": "改名"})
        assert resp.json()["name"] == "改名"
        # 掩码密码不覆盖原值
        resp = client.put(f"/api/nas/{nas_id}", json={"password": "******"})
        assert client.get("/api/nas").json()["configs"][0]["password"] == "******"

        assert client.delete(f"/api/nas/{nas_id}").json()["ok"] is True
        assert client.get("/api/nas").json()["configs"] == []


def test_nas_bad_protocol(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        resp = client.post("/api/nas", json={"name": "x", "protocol": "ftp"})
        assert resp.status_code == 400


def test_nas_local_upload(tmp_path):
    """local 协议：上传下载产物到指定目录."""
    app = create_app(tmp_path)
    with TestClient(app) as client:
        # 造一本已下载的书
        book_dir = tmp_path / "downloads" / "999" / "001"
        book_dir.mkdir(parents=True)
        (book_dir / "0001.jpg").write_bytes(_png_bytes())

        target = tmp_path / "nas-target"
        resp = client.post(
            "/api/nas",
            json={"name": "backup", "protocol": "local", "remote_path": str(target)},
        )
        nas_id = resp.json()["id"]

        resp = client.post(
            f"/api/nas/{nas_id}/upload", json={"bookId": "999", "bookTitle": "测试书"}
        )
        assert resp.status_code == 200
        assert resp.json()["files"] == 1
        assert (target / "测试书" / "001" / "0001.jpg").read_bytes() == _png_bytes()


def test_nas_local_test_and_missing_book(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        resp = client.post(
            "/api/nas",
            json={"name": "t", "protocol": "local", "remote_path": str(tmp_path / "x")},
        )
        nas_id = resp.json()["id"]
        assert client.post(f"/api/nas/{nas_id}/test").json()["ok"] is True

        resp = client.post(f"/api/nas/{nas_id}/upload", json={"bookId": "no-such"})
        assert resp.status_code == 404


def test_waifu2x_status_unavailable(tmp_path):
    """本机无 sr_vulkan，状态应如实返回不可用，convert 返回 503."""
    app = create_app(tmp_path)
    with TestClient(app) as client:
        status = client.get("/api/tools/waifu2x/status").json()
        assert status["available"] is False

        files = {"file": ("t.png", _png_bytes(), "image/png")}
        resp = client.post("/api/tools/waifu2x/convert", files=files)
        assert resp.status_code == 503


def test_dns_resolve(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        resp = client.post("/api/tools/dns/resolve", json={"host": "localhost"})
        data = resp.json()
        assert data["ok"] is True
        assert any(ip in ("127.0.0.1", "::1") for ip in data["ips"])

        resp = client.post(
            "/api/tools/dns/resolve", json={"host": "invalid..host--"}
        )
        assert resp.json()["ok"] is False


def test_proxy_test_disabled(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        resp = client.get("/api/tools/proxy/test")
        assert resp.json()["ok"] is False


def test_settings_local_dirs_persisted(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        settings = client.get("/api/settings").json()
        settings["local"]["dirs"] = ["/tmp/manga"]
        client.put("/api/settings", json=settings)
        assert client.get("/api/settings").json()["local"]["dirs"] == ["/tmp/manga"]
