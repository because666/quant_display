"""
影子账户 + 实时建议 API 全流程集成测试。

- 使用临时 SQLite 文件库，并同步替换各模块中的 ``SessionLocal`` 引用。
- DeepSeek 使用 monkeypatch 模拟流式响应，不发起外网请求。
- 覆盖成功路径、鉴权失败、预测结果为空等场景。
"""
from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from src.api.v1.deps import get_predictor
from src.config import get_settings
from src.database.database import Base
from src.data_fetcher import _normalize_stock_code
from src.database.models import AIAdvice
import src.account as account_mod
import src.api.v1.realtime_advice as realtime_mod
import src.database.database as db_mod
from src import account as account_svc
from src import deepseek_stream as deepseek_mod
from src.main import app


@pytest.fixture
def sqlite_integration_db(tmp_path, monkeypatch):
    """独立 SQLite 文件库 + 外键 + 全表重建。"""
    db_path = tmp_path / "integration_ai.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    db_mod.engine.dispose()
    eng = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _fk(dbapi_connection, _connection_record) -> None:
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    factory = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    db_mod.engine = eng
    db_mod.SessionLocal = factory
    account_mod.SessionLocal = factory
    realtime_mod.SessionLocal = factory

    import src.database.models as _models  # noqa: F401, ensure mappers

    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)

    yield {"url": url, "engine": eng, "SessionLocal": factory}

    app.dependency_overrides.clear()
    eng.dispose()
    get_settings.cache_clear()


@pytest.fixture
def fake_predictor():
    class _P:
        model_type = "lightgbm"
        _data_dir = Path(__file__).resolve().parent

        def get_top_stocks(self, factor_df: pd.DataFrame, top_n: int = 10, with_contributions: bool = False):
            return pd.DataFrame(
                [
                    {"stock_code": "000001.SZ", "score": 0.95, "rank": 1},
                    {"stock_code": "600000.SH", "score": 0.90, "rank": 2},
                ]
            )

        def get_feature_importance(self) -> dict[str, float]:
            return {"factor_a": 100.0, "factor_b": 80.0, "factor_c": 60.0, "factor_d": 40.0, "factor_e": 20.0}

    def _dep() -> Any:
        return _P()

    app.dependency_overrides[get_predictor] = _dep
    return _P


@pytest.fixture
def capture_stream(monkeypatch) -> list[list[dict[str, str]]]:
    """捕获传入 ``stream_advice`` 的 messages。"""
    captured: list[list[dict[str, str]]] = []

    async def _fake_stream(messages: list[dict[str, Any]], **kwargs: Any):
        captured.append(copy.deepcopy(messages))
        yield 'data: {"content": "## 操作建议\\n"}\n\n'
        yield 'data: {"content": "### 买入建议\\n模拟正文\\n"}\n\n'

    monkeypatch.setattr(realtime_mod.ds, "stream_advice", _fake_stream)
    return captured


@pytest.fixture
def stub_factor_and_prices(monkeypatch):
    def _fake_load(*, data_dir=None, latest_date=None):
        return (
            pd.DataFrame({"stock_code": ["000001.SZ", "600000.SH"], "dummy_f": [1.0, 2.0]}),
            "2024-06-01",
        )

    monkeypatch.setattr(realtime_mod, "load_prediction_data", _fake_load)

    monkeypatch.setattr(
        realtime_mod,
        "_batch_last_closes",
        lambda codes: {_normalize_stock_code(c): 10.5 for c in codes},
    )

    def _fixed_ranges(codes: list[str], close_map: dict[str, float]) -> dict[str, dict[str, Any]]:
        return {
            c: {
                "buy_low": 9.0,
                "buy_high": 9.8,
                "sell_low": 11.0,
                "sell_high": 11.5,
                "atr": 0.5,
                "support": 8.5,
                "resistance": 12.0,
            }
            for c in codes
        }

    monkeypatch.setattr(realtime_mod, "_build_price_ranges_dict", _fixed_ranges)


def _parse_sse_data_lines(body: str) -> tuple[list[dict[str, Any]], list[str]]:
    """返回 (json payloads, raw lines)；忽略空行。"""
    payloads: list[dict[str, Any]] = []
    raw: list[str] = []
    for block in body.split("\n\n"):
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw.append(line)
            payload = line[5:].strip()
            if payload == "[DONE]":
                payloads.append({"done": True})
                continue
            try:
                payloads.append(json.loads(payload))
            except json.JSONDecodeError:
                payloads.append({"raw": payload})
    return payloads, raw


def test_full_flow_create_holdings_sse_and_persist(
    sqlite_integration_db,
    fake_predictor,
    capture_stream,
    stub_factor_and_prices,
) -> None:
    cr = account_svc.create_account(
        "test_account",
        holdings=[{"code": "000001.SZ", "name": "平安银行", "quantity": 100, "cost": 9.2}],
    )
    assert cr.ok and cr.value
    aid = cr.value["id"]

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/realtime_advice",
            json={"account_name": "test_account", "refresh": False},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            body = resp.read().decode("utf-8")

    payloads, lines = _parse_sse_data_lines(body)
    assert any("content" in p for p in payloads if isinstance(p, dict))
    assert any(p.get("done") for p in payloads)
    for ln in lines:
        assert ln.startswith("data: ")
        rest = ln[5:].strip()
        assert rest == "[DONE]" or rest.startswith("{")

    assert len(capture_stream) == 1
    user_text = capture_stream[0][1]["content"]
    assert "000001.SZ" in user_text or "000001" in user_text
    assert "买入参考" in user_text
    assert "9" in user_text

    factory = sqlite_integration_db["SessionLocal"]
    with factory() as session:
        n = session.scalar(select(func.count()).select_from(AIAdvice).where(AIAdvice.account_id == aid))
        assert int(n or 0) == 1
        row = session.scalars(select(AIAdvice).where(AIAdvice.account_id == aid)).first()
        assert row is not None
        assert "## 操作建议" in row.advice_markdown
        assert len(row.top_stocks) >= 1


def test_second_call_and_update_ranges(
    sqlite_integration_db,
    fake_predictor,
    capture_stream,
    stub_factor_and_prices,
) -> None:
    account_svc.create_account("test_account2", holdings=[])
    gr = account_svc.get_account_by_name("test_account2")
    assert gr.ok and gr.value
    aid = int(gr.value["id"])

    ur = account_svc.update_ranges(aid, date(2023, 1, 1), date(2023, 12, 31), date(2024, 1, 1), date(2024, 6, 30))
    assert ur.ok
    assert ur.value["backtest_start"] == "2023-01-01"

    with TestClient(app) as client:
        for _ in range(2):
            with client.stream(
                "POST",
                "/api/v1/realtime_advice",
                json={"account_name": "test_account2", "refresh": False},
            ) as resp:
                assert resp.status_code == 200
                resp.read()

    factory = sqlite_integration_db["SessionLocal"]
    with factory() as session:
        assert int(session.scalar(select(func.count()).select_from(AIAdvice).where(AIAdvice.account_id == aid)) or 0) == 2

    g2 = account_svc.get_account(aid)
    assert g2.ok
    assert g2.value["backtest_start"] == "2023-01-01"


def test_async_client_sse_chunks(
    sqlite_integration_db,
    fake_predictor,
    capture_stream,
    stub_factor_and_prices,
) -> None:
    import asyncio

    account_svc.create_account("async_acc", holdings=[])

    async def _run() -> str:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/api/v1/realtime_advice",
                json={"account_name": "async_acc", "refresh": False},
                timeout=60.0,
            ) as resp:
                assert resp.status_code == 200
                buf = b""
                async for chunk in resp.aiter_bytes():
                    buf += chunk
        return buf.decode("utf-8")

    text = asyncio.run(_run())
    assert "data:" in text
    payloads, _ = _parse_sse_data_lines(text)
    assert any("content" in x for x in payloads if isinstance(x, dict))


def test_deepseek_auth_error_event_in_stream(
    sqlite_integration_db,
    fake_predictor,
    stub_factor_and_prices,
    monkeypatch,
) -> None:
    account_svc.create_account("auth_fail_acc", holdings=[])

    async def _boom(_messages, **_kw):
        raise deepseek_mod.DeepSeekAuthError("invalid key for test")
        yield ""  # noqa: B901 — 使函数成为 async generator，首帧即抛错

    monkeypatch.setattr(realtime_mod.ds, "stream_advice", _boom)

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/realtime_advice",
            json={"account_name": "auth_fail_acc", "refresh": False},
        ) as resp:
            assert resp.status_code == 200
            body = resp.read().decode("utf-8")

    payloads, _ = _parse_sse_data_lines(body)
    assert any(p.get("error") is True for p in payloads if isinstance(p, dict))

    factory = sqlite_integration_db["SessionLocal"]
    with factory() as session:
        assert int(session.scalar(select(func.count()).select_from(AIAdvice)) or 0) == 0


def test_empty_top_stocks_persists_error_row(
    sqlite_integration_db,
    stub_factor_and_prices,
    capture_stream,
    monkeypatch,
) -> None:
    class _EmptyPred:
        model_type = "lightgbm"
        _data_dir = Path(".")

        def get_top_stocks(self, *a, **k):
            return pd.DataFrame(columns=["stock_code", "score", "rank"])

        def get_feature_importance(self):
            return {"f": 1.0}

    app.dependency_overrides[get_predictor] = lambda: _EmptyPred()

    account_svc.create_account("empty_top_acc", holdings=[])

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/realtime_advice",
            json={"account_name": "empty_top_acc", "refresh": False},
        ) as resp:
            body = resp.read().decode("utf-8")

    payloads, _ = _parse_sse_data_lines(body)
    assert any(p.get("code") == "predict" for p in payloads if isinstance(p, dict))

    factory = sqlite_integration_db["SessionLocal"]
    with factory() as session:
        row = session.scalars(select(AIAdvice)).first()
        assert row is not None
        assert "[错误]" in row.advice_markdown

    app.dependency_overrides.clear()
