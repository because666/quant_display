"""FastAPI 依赖：单例 ModelPredictor，避免每次请求重复加载模型。"""
from __future__ import annotations

from functools import lru_cache

from src.config import get_settings
from src.predictor import ModelKind, ModelPredictor


@lru_cache(maxsize=1)
def _predictor_singleton(model_key: str) -> ModelPredictor:
    mt: ModelKind = "lightgbm" if model_key == "lightgbm" else "xgboost"
    return ModelPredictor(mt)


def get_predictor() -> ModelPredictor:
    s = get_settings()
    key = (s.default_predict_model or "lightgbm").strip().lower()
    if key not in ("lightgbm", "xgboost"):
        key = "lightgbm"
    return _predictor_singleton(key)


def clear_predictor_cache() -> None:
    """单测或热切换模型时清空缓存。"""
    _predictor_singleton.cache_clear()
