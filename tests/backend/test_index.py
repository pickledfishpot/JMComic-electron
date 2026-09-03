"""首页推荐、书籍详情、搜索、分类、评论 API 测试."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from jmcomic_backend.main import create_app


SAMPLE_INDEX = {
    "page": "0",
    "sections": {
        "本周排行": [
            {
                "id": "123456",
                "title": "测试漫画",
                "author": ["作者A"],
                "authorList": ["作者A"],
                "tags": ["标签1"],
                "categories": ["分类A"],
                "coverUrl": "/api/images/media/albums/123456_3x4.jpg",
                "likes": "100",
                "views": "2000",
            }
        ]
    },
}

SAMPLE_BOOK = {
    "id": "123456",
    "title": "测试漫画",
    "description": "描述",
    "authorList": ["作者A"],
    "tags": ["标签1"],
    "categories": ["分类A"],
    "coverUrl": "/api/images/media/albums/123456_3x4.jpg",
    "likes": "100",
    "views": "2000",
    "commentTotal": 5,
    "isFavorite": False,
    "eps": [{"index": 0, "epsId": "123456", "name": "", "sort": 0}],
}

SAMPLE_SEARCH = {
    "total": 1,
    "books": [
        {
            "id": "123456",
            "title": "测试漫画",
            "author": ["作者A"],
            "authorList": ["作者A"],
            "tags": ["标签1"],
            "categories": ["分类A"],
            "coverUrl": "/api/images/media/albums/123456_3x4.jpg",
            "likes": "100",
            "views": "2000",
        }
    ],
}

SAMPLE_CATEGORIES = {
    "categories": [
        {"id": "1", "name": "同人", "slug": "doujin", "type": "doujin", "total": 100}
    ],
    "blocks": {"热门标签": ["标签1"]},
}

SAMPLE_COMMENTS = {
    "total": 1,
    "comments": [
        {
            "id": "1",
            "uid": "1",
            "name": "用户A",
            "title": "Lv1",
            "level": "1",
            "content": "测试评论",
            "headUrl": "",
            "like": "0",
            "date": "2026-09-03",
            "linkBookName": "",
            "linkBookId": "",
            "subComments": [],
        }
    ],
}


def test_get_index(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    with patch("jmcomic_backend.api.routes.index.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.get_index = AsyncMock(return_value=SAMPLE_INDEX["sections"])
        response = client.get("/api/index")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == "0"
    assert "本周排行" in data["sections"]


def test_get_book_detail(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    with patch("jmcomic_backend.api.routes.books.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.get_book_detail = AsyncMock(return_value=SAMPLE_BOOK)
        response = client.get("/api/books/123456")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "123456"
    assert data["title"] == "测试漫画"


def test_proxy_image(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    with patch("jmcomic_backend.api.routes.images.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.fetch_image = AsyncMock(return_value=(b"fake-image-data", "image/jpeg"))
        response = client.get("/api/images/media/albums/123456_3x4.jpg")
    assert response.status_code == 200
    assert response.content == b"fake-image-data"
    assert response.headers["content-type"] == "image/jpeg"


def test_search_books(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    with patch("jmcomic_backend.api.routes.search.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.search = AsyncMock(return_value=SAMPLE_SEARCH)
        response = client.get("/api/search?q=测试&page=1&sort=mr")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "测试"
    assert data["total"] == 1
    assert data["books"][0]["id"] == "123456"


def test_get_categories(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    with patch("jmcomic_backend.api.routes.categories.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.get_categories = AsyncMock(return_value=SAMPLE_CATEGORIES)
        response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) == 1
    assert data["categories"][0]["slug"] == "doujin"


def test_get_category_books(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    with patch("jmcomic_backend.api.routes.categories.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.get_category_books = AsyncMock(return_value=SAMPLE_SEARCH)
        response = client.get("/api/categories/doujin/books?page=1&sort=mr")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "doujin"
    assert data["total"] == 1


def test_get_book_comments(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    with patch("jmcomic_backend.api.routes.comments.JmClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.get_book_comments = AsyncMock(return_value=SAMPLE_COMMENTS)
        response = client.get("/api/books/123456/comments?page=1")
    assert response.status_code == 200
    data = response.json()
    assert data["bookId"] == "123456"
    assert data["total"] == 1
    assert data["comments"][0]["content"] == "测试评论"
