from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

from src.feature_engineering import compute_factors


def main() -> None:
    rng = np.random.default_rng(42)
    n_stocks = 60
    n_weeks = 40

    stock_codes = [f"{i:06d}" for i in range(1, n_stocks + 1)]
    dates = pd.date_range("2016-01-01", periods=n_weeks, freq="W-FRI")

    rows: list[dict] = []
    for code in stock_codes:
        # random walk close
        rets = rng.normal(0.001, 0.03, size=n_weeks)
        close = 100 * np.cumprod(1 + rets)
        volume = rng.lognormal(mean=10, sigma=0.3, size=n_weeks)
        turnover = rng.uniform(0.01, 0.08, size=n_weeks)
        for d, c, v, t in zip(dates, close, volume, turnover):
            rows.append(
                {
                    "date": d,
                    "stock_code": code,
                    "close": float(c),
                    "volume": float(v),
                    "turnover": float(t),
                }
            )

    weekly_df = pd.DataFrame(rows)
    out = compute_factors(weekly_df, output_path=Path("data/weekly_factors_smoke.parquet"))
    factor_cols = [c for c in out.columns if c not in ("date", "stock_code")]
    print("factor_count=", len(factor_cols))
    assert 15 <= len(factor_cols) <= 20, "factor count out of range"
    print("smoke ok")


if __name__ == "__main__":
    main()

