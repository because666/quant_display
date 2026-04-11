from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data_loader import generate_query_datasets


def main() -> None:
    rng = np.random.default_rng(0)
    n_stocks = 60
    # 足够覆盖 2014-2024，确保 train/val/test 都有数据
    n_weeks = 520

    stock_codes = [f"{i:06d}" for i in range(1, n_stocks + 1)]
    dates = pd.date_range("2014-01-03", periods=n_weeks, freq="W-FRI")

    rows: list[dict] = []
    for code in stock_codes:
        rets = rng.normal(0.001, 0.03, size=n_weeks)
        close = 50 * np.cumprod(1 + rets)
        for d, c in zip(dates, close):
            rows.append(
                {
                    "date": d,
                    "stock_code": code,
                    "close": float(c),
                    # 模拟因子列（会被 data_loader 自动推断为 factor_cols）
                    "mom_1m": float(rng.normal(0, 1)),
                    "volatility_4w": float(rng.normal(0, 1)),
                    "avg_volume_4w": float(rng.normal(0, 1)),
                    "rsi_14": float(rng.normal(0, 1)),
                }
            )

    weekly_df = pd.DataFrame(rows)
    out_dir = Path("data")

    # 覆盖输出（便于你反复联调）
    generate_query_datasets(
        weekly_df,
        output_dir=out_dir,
        train_end="2020-12-31",
        val_end="2022-12-31",
        forward_weeks=1,
    )

    # quick validation
    train_df = pd.read_parquet(out_dir / "train.parquet")
    group_sizes = train_df.groupby("date").size()
    assert (group_sizes > 0).all()
    assert "future_return_1w" in train_df.columns
    print("task4 smoke written to backend/data successfully")


if __name__ == "__main__":
    main()

