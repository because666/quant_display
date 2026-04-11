from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from src.data_loader import generate_query_datasets


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def _compute_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _max_drawdown(window_prices: np.ndarray) -> float:
    peak = np.maximum.accumulate(window_prices)
    dd = window_prices / peak - 1.0
    return float(-np.min(dd))


def _zscore_by_date(df: pd.DataFrame, factor_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in factor_cols:
        g = out.groupby("date")[col]
        mean = g.transform("mean")
        std = g.transform(lambda s: s.std(ddof=0))
        z = (out[col] - mean) / std.replace(0, np.nan)
        out[col] = z.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-10, 10)
    return out


def main() -> None:
    weekly_base_path = DATA_DIR / "weekly_base_real.parquet"
    weekly_factors_path = DATA_DIR / "weekly_factors.parquet"
    weekly_model_input_path = DATA_DIR / "weekly_model_input.parquet"

    if not weekly_base_path.exists():
        raise FileNotFoundError(f"Missing {weekly_base_path}. Run weekly base build first.")

    base = pd.read_parquet(weekly_base_path)
    base["date"] = pd.to_datetime(base["date"])
    base["stock_code"] = base["stock_code"].astype(str)
    base = base.sort_values(["stock_code", "date"]).reset_index(drop=True)

    factors_all: list[pd.DataFrame] = []
    for code, gdf in tqdm(base.groupby("stock_code", sort=False), desc="Computing factors (low-mem)"):
        d = gdf.copy()
        d = d.sort_values("date").reset_index(drop=True)

        close = pd.to_numeric(d["close"], errors="coerce")
        ret = close.pct_change()
        ret_lag = ret.shift(1)
        close_lag = close.shift(1)

        vol = pd.to_numeric(d.get("volume", np.nan), errors="coerce")
        vol_lag = vol.shift(1)
        turnover = pd.to_numeric(d.get("turnover", np.nan), errors="coerce")
        turnover_lag = turnover.shift(1)

        out = pd.DataFrame({"date": d["date"], "stock_code": code})
        out["mom_1m"] = (1 + ret_lag).rolling(4).apply(np.prod, raw=True) - 1
        out["mom_3m"] = (1 + ret_lag).rolling(12).apply(np.prod, raw=True) - 1
        out["mom_6m"] = (1 + ret_lag).rolling(24).apply(np.prod, raw=True) - 1
        out["volatility_4w"] = ret_lag.rolling(4).std(ddof=0)
        out["volatility_8w"] = ret_lag.rolling(8).std(ddof=0)
        out["volatility_12w"] = ret_lag.rolling(12).std(ddof=0)
        out["max_retreat_8w"] = close_lag.rolling(8).apply(_max_drawdown, raw=True)
        out["avg_volume_4w"] = vol_lag.rolling(4).mean()
        out["avg_volume_8w"] = vol_lag.rolling(8).mean()
        out["turnover_avg_4w"] = turnover_lag.rolling(4).mean()
        out["turnover_avg_8w"] = turnover_lag.rolling(8).mean()
        out["rsi_14"] = _compute_rsi(close, 14).shift(1)
        out["rsi_21"] = _compute_rsi(close, 21).shift(1)
        out["ma_ratio_4w"] = close_lag / close_lag.rolling(4).mean() - 1
        out["ma_ratio_12w"] = close_lag / close_lag.rolling(12).mean() - 1
        factors_all.append(out)

    factors = pd.concat(factors_all, ignore_index=True)
    factor_cols = [c for c in factors.columns if c not in {"date", "stock_code"}]
    factors = _zscore_by_date(factors, factor_cols=factor_cols)
    factors.to_parquet(weekly_factors_path, index=False)
    print(f"[Stage2-LowMem] weekly_factors saved: {weekly_factors_path} shape={factors.shape}")

    model_input = base[["date", "stock_code", "close"]].merge(factors, on=["date", "stock_code"], how="inner")
    model_input = model_input.sort_values(["stock_code", "date"]).reset_index(drop=True)
    model_input.to_parquet(weekly_model_input_path, index=False)
    print(f"[Stage2-LowMem] weekly_model_input saved: {weekly_model_input_path} shape={model_input.shape}")

    out = generate_query_datasets(
        model_input,
        output_dir=DATA_DIR,
        train_end="2020-12-31",
        val_end="2022-12-31",
        forward_weeks=1,
    )
    print(f"[Stage2-LowMem] datasets generated: {out}")

    # Keep explicit factor columns for realtime module compatibility.
    with open(DATA_DIR / "factor_columns.pkl", "wb") as f:
        pickle.dump(factor_cols, f)


if __name__ == "__main__":
    main()
