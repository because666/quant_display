"""回测 JSON 导出与 SQLite 落库。"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from src.backtest import (
    build_comparison_json,
    persist_backtest_result,
    save_results_to_json,
)
from src.config import get_settings
from src.db.session import get_engine, reset_engine


def test_save_results_to_json_writes_expected_files(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-12"]),
            "total_value": [1_000_000.0, 1_010_000.0],
            "cash": [0.0, 0.0],
            "holdings": ["{}", '{"600000":10.0}'],
        }
    )
    pack = {"result_df": df, "metrics": {"annualized_return": 0.05, "sharpe_ratio": 1.2}, "params": {}}
    bench = {
        "index_code": "000300.SH",
        "name": "沪深300",
        "granularity": "daily",
        "dates": ["2024-01-05", "2024-01-08"],
        "nav_values": [1.0, 1.01],
        "source": "test",
        "range": {"start": "2024-01-05", "end": "2024-01-12"},
        "note": "",
    }
    save_results_to_json(
        out_dir=tmp_path,
        lightgbm_pack=pack,
        xgboost_pack=pack,
        benchmark=bench,
    )
    for name in (
        "lightgbm_nav.json",
        "lightgbm_metrics.json",
        "lightgbm_holdings.json",
        "lightgbm_benchmark.json",
        "xgboost_nav.json",
        "comparison.json",
    ):
        assert (tmp_path / name).exists(), name
    nav = json.loads((tmp_path / "lightgbm_nav.json").read_text(encoding="utf-8"))
    assert nav["granularity"] == "weekly"
    assert nav["dates"][0] == "2024-01-05"
    assert len(nav["nav_values"]) == 2
    h = json.loads((tmp_path / "lightgbm_holdings.json").read_text(encoding="utf-8"))
    assert h["series"][1]["holdings"]["600000"] == 10.0


def test_build_comparison_json() -> None:
    c = build_comparison_json({"a": 1, "b": 2}, {"a": 3, "c": 4})
    keys = {r["metric"] for r in c["metrics_table"]}
    assert keys == {"a", "b", "c"}
    row_a = next(r for r in c["metrics_table"] if r["metric"] == "a")
    assert row_a["lightgbm"] == 1
    assert row_a["xgboost"] == 3
    assert row_a["difference"] == pytest.approx(-2.0)


def test_persist_backtest_result_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "test_bt.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    reset_engine()

    df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-05")],
            "total_value": [1_000_000.0],
        }
    )
    persist_backtest_result(
        model_type="lightgbm",
        params={"top_n": 5},
        result_df=df,
        metrics={"annualized_return": 0.1},
    )
    eng = get_engine()
    with eng.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM backtest_result")).scalar()
    assert int(n) == 1

    reset_engine()
    get_settings.cache_clear()
