"""Convert Qlib CN bin data into project raw parquet files.

Output schema follows `src.data_fetcher.download_daily_data`:
date, open, high, low, close, volume, amount, turnover, pct_chg,
is_suspended, is_limit_up, is_limit_down, stock_code
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm


def _read_calendar(calendar_path: Path) -> pd.DatetimeIndex:
    cal = pd.read_csv(calendar_path, header=None).iloc[:, 0].astype(str)
    return pd.to_datetime(cal, errors="coerce")


def _read_qlib_bin_series(bin_path: Path, calendar: pd.DatetimeIndex) -> pd.Series:
    if not bin_path.exists():
        return pd.Series(dtype=float)
    arr = np.fromfile(str(bin_path), dtype="<f4")
    if arr.size <= 1:
        return pd.Series(dtype=float)
    start_idx = int(round(float(arr[0])))
    values = arr[1:]
    end_idx = start_idx + len(values)
    if start_idx < 0 or end_idx > len(calendar):
        return pd.Series(dtype=float)
    idx = calendar[start_idx:end_idx]
    return pd.Series(values, index=idx)


def _to_stock_code(symbol_dir_name: str) -> str | None:
    s = symbol_dir_name.strip().lower()
    if len(s) != 8:
        return None
    if not (s.startswith("sh") or s.startswith("sz") or s.startswith("bj")):
        return None
    digits = s[2:]
    if not digits.isdigit():
        return None
    return digits


def _build_daily_df(symbol_dir: Path, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    fields = {
        "open": "open.day.bin",
        "high": "high.day.bin",
        "low": "low.day.bin",
        "close": "close.day.bin",
        "volume": "volume.day.bin",
        "amount": "amount.day.bin",
    }
    series_map: dict[str, pd.Series] = {}
    for out_col, file_name in fields.items():
        series_map[out_col] = _read_qlib_bin_series(symbol_dir / file_name, calendar)

    if series_map["close"].empty:
        return pd.DataFrame()

    df = pd.concat(series_map, axis=1).reset_index()
    # DatetimeIndex name may be "index", 0, or others depending on source.
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Keep only rows where core OHLC exists.
    df = df.dropna(subset=["open", "high", "low", "close"])
    if df.empty:
        return df

    # Align with existing project semantics.
    df["turnover"] = np.nan
    df["pct_chg"] = df["close"].pct_change() * 100.0
    prev_close = df["close"].shift(1)
    df["is_suspended"] = (df["volume"].fillna(0) == 0) & prev_close.notna() & (df["close"] == prev_close)
    df["is_limit_up"] = (df["pct_chg"].fillna(0) >= 9.5) & (~df["is_suspended"])
    df["is_limit_down"] = (df["pct_chg"].fillna(0) <= -9.5) & (~df["is_suspended"])
    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert qlib_bin features to raw parquet files.")
    parser.add_argument("--qlib-dir", type=Path, default=Path("data/qlib_cn_data/qlib_bin"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--start-date", type=str, default="2014-01-01")
    parser.add_argument("--end-date", type=str, default="2024-12-31")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of symbols for smoke test")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing parquet files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    qlib_dir = args.qlib_dir
    features_root = qlib_dir / "features"
    calendar_path = qlib_dir / "calendars" / "day.txt"
    raw_dir = args.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not features_root.exists():
        raise FileNotFoundError(f"Qlib features directory not found: {features_root}")
    if not calendar_path.exists():
        raise FileNotFoundError(f"Qlib calendar file not found: {calendar_path}")

    start_date = pd.to_datetime(args.start_date)
    end_date = pd.to_datetime(args.end_date)
    calendar = _read_calendar(calendar_path)

    symbol_dirs = sorted([p for p in features_root.iterdir() if p.is_dir()])
    if args.limit > 0:
        symbol_dirs = symbol_dirs[: args.limit]

    ok_count = 0
    skip_count = 0
    fail_count = 0

    for symbol_dir in tqdm(symbol_dirs, desc="Converting qlib bins"):
        stock_code = _to_stock_code(symbol_dir.name)
        if stock_code is None:
            skip_count += 1
            continue

        out_path = raw_dir / f"{stock_code}.parquet"
        if out_path.exists() and not args.overwrite:
            skip_count += 1
            continue

        try:
            df = _build_daily_df(symbol_dir, calendar)
            if df.empty:
                skip_count += 1
                continue

            df = df[(df["date"] >= start_date) & (df["date"] <= end_date)].copy()
            if df.empty:
                skip_count += 1
                continue

            df["stock_code"] = stock_code
            out_cols = [
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "turnover",
                "pct_chg",
                "is_suspended",
                "is_limit_up",
                "is_limit_down",
                "stock_code",
            ]
            df[out_cols].to_parquet(out_path, index=False)
            ok_count += 1
        except Exception:  # noqa: BLE001
            fail_count += 1

    print(f"Done. ok={ok_count}, skipped={skip_count}, failed={fail_count}, out_dir={raw_dir}")


if __name__ == "__main__":
    main()
