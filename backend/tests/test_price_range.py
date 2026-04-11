"""price_range：ATR、支撑阻力、买卖区间。"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import price_range as pr


def _synthetic_daily(n: int = 40, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-02", periods=n, freq="B")
    close = 10.0 + np.cumsum(rng.normal(0, 0.05, size=n))
    high = close + rng.uniform(0.02, 0.15, size=n)
    low = close - rng.uniform(0.02, 0.15, size=n)
    return pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1e6,
            "amount": 1e7,
            "turnover": 1.0,
            "pct_chg": 0.0,
            "is_suspended": False,
            "is_limit_up": False,
            "is_limit_down": False,
            "stock_code": "000001",
        }
    )


def test_atr_and_sr_and_range_order(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _synthetic_daily(40)
    monkeypatch.setattr(pr, "load_cached_data", lambda _code: df.copy())
    monkeypatch.setattr(pr, "RAW_DATA_DIR", Path("/nonexistent_dir_price_range_test"))
    pr.clear_atr_cache()

    atr = pr.calculate_atr("000001", period=14)
    assert atr > 0
    assert np.isfinite(atr)

    sr = pr.calculate_support_resistance("000001", lookback_days=20)
    assert sr["support"] <= sr["resistance"]

    px = float(df["close"].iloc[-1])
    out = pr.get_price_range("000001", px)
    assert out["buy_low"] <= out["buy_high"] < px
    assert out["sell_low"] <= out["sell_high"]
    assert out["buy_low"] >= out["support"] - 1e-9
    assert out["sell_high"] <= out["resistance"] + 1e-9
    # 阻力高于现价时，卖出区间主体在现价上方
    if out["resistance"] >= px + 1e-6:
        assert out["sell_low"] > px


def test_small_atr_intervals(monkeypatch: pytest.MonkeyPatch) -> None:
    n = 30
    dates = pd.date_range("2024-01-02", periods=n, freq="B")
    close = np.full(n, 10.0)
    high = close + 0.001
    low = close - 0.001
    df = pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1e6,
            "amount": 1e7,
            "turnover": 1.0,
            "pct_chg": 0.0,
            "is_suspended": False,
            "is_limit_up": False,
            "is_limit_down": False,
            "stock_code": "000001",
        }
    )
    monkeypatch.setattr(pr, "load_cached_data", lambda _code: df.copy())
    monkeypatch.setattr(pr, "RAW_DATA_DIR", Path("/nonexistent_dir_price_range_test2"))
    pr.clear_atr_cache()

    out = pr.get_price_range("000001", 10.0)
    assert out["atr"] < 0.05
    w = out["buy_high"] - out["buy_low"]
    assert w < 0.05


def test_get_price_range_perf_cached(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    df = _synthetic_daily(50)
    monkeypatch.setattr(pr, "load_cached_data", lambda _code: df)
    p = tmp_path / "000001.parquet"
    df.to_parquet(p, index=False)
    monkeypatch.setattr(pr, "RAW_DATA_DIR", tmp_path)
    pr.clear_atr_cache()

    px = float(df["close"].iloc[-1])
    pr.get_price_range("000001", px)  # prime cache + parquet stat

    n = 80
    t0 = time.perf_counter()
    for _ in range(n):
        pr.get_price_range("000001", px)
    elapsed = time.perf_counter() - t0
    assert elapsed / n < 0.010, f"mean {elapsed/n*1e3:.3f}ms per call (expected <10ms)"


def test_insufficient_data(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _synthetic_daily(10)
    monkeypatch.setattr(pr, "load_cached_data", lambda _code: df.copy())
    monkeypatch.setattr(pr, "RAW_DATA_DIR", Path("/nonexistent"))
    pr.clear_atr_cache()
    with pytest.raises(ValueError, match="K 线不足"):
        pr.calculate_atr("000001", period=14)
