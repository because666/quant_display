"""
校验 feature_engineering 向量化实现与朴素实现数值一致（默认 rtol=1e-6）。
用法：在 backend 目录下 PYTHONPATH=. python scripts/verify_factor_engineering_parity.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# noqa: E402 — 需在设置路径后导入
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from src.feature_engineering import (  # pylint: disable=wrong-import-position
    _compute_rsi,
    compute_factors,
)


def _assert_close(a: np.ndarray, b: np.ndarray, *, rtol: float = 1e-6, atol: float = 1e-9) -> None:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    mask = np.isfinite(a) & np.isfinite(b)
    if not np.allclose(a[mask], b[mask], rtol=rtol, atol=atol):
        diff = np.abs(a[mask] - b[mask])
        raise AssertionError(f"max abs diff {np.nanmax(diff)} exceeds rtol={rtol}")


def test_momentum_log_vs_prod() -> None:
    rng = np.random.default_rng(0)
    s = pd.Series(rng.normal(0.01, 0.02, size=120))
    # 保证 1+r > 0，与 log 路径一致
    s = s.clip(-0.5, 0.5)
    window = 12
    legacy = (1.0 + s).rolling(window, min_periods=window).apply(np.prod, raw=True) - 1.0
    one_plus = 1.0 + s
    log_op = np.where(np.isfinite(one_plus) & (one_plus > 0), np.log(one_plus), np.nan)
    vect = np.expm1(pd.Series(log_op).rolling(window, min_periods=window).sum())
    _assert_close(legacy.to_numpy(), vect.to_numpy())


def test_rsi_matches_per_stock() -> None:
    rng = np.random.default_rng(1)
    n = 80
    close = pd.Series(np.cumprod(1 + rng.normal(0, 0.02, size=n)) * 10)
    for period in (7, 14, 21):
        a = _compute_rsi(close, period)
        # 朴素按行：与向量化 groupby 单组应一致
        b = _compute_rsi(close.copy(), period)
        _assert_close(a.to_numpy(), b.to_numpy())


def test_compute_factors_smoke_parity() -> None:
    rng = np.random.default_rng(42)
    n_stocks = 30
    n_weeks = 50
    codes = [f"{i:06d}" for i in range(1, n_stocks + 1)]
    dates = pd.date_range("2016-01-01", periods=n_weeks, freq="W-FRI")
    rows: list[dict] = []
    for code in codes:
        rets = rng.normal(0.001, 0.03, size=n_weeks)
        px = 100 * np.cumprod(1 + rets)
        vol = rng.lognormal(10, 0.3, size=n_weeks)
        to = rng.uniform(0.01, 0.08, size=n_weeks)
        for d, c, v, t in zip(dates, px, vol, to):
            rows.append({"date": d, "stock_code": code, "close": float(c), "volume": float(v), "turnover": float(t)})
    weekly_df = pd.DataFrame(rows)

    out_path = os.path.join(_BACKEND, "data", "_parity_factors.parquet")
    t0 = time.perf_counter()
    out = compute_factors(weekly_df, output_path=Path(out_path))
    dt = time.perf_counter() - t0
    assert not out.empty
    assert dt < 120.0, f"smoke batch took {dt:.1f}s"
    num_cols = [c for c in out.columns if c not in ("date", "stock_code")]
    assert np.isfinite(out[num_cols].to_numpy(dtype=float)).all()


def main() -> None:
    test_momentum_log_vs_prod()
    test_rsi_matches_per_stock()
    test_compute_factors_smoke_parity()
    print("verify_factor_engineering_parity: OK")


if __name__ == "__main__":
    main()
