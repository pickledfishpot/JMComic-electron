"""pytest 公共 fixture."""

import pytest
from fastapi.testclient import TestClient

from jmcomic_backend.main import create_app


@pytest.fixture
def client(tmp_path):
    """带 lifespan 的 TestClient（初始化 history / image_cache 等 app.state）."""
    with TestClient(create_app(tmp_path)) as test_client:
        yield test_client
