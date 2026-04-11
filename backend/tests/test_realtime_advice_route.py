"""realtime_advice 路由注册与 OpenAPI。"""
from __future__ import annotations

from src.main import app


def test_openapi_has_realtime_advice_post() -> None:
    schema = app.openapi()
    path = schema.get("paths", {}).get("/api/v1/realtime_advice", {})
    assert "post" in path
