from __future__ import annotations

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.data_loader import generate_query_datasets
from src.feature_engineering import compute_factors


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR = PROJECT_ROOT / "data"
WEEKLY_BASE_PATH = DATA_DIR / "weekly_base.parquet"
WEEKLY_FACTORS_PATH = DATA_DIR / "weekly_factors.parquet"
WEEKLY_MODEL_INPUT_PATH = DATA_DIR / "weekly_model_input.parquet"


def build_weekly_base_from_raw(raw_dir: Path) -> pd.DataFrame:
    parquet_files = sorted(raw_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No raw parquet files found in: {raw_dir}")

    rows: list[pd.DataFrame] = []
    for file_path in tqdm(parquet_files, desc="Resampling daily->weekly"):
        df = pd.read_parquet(file_path)
        if df.empty:
            continue

        if "date" not in df.columns or "stock_code" not in df.columns or "close" not in df.columns:
            continue

        _df = df.copy()
        _df["date"] = pd.to_datetime(_df["date"], errors="coerce")
        _df = _df.dropna(subset=["date"]).sort_values("date")
        if _df.empty:
            continue

        stock_code = str(_df["stock_code"].iloc[0])
        _df = _df.set_index("date")

        agg = {"close": "last"}
        if "volume" in _df.columns:
            agg["volume"] = "sum"
        if "amount" in _df.columns:
            agg["amount"] = "sum"
        if "turnover" in _df.columns:
            agg["turnover"] = "mean"

        weekly = _df.resample("W-FRI").agg(agg).dropna(subset=["close"])
        if weekly.empty:
            continue

        weekly = weekly.reset_index()
        weekly["stock_code"] = stock_code
        rows.append(weekly)

    if not rows:
        raise RuntimeError("No weekly data generated from raw parquet files.")

    weekly_df = pd.concat(rows, ignore_index=True)
    weekly_df = weekly_df.sort_values(["stock_code", "date"]).reset_index(drop=True)
    return weekly_df


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("[Stage2] Step1: build weekly base data from raw parquet")
    weekly_base_df = build_weekly_base_from_raw(RAW_DIR)
    weekly_base_df.to_parquet(WEEKLY_BASE_PATH, index=False)
    print(
        f"[Stage2] weekly_base saved: {WEEKLY_BASE_PATH} "
        f"shape={weekly_base_df.shape}, date_range=({weekly_base_df['date'].min()} -> {weekly_base_df['date'].max()})"
    )

    print("[Stage2] Step2: compute factors from weekly base")
    weekly_factors_df = compute_factors(weekly_base_df, output_path=WEEKLY_FACTORS_PATH)
    print(f"[Stage2] weekly_factors saved: {WEEKLY_FACTORS_PATH} shape={weekly_factors_df.shape}")

    print("[Stage2] Step3: build model input weekly_df (close + selected factors)")
    weekly_model_input = weekly_base_df[["date", "stock_code", "close"]].merge(
        weekly_factors_df, on=["date", "stock_code"], how="inner"
    )
    weekly_model_input = weekly_model_input.sort_values(["stock_code", "date"]).reset_index(drop=True)
    weekly_model_input.to_parquet(WEEKLY_MODEL_INPUT_PATH, index=False)
    print(f"[Stage2] weekly_model_input saved: {WEEKLY_MODEL_INPUT_PATH} shape={weekly_model_input.shape}")

    print("[Stage2] Step4: generate query train/val/test datasets")
    out = generate_query_datasets(
        weekly_model_input,
        output_dir=DATA_DIR,
        train_end="2020-12-31",
        val_end="2022-12-31",
        forward_weeks=1,
    )
    print(f"[Stage2] datasets generated: {out}")


if __name__ == "__main__":
    main()
