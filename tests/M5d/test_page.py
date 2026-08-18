"""Workbench page serving and required views."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.M5d.conftest import REQUIRED_VIEW_IDS, WORKBENCH_CSS, WORKBENCH_INDEX, WORKBENCH_JS


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.m5d
class TestWorkbenchPage:
    def test_root_serves_html_workbench(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        body = response.text
        assert "<h1>学习工作台</h1>" in body
        assert "产品介绍" not in body
        assert "立即注册" not in body

    def test_required_learning_views_exist(self, client: TestClient):
        body = client.get("/").text
        for view_id in REQUIRED_VIEW_IDS:
            assert f'id="{view_id}"' in body

    def test_static_assets_are_served(self, client: TestClient):
        js = client.get("/static/workbench/app.js")
        css = client.get("/static/workbench/styles.css")
        assert js.status_code == 200
        assert css.status_code == 200
        assert "WORKBENCH_API" in js.text
        assert "due-panel" in css.text or ".panel" in css.text

    def test_workbench_files_exist_on_disk(self):
        assert WORKBENCH_INDEX.is_file()
        assert WORKBENCH_JS.is_file()
        assert WORKBENCH_CSS.is_file()