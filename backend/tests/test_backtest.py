"""BacktestEngine 涨跌停过滤与交易成本公式单测。"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.backtest import BacktestEngine

_BACKEND = Path(__file__).resolve().parents[1]


class _FakePredictor:
    model_type = "lightgbm"
    _factor_cols = ["f1"]
    _data_dir = _BACKEND / "data"

    def predict_panel(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        if factor_df.empty:
            return pd.DataFrame(columns=["date", "stock_code", "score"])
        rank = {"AAA": 3.0, "BBB": 2.0, "CCC": 1.0}
        out = factor_df[["date", "stock_code"]].copy()
        out["date"] = pd.to_datetime(out["date"])
        out["stock_code"] = out["stock_code"].astype(str)
        out["score"] = out["stock_code"].map(rank).astype(float)
        return out

    def predict(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        rank = {"AAA": 3.0, "BBB": 2.0, "CCC": 1.0}
        out = pd.DataFrame(
            {
                "stock_code": factor_df["stock_code"].astype(str),
                "score": factor_df["stock_code"].map(rank).astype(float),
                "f1": factor_df["f1"],
            }
        )
        return out.sort_values("score", ascending=False, kind="mergesort").reset_index(drop=True)


def test_limit_up_stock_not_in_target_holdings() -> None:
    """涨停标的不可买入，Top N 顺延至下一名。"""
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05"] * 3),
            "stock_code": ["AAA", "BBB", "CCC"],
            "f1": [0.0, 0.0, 0.0],
            "close": [10.0, 10.0, 10.0],
            "buy_blocked_limit_up": [True, False, False],
            "sell_blocked_limit_down": [False, False, False],
            "future_return_1w": [0.01, 0.01, 0.01],
        }
    )
    eng = BacktestEngine("lightgbm", top_n=2, initial_capital=100_000.0)
    out = eng.run_backtest(df, predictor=_FakePredictor(), use_split="all")
    assert len(out) == 1
    h = json.loads(str(out.iloc[0]["holdings"]))
    assert "AAA" not in h
    assert "BBB" in h and "CCC" in h


def test_sell_cash_includes_commission_slippage_stamp() -> None:
    """卖出侧：滑点压低成交价，再扣双边佣金与卖出印花税。"""
    eng = BacktestEngine(
        "lightgbm",
        top_n=1,
        initial_capital=1.0,
        commission=0.0003,
        slippage=0.001,
        stamp_tax=0.0005,
    )
    # 100 股，收盘价 10：单价 9.99，成交额 999，再 * (1 - 0.0003 - 0.0005)
    c = eng._cash_from_sell(100.0, 10.0)
    assert abs(c - 999.0 * (1.0 - 0.0003 - 0.0005)) < 1e-6


def test_buy_reduces_nav_below_initial_due_to_fees() -> None:
    """首周满仓买入后总市值略低于初始现金（佣金+滑点）。"""
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05"]),
            "stock_code": ["ZZZ"],
            "f1": [0.0],
            "close": [100.0],
            "buy_blocked_limit_up": [False],
            "sell_blocked_limit_down": [False],
            "future_return_1w": [0.0],
        }
    )

    class _P:
        model_type = "lightgbm"
        _factor_cols = ["f1"]
        _data_dir = _BACKEND / "data"

        def predict_panel(self, factor_df: pd.DataFrame) -> pd.DataFrame:
            out = factor_df[["date", "stock_code"]].copy()
            out["date"] = pd.to_datetime(out["date"])
            out["score"] = 1.0
            return out

        def predict(self, factor_df: pd.DataFrame) -> pd.DataFrame:
            return pd.DataFrame({"stock_code": ["ZZZ"], "score": [1.0], "f1": [0.0]})

    eng = BacktestEngine("lightgbm", top_n=1, initial_capital=1_000_000.0)
    out = eng.run_backtest(df, predictor=_P(), use_split="all")
    tv = float(out.iloc[0]["total_value"])
    assert tv < 1_000_000.0
    # 约 1e6 / (1.001*1.0003) 股 * 100 ≈ 998701
    assert tv > 998_500.0


def test_predict_failure_skips_week_without_crash() -> None:
    """某周 predict 失败时跳过调仓，回测继续。"""

    class _BadPredictor:
        model_type = "lightgbm"
        _factor_cols = ["f1"]
        _data_dir = _BACKEND / "data"

        def predict_panel(self, factor_df: pd.DataFrame) -> pd.DataFrame:
            raise RuntimeError("batch down")

        def predict(self, factor_df: pd.DataFrame) -> pd.DataFrame:
            raise ValueError("no factors")

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"]),
            "stock_code": ["ZZZ", "ZZZ"],
            "f1": [0.0, 0.0],
            "close": [10.0, 10.0],
            "buy_blocked_limit_up": [False, False],
            "sell_blocked_limit_down": [False, False],
            "future_return_1w": [0.0, 0.0],
        }
    )
    eng = BacktestEngine("lightgbm", top_n=1, initial_capital=100_000.0)
    out = eng.run_backtest(df, predictor=_BadPredictor(), use_split="all")
    assert len(out) == 2
    assert all(float(out.iloc[i]["total_value"]) == pytest.approx(100_000.0) for i in range(2))
