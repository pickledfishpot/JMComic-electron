"""认证与收藏 API 测试."""

from unittest.mock import AsyncMock, patch

SAMPLE_USER = {
    "uid": "12345",
    "username": "tester",
    "title": "Lv2",
    "level": "2",
    "coin": "0",
    "gender": "Male",
    "favorites": "3",
    "favorites_max": "200",
    "exp": 10,
    "next_exp": 100,
}

SAMPLE_FAVORITES = {
    "total": 1,
    "count": 1,
    "books": [
        {
            "id": "123456",
            "title": "收藏的本子",
            "author": ["作者A"],
            "authorList": ["作者A"],
            "tags": [],
            "categories": [],
            "coverUrl": "/api/images/media/albums/123456_3x4.jpg",
            "likes": "1",
            "views": "2",
        }
    ],
    "folders": [{"id": "7", "name": "默认"}],
}


def _login(client):
    with patch("jmcomic_backend.api.routes.auth.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.login = AsyncMock(return_value=(dict(SAMPLE_USER), {"AVS": "abc"}))
        response = client.post(
            "/api/auth/login", json={"username": "tester", "password": "pw"}
        )
    assert response.status_code == 200
    return response.json()["user"]


def test_login_success(client):
    user = _login(client)
    assert user["uid"] == "12345"
    assert user["username"] == "tester"
    assert "cookies" not in user

    # 登录态可恢复
    response = client.get("/api/auth/me")
    assert response.json()["user"]["uid"] == "12345"


def test_login_failure(client):
    from jmcomic_backend.services.jm_client import JmApiError

    with patch("jmcomic_backend.api.routes.auth.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.login = AsyncMock(side_effect=JmApiError("密码错误"))
        response = client.post(
            "/api/auth/login", json={"username": "tester", "password": "bad"}
        )
    assert response.status_code == 401


def test_logout(client):
    _login(client)
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert client.get("/api/auth/me").json()["user"] is None


def test_favorites_requires_login(client):
    response = client.get("/api/favorites")
    assert response.status_code == 401


def test_get_favorites(client):
    _login(client)
    with patch("jmcomic_backend.api.routes.favorites.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.get_favorites = AsyncMock(return_value=dict(SAMPLE_FAVORITES))
        response = client.get("/api/favorites?page=1&sort=mr&folderId=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["books"][0]["title"] == "收藏的本子"
    assert data["folders"][0]["name"] == "默认"


def test_toggle_favorite(client):
    _login(client)
    with patch("jmcomic_backend.api.routes.favorites.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.toggle_favorite = AsyncMock(return_value={"ok": True, "message": "收藏成功"})
        response = client.post("/api/favorites", json={"bookId": "123456"})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_history_list_with_title(client):
    client.put(
        "/api/books/123456/progress",
        json={"epsIndex": 1, "pageIndex": 5, "title": "测试漫画"},
    )
    client.put(
        "/api/books/789/progress",
        json={"epsIndex": 0, "pageIndex": 2, "title": "另一本"},
    )
    response = client.get("/api/history?page=1&pageSize=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    # 最近更新的排最前
    assert data["items"][0]["title"] == "另一本"
    assert data["items"][0]["epsIndex"] == 0
    assert data["items"][1]["bookId"] == "123456"

    response = client.delete("/api/history/123456")
    assert response.json()["ok"] is True
    assert client.get("/api/history").json()["total"] == 1
