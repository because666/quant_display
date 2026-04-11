from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data_loader import generate_query_datasets


def main() -> None:
    rng = np.random.default_rng(0)
    n_stocks = 30
    # 让日期覆盖 2014-2024（用于验证 train/val/test 分割边界）
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
                    # simulate factors
                    "mom_1m": float(rng.normal(0, 1)),
                    "volatility_4w": float(rng.normal(0, 1)),
                    "avg_volume_4w": float(rng.normal(0, 1)),
                    "rsi_14": float(rng.normal(0, 1)),
                }
            )

    weekly_df = pd.DataFrame(rows)
    out_dir = Path("data/query_smoke_out")
    if out_dir.exists():
        # overwrite
        import shutil

        shutil.rmtree(out_dir)

    out = generate_query_datasets(
        weekly_df,
        output_dir=out_dir,
        train_end="2020-12-31",
        val_end="2022-12-31",
        forward_weeks=1,
    )
    assert out["train"].exists()
    assert out["val"].exists()
    assert out["test"].exists()

    train_df = pd.read_parquet(out["train"])
    # Ensure each date group has samples
    group_sizes = train_df.groupby("date").size()
    assert (group_sizes > 0).all()

    # Ensure label column exists
    assert "future_return_1w" in train_df.columns
    # Ensure features are only factor columns plus group info
    factor_cols = [c for c in train_df.columns if c not in {"date", "stock_code", "future_return_1w", "group_id", "group_size"}]
    assert len(factor_cols) >= 1
    print("data_loader smoke ok")


if __name__ == "__main__":
    main()

