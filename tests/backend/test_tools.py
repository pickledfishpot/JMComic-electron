"""工具与设置 API 测试.

这几个用例原本在 test_tools_nas.py 里，删除 NAS 功能时被连带删掉，
与 NAS 无关，捞回独立文件（724ca3a 的遗留问题）.
"""

import base64

from fastapi.testclient import TestClient

from jmcomic_backend.main import create_app


def _png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


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

        resp = client.post("/api/tools/dns/resolve", json={"host": "invalid..host--"})
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
