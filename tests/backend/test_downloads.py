"""下载队列测试：完整下载流程 + 任务状态机."""

import time
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from jmcomic_backend.main import create_app
from jmcomic_backend.services.download_manager import (
    STATUS_DONE,
    STATUS_ERROR,
    STATUS_PAUSED,
    STATUS_PENDING,
    DownloadManager,
)

SAMPLE_DETAIL = {
    "id": "123456",
    "title": "测试漫画",
    "eps": [
        {"index": 0, "epsId": "555", "name": "第1话", "sort": 0},
        {"index": 1, "epsId": "556", "name": "第2话", "sort": 1},
    ],
}

SAMPLE_PAGES = [
    {"index": 0, "name": "00001", "path": "media/photos/555/00001.jpg"},
    {"index": 1, "name": "00002", "path": "media/photos/555/00002.jpg"},
    {"index": 2, "name": "00003", "path": "media/photos/555/00003.jpg"},
]


def _patch_jm(monkeypatch=None):
    """同时 patch 路由与下载管理器内的 JmClient."""
    patches = []

    def _apply(target):
        cm = patch(target)
        mock_cls = cm.start()
        patches.append(cm)
        instance = mock_cls.return_value.__aenter__.return_value
        return instance

    route_client = _apply("jmcomic_backend.api.routes.downloads.JmClient")
    route_client.get_book_detail = AsyncMock(return_value=dict(SAMPLE_DETAIL))

    mgr_client = _apply("jmcomic_backend.services.download_manager.JmClient")
    mgr_client.get_chapter_pages = AsyncMock(
        return_value=[dict(p) for p in SAMPLE_PAGES]
    )
    # epsId 555 < scramble 220980：分割数为 0，图片原样保存
    mgr_client.get_scramble_id = AsyncMock(return_value=220980)
    mgr_client.fetch_image = AsyncMock(return_value=(b"img-bytes", "image/jpeg"))
    return patches


def test_start_download_and_complete(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        patches = _patch_jm()
        try:
            response = client.post(
                "/api/downloads/start", json={"bookId": "123456", "epsIndexes": [0]}
            )
            assert response.status_code == 200
            task_ids = response.json()["taskIds"]
            assert len(task_ids) == 1

            # 轮询等待 worker 完成
            task = {}
            for _ in range(100):
                tasks = client.get("/api/downloads").json()["tasks"]
                task = next(t for t in tasks if t["id"] == task_ids[0])
                if task["status"] == STATUS_DONE:
                    break
                time.sleep(0.05)
            assert task["status"] == STATUS_DONE
            assert task["totalPages"] == 3
            assert task["donePages"] == 3
            assert task["bookTitle"] == "测试漫画"
        finally:
            for cm in patches:
                cm.stop()

    # 文件落盘：download_dir/{book_id}/001/0001.jpg ...
    eps_dir = tmp_path / "downloads" / "123456" / "001"
    files = sorted(eps_dir.glob("*.jpg"))
    assert [f.name for f in files] == ["0001.jpg", "0002.jpg", "0003.jpg"]
    assert files[0].read_bytes() == b"img-bytes"


def test_start_download_all_eps(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        patches = _patch_jm()
        try:
            response = client.post("/api/downloads/start", json={"bookId": "123456"})
            assert len(response.json()["taskIds"]) == 2
        finally:
            for cm in patches:
                cm.stop()


def test_start_download_invalid_eps(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        patches = _patch_jm()
        try:
            response = client.post(
                "/api/downloads/start", json={"bookId": "123456", "epsIndexes": [99]}
            )
            assert response.status_code == 404
        finally:
            for cm in patches:
                cm.stop()


def test_manager_status_transitions(tmp_path):
    """不启动 worker，直接验证任务状态机."""
    manager = DownloadManager(tmp_path / "app.db", tmp_path / "downloads")
    task_id = manager.create_task("123456", "标题", 0, "555", "第1话")

    assert manager.list_tasks()[0]["status"] == STATUS_PENDING
    assert manager.pause(task_id) is True
    assert manager.list_tasks()[0]["status"] == STATUS_PAUSED
    assert manager.resume(task_id) is True
    assert manager.list_tasks()[0]["status"] == STATUS_PENDING

    # 只有 error 状态可 retry
    assert manager.retry(task_id) is False
    manager._set_status(task_id, STATUS_ERROR, error="boom")
    assert manager.retry(task_id) is True
    assert manager.list_tasks()[0]["error"] == ""

    assert manager.remove(task_id) is True
    assert manager.list_tasks() == []
    manager.close()


def test_manager_error_path(tmp_path):
    """下载中途失败应记录 error 状态，可 retry."""
    app = create_app(tmp_path)
    with TestClient(app) as client:
        patches = _patch_jm()
        try:
            client.post("/api/downloads/start", json={"bookId": "123456"})
            # 任务创建后再让图片拉取失败
            from jmcomic_backend.services.download_manager import JmClient

            JmClient.return_value.__aenter__.return_value.fetch_image = AsyncMock(
                side_effect=RuntimeError("network down")
            )
            task = {}
            for _ in range(100):
                tasks = client.get("/api/downloads").json()["tasks"]
                task = tasks[0]
                if task["status"] == STATUS_ERROR:
                    break
                time.sleep(0.05)
            assert task["status"] == STATUS_ERROR
            assert "network down" in task["error"]
        finally:
            for cm in patches:
                cm.stop()
