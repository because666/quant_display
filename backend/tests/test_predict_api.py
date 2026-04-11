"""预测 API 格式与 ModelPredictor 单例行为。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.v1.deps import clear_predictor_cache, get_predictor
from src.main import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class _FakePredictorPost:
    model_type = "lightgbm"
    _data_dir = BACKEND_ROOT / "data"

    def get_top_stocks(self, df, top_n=20, with_contributions=False):
        return pd.DataFrame(
            [
                {"stock_code": "000001", "score": 0.85, "rank": 1},
                {"stock_code": "000002", "score": 0.72, "rank": 2},
            ]
        )

    def get_feature_importance(self):
        return {"mom_1m": 0.3, "rsi_21": 0.2}


def test_post_predict_json_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.api.v1 import predict as predict_mod

    monkeypatch.setattr(
        predict_mod,
        "load_prediction_data",
        lambda **kw: (
            pd.DataFrame({"stock_code": ["000001", "000002"], "mom_1m": [1.0, 2.0]}),
            "2024-12-31",
        ),
    )
    app.dependency_overrides[get_predictor] = lambda: _FakePredictorPost()

    r = client.post("/api/v1/predict", json={"top_n": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "data" in body
    d = body["data"]
    assert d["timestamp"] == "2024-12-31"
    assert isinstance(d["feature_importance"], dict)
    assert d["feature_importance"]["mom_1m"] == 0.3
    assert len(d["top_stocks"]) == 2
    assert d["top_stocks"][0] == {"code": "000001", "score": 0.85}


class _FakePredictorInfo:
    model_type = "lightgbm"

    def get_feature_importance(self):
        return {"f1": 10.0, "f2": 5.0}

    def get_model_trained_at(self):
        return "2024-12-31T12:00:00"


def test_get_model_info_json_shape(client: TestClient) -> None:
    app.dependency_overrides[get_predictor] = lambda: _FakePredictorInfo()
    r = client.get("/api/v1/model/info")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    d = body["data"]
    assert d["model_type"] == "lightgbm"
    assert d["trained_at"] == "2024-12-31T12:00:00"
    assert "feature_importance_list" in d
    assert isinstance(d["feature_importance_list"], list)
    assert d["feature_importance_list"][0]["feature"] == "f1"


@pytest.mark.skipif(
    not (BACKEND_ROOT / "models" / "lightgbm.pkl").exists(),
    reason="未找到 lightgbm.pkl，跳过单例集成测试",
)
def test_predictor_singleton_same_instance() -> None:
    clear_predictor_cache()
    a = get_predictor()
    b = get_predictor()
    assert a is b


@pytest.mark.skipif(
    not (BACKEND_ROOT / "models" / "lightgbm.pkl").exists()
    or not (BACKEND_ROOT / "data" / "test.parquet").exists(),
    reason="需要 models/lightgbm.pkl 与 data/test.parquet",
)
def test_get_advice_context_dict_keys() -> None:
    """get_advice_context 返回 AI 推荐所需字段。"""
    from src.predictor import ModelPredictor

    p = ModelPredictor("lightgbm")
    raw = pd.read_parquet(BACKEND_ROOT / "data" / "test.parquet")
    cols = ["stock_code"] + [c for c in p._factor_cols if c in raw.columns]
    df = raw[cols].head(200)
    ctx = p.get_advice_context(top_n=5, factor_df=df, section_date="2025-01-01")
    assert ctx["section_date"] == "2025-01-01"
    assert len(ctx["top_stocks"]) <= 5
    assert ctx["top_stocks"][0]["code"]
    assert "score" in ctx["top_stocks"][0]
    assert "feature_importance" in ctx
    assert ctx["model_type"] == "lightgbm"
