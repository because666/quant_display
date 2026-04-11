"""LightGBM / XGBoost 对比：净值对齐、换手估算、月度热力图数据结构。"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.backtest import (
    align_comparison_nav_curves,
    build_rebalance_turnover_trades,
    metrics_table_with_difference,
    monthly_returns_heatmap_data,
    run_comparison,
    weekly_portfolio_win_rate,
)


def test_align_comparison_nav_same_length_and_excess() -> None:
    d1 = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"]),
            "total_value": [1_000_000.0, 1_100_000.0],
            "cash": [0.0, 0.0],
            "holdings": ["{}", "{}"],
        }
    )
    d2 = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"]),
            "total_value": [1_000_000.0, 1_050_000.0],
            "cash": [0.0, 0.0],
            "holdings": ["{}", "{}"],
        }
    )
    nav = align_comparison_nav_curves(d1, d2)
    assert len(nav["dates"]) == 2
    assert nav["lightgbm_nav_norm"][0] == 1.0
    assert nav["xgboost_nav_norm"][0] == 1.0
    assert abs(nav["excess_lightgbm_over_xgb_nav"][-1] - (1.1 / 1.05 - 1.0)) < 1e-6


def test_monthly_returns_heatmap_shape() -> None:
    dates = ["2024-01-05", "2024-02-02", "2024-02-09", "2024-03-01"]
    nav = [100.0, 101.0, 102.0, 105.0]
    h = monthly_returns_heatmap_data(dates, nav)
    assert 2024 in h["years"]
    assert len(h["values"]) == len(h["years"])
    assert len(h["values"][0]) == 12


def test_metrics_table_difference() -> None:
    rows = metrics_table_with_difference({"a": 0.5, "b": 1}, {"a": 0.3, "c": 2})
    da = next(r for r in rows if r["metric"] == "a")
    assert da["difference"] == pytest.approx(0.2)


def test_weekly_portfolio_win_rate() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12", "2024-01-19"]),
            "total_value": [100.0, 110.0, 105.0],
        }
    )
    wr = weekly_portfolio_win_rate(df)
    assert wr == pytest.approx(1.0 / 2.0)


def test_build_rebalance_turnover_positive() -> None:
    weekly = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"] * 2),
            "stock_code": ["AAA", "AAA", "BBB", "BBB"],
            "close": [10.0, 10.0, 20.0, 20.0],
        }
    )
    res = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"]),
            "total_value": [1_000_000.0, 1_000_000.0],
            "cash": [0.0, 0.0],
            "holdings": [
                json.dumps({"AAA": 100.0}, separators=(",", ":")),
                json.dumps({"BBB": 50.0}, separators=(",", ":")),
            ],
        }
    )
    tr = build_rebalance_turnover_trades(res, weekly)
    assert tr.iloc[0]["buy_amount"] >= 0
    assert tr.iloc[1]["buy_amount"] + tr.iloc[1]["sell_amount"] > 0


def test_run_comparison_writes_files(monkeypatch, tmp_path: Path) -> None:
    import src.backtest as bt

    monkeypatch.setattr(bt, "_dual_backtest_core", _fake_dual_core)
    monkeypatch.setattr(bt, "write_backtest_comparison_html", lambda *a, **k: False)

    out = run_comparison(out_dir=tmp_path, write_html=False)
    assert (tmp_path / "comparison.json").exists()
    assert (tmp_path / "comparison_nav.json").exists()
    raw = json.loads((tmp_path / "comparison.json").read_text(encoding="utf-8"))
    assert raw["kind"] == "strategy_comparison"
    assert "monthly_returns_heatmap" in raw
    assert "metrics_table" in raw
    assert out["out_dir"]


def _fake_dual_core(**_kwargs: object):
    dates = pd.to_datetime(["2024-01-05", "2024-01-12"])
    df = pd.DataFrame(
        {
            "date": dates,
            "total_value": [1_000_000.0, 1_020_000.0],
            "cash": [0.0, 0.0],
            "holdings": ["{}", "{}"],
        }
    )
    weekly = pd.DataFrame(
        {
            "date": dates,
            "stock_code": ["X", "X"],
            "close": [1.0, 1.0],
        }
    )
    params = {"model_type": "lightgbm", "top_n": 1}
    packs = {
        "lightgbm": {"result_df": df.copy(), "params": params},
        "xgboost": {"result_df": df.copy(), "params": params},
    }
    return weekly, packs
