"""metrics 模块：净值指标、换手与胜率、NDCG、汇总字典可 JSON。"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.metrics import (
    aggregate_metrics,
    annualized_return,
    max_drawdown,
    ndcg_at_k,
    sharpe_ratio,
    turnover_rate,
    weekly_nav_to_daily_business_ffill,
    win_rate,
)


def test_annualized_return_positive_trend() -> None:
    idx = pd.date_range("2024-01-02", periods=252, freq="B")
    nav = pd.Series(np.linspace(100.0, 110.0, len(idx)), index=idx)
    ar = annualized_return(nav)
    assert ar > 0
    assert ar < 2.0


def test_weekly_nav_to_daily_ffill_length() -> None:
    idx = pd.to_datetime(["2024-01-05", "2024-01-12"])
    nav = pd.Series([100.0, 101.0], index=idx)
    d = weekly_nav_to_daily_business_ffill(nav)
    assert len(d) >= 5
    assert d.iloc[0] == 100.0
    assert d.iloc[-1] == 101.0


def test_nav_forward_fill() -> None:
    idx = pd.date_range("2024-01-02", periods=10, freq="B")
    nav = pd.Series([100.0, np.nan, np.nan, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0], index=idx)
    ar = annualized_return(nav)
    assert not np.isnan(ar)


def test_max_drawdown_peak_trough_order() -> None:
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    nav = pd.Series([100.0, 110.0, 80.0, 100.0], index=idx)
    dd = max_drawdown(nav)
    assert dd["max_drawdown"] == pytest.approx((110.0 - 80.0) / 110.0, rel=1e-9)
    assert dd["peak_date"] == "2024-01-03"
    assert dd["trough_date"] == "2024-01-04"


def test_sharpe_uses_log_returns_finite() -> None:
    idx = pd.date_range("2024-01-02", periods=252, freq="B")
    rng = np.random.default_rng(42)
    nav = pd.Series(100 * np.cumprod(1 + rng.normal(0.0003, 0.008, size=len(idx))), index=idx)
    s = sharpe_ratio(nav, risk_free_rate=0.03)
    assert np.isfinite(s)


def test_turnover_aggregate_matches_side_aggregate() -> None:
    agg = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"]),
            "buy_amount": [400_000.0, 0.0],
            "sell_amount": [100_000.0, 0.0],
            "total_value": [1_000_000.0, 1_000_000.0],
        }
    )
    side = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-05", "2024-01-12"]),
            "side": ["buy", "sell", "buy"],
            "gross_amount": [400_000.0, 100_000.0, 0.0],
            "total_value": [1_000_000.0, 1_000_000.0, 1_000_000.0],
        }
    )
    t1 = turnover_rate(agg)
    t2 = turnover_rate(side)
    assert t1 == pytest.approx(t2, rel=1e-9)
    assert t1 == pytest.approx(0.25, rel=1e-9)


def test_turnover_matches_manual_rebalance_notion() -> None:
    """单周：买+卖名义 / 当日总资产 = (3e5+3e5)/1e6 = 0.6。"""
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-02-01"]),
            "buy_amount": [300_000.0],
            "sell_amount": [300_000.0],
            "total_value": [1_000_000.0],
        }
    )
    assert turnover_rate(df) == pytest.approx(0.6, rel=1e-9)


def test_win_rate() -> None:
    df = pd.DataFrame({"pnl": [100.0, -50.0, 0.0, 20.0]})
    assert win_rate(df) == pytest.approx(0.5)


def test_win_rate_from_nav_series_matches_weekly_portfolio() -> None:
    """与回测 trades_df（调仓日 total_value）一致：周度收益为正的占比。"""
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12", "2024-01-19"]),
            "buy_amount": [0.0, 100_000.0, 0.0],
            "sell_amount": [0.0, 0.0, 50_000.0],
            "total_value": [1_000_000.0, 1_050_000.0, 1_030_000.0],
        }
    )
    # 收益: +5%, -1.9% -> 一正一负
    assert win_rate(df) == pytest.approx(1.0 / 2.0)


def test_ndcg_perfect_one() -> None:
    y_true = np.array([3.0, 2.0, 1.0, 0.0])
    y_score = np.array([4.0, 3.0, 2.0, 1.0])
    assert ndcg_at_k(y_true, y_score, k=4) == pytest.approx(1.0, rel=1e-9)


def test_aggregate_metrics_json_roundtrip() -> None:
    idx = pd.date_range("2024-01-02", periods=60, freq="B")
    nav = pd.Series(100 * (1.001 ** np.arange(len(idx))), index=idx)
    m = aggregate_metrics(
        nav,
        trades_df=pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-10"]),
                "buy_amount": [50_000.0],
                "sell_amount": [10_000.0],
                "total_value": [100_000.0],
            }
        ),
        y_true_ndcg=[2, 1, 0],
        y_score_ndcg=[0.3, 0.2, 0.1],
        ndcg_k=3,
    )
    s = json.dumps(m)
    back = json.loads(s)
    assert "annualized_return" in back
    assert back["drawdown_peak_date"] is None or isinstance(back["drawdown_peak_date"], str)
