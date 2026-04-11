from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

import akshare as ak
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
META_DATA_DIR = PROJECT_ROOT / "data" / "meta"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
META_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _retry_call(func, *args, retries: int = 3, sleep_seconds: float = 1.5, **kwargs):
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries:
                time.sleep(sleep_seconds * attempt)
    raise RuntimeError(f"Call failed after {retries} retries: {func.__name__}") from last_error


def _normalize_stock_code(code: str) -> str:
    return str(code).strip().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")


def _find_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _extract_info_value(info_df: pd.DataFrame, keys: list[str]) -> str | None:
    if info_df is None or info_df.empty or "item" not in info_df.columns or "value" not in info_df.columns:
        return None
    item_series = info_df["item"].astype(str)
    for key in keys:
        matched = info_df[item_series.str.contains(key, na=False)]
        if not matched.empty:
            value = str(matched.iloc[0]["value"]).strip()
            if value:
                return value
    return None


def _fetch_stock_meta(stock_code: str) -> dict | None:
    try:
        info_df = _retry_call(ak.stock_individual_info_em, symbol=stock_code, retries=2, sleep_seconds=1.0)
    except Exception:  # noqa: BLE001
        return None

    listing_raw = _extract_info_value(info_df, ["上市时间", "上市日期"])
    delist_raw = _extract_info_value(info_df, ["退市时间", "退市日期"])
    listing_date = pd.to_datetime(listing_raw, errors="coerce")
    delist_date = pd.to_datetime(delist_raw, errors="coerce")
    is_delisted = pd.notna(delist_date)
    return {
        "listing_date": listing_date,
        "delist_date": delist_date,
        "is_delisted": bool(is_delisted),
    }


def get_stock_list(strict_universe: bool = True, refresh_cache: bool = False) -> pd.DataFrame:
    """
    获取 A 股股票列表。
    - strict_universe=True: 严格筛选 2014 年前上市且未退市，默认启用（约 3000 只）
    - refresh_cache=True: 强制刷新股票池缓存

    返回列：code, name, listing_date
    """
    if strict_universe:
        from src.stock_pool import get_surviving_stocks

        return get_surviving_stocks(
            start_date="2014-01-01",
            end_date=pd.Timestamp.today().strftime("%Y-%m-%d"),
            refresh_cache=refresh_cache,
        )

    raw_df = _retry_call(ak.stock_info_a_code_name)
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["code", "name", "listing_date"])

    df = raw_df.copy()
    code_col = _find_column(df, ["code", "代码", "证券代码"])
    name_col = _find_column(df, ["name", "名称", "证券简称"])
    list_col = _find_column(df, ["listing_date", "上市日期", "list_date", "上市时间"])

    if code_col is None or name_col is None:
        raise ValueError("stock_info_a_code_name() response missing required code/name columns.")

    result = pd.DataFrame(
        {
            "code": df[code_col].astype(str).map(_normalize_stock_code),
            "name": df[name_col].astype(str),
        }
    )

    if list_col is not None:
        result["listing_date"] = pd.to_datetime(df[list_col], errors="coerce")
    else:
        result["listing_date"] = pd.NaT

    # 初筛：去掉明显退市代码名
    result = result[~result["name"].str.contains(r"退", na=False)].copy()

    result = result.drop_duplicates(subset=["code"]).reset_index(drop=True)
    return result[["code", "name", "listing_date"]]


def download_daily_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    下载单只股票前复权日线数据，并添加 is_suspended 标志。
    停牌定义：当日成交量为 0 且收盘价与前一日收盘价相同。
    """
    code = _normalize_stock_code(stock_code)
    df = _retry_call(
        ak.stock_zh_a_hist,
        symbol=code,
        period="daily",
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
        adjust="qfq",
    )

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

    if df is None or df.empty:
        return pd.DataFrame(columns=out_cols)

    col_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "换手率": "turnover",
        "涨跌幅": "pct_chg",
    }

    data = df.rename(columns=col_map).copy()

    for col in ["open", "close", "high", "low", "volume", "amount", "turnover", "pct_chg"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    if "amount" not in data.columns:
        data["amount"] = float("nan")
    if "turnover" not in data.columns:
        data["turnover"] = float("nan")

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["stock_code"] = code
    data = data.sort_values("date").dropna(subset=["date"]).reset_index(drop=True)

    prev_close = data["close"].shift(1)
    data["is_suspended"] = (
        (data["volume"].fillna(0) == 0) & prev_close.notna() & (data["close"] == prev_close)
    )

    # 简化版涨跌停标记：基于涨跌幅阈值（未区分 ST 5% 规则）
    data["is_limit_up"] = (data["pct_chg"].fillna(0) >= 9.5) & (~data["is_suspended"])
    data["is_limit_down"] = (data["pct_chg"].fillna(0) <= -9.5) & (~data["is_suspended"])

    return data[out_cols]


def cache_daily_data(stock_code: str, df: pd.DataFrame) -> Path:
    code = _normalize_stock_code(stock_code)
    file_path = RAW_DATA_DIR / f"{code}.parquet"
    df.to_parquet(file_path, index=False)
    return file_path


def load_cached_data(
    stock_code: str,
    start_date: str = "20140101",
    end_date: str = pd.Timestamp.today().strftime("%Y%m%d"),
) -> pd.DataFrame:
    code = _normalize_stock_code(stock_code)
    file_path = RAW_DATA_DIR / f"{code}.parquet"
    if file_path.exists():
        return pd.read_parquet(file_path)

    start_str = start_date.replace("-", "")
    end_str = end_date.replace("-", "")
    df = download_daily_data(code, start_str, end_str)
    cache_daily_data(code, df)
    return df


def get_all_stocks_data(
    start_date: str = "20140101",
    end_date: str = pd.Timestamp.today().strftime("%Y%m%d"),
    return_merged: bool = False,
    strict_universe: bool = True,
) -> pd.DataFrame | None:
    """
    批量下载或读取全部股票数据。
    - 默认逐个保存 parquet，返回 None（节省内存）
    - return_merged=True 时返回合并后的 DataFrame
    """
    stocks = get_stock_list(strict_universe=strict_universe)
    if stocks.empty:
        return pd.DataFrame() if return_merged else None

    merged: list[pd.DataFrame] = []
    for code in tqdm(stocks["code"].tolist(), desc="Fetching A-share daily data"):
        try:
            df = load_cached_data(code, start_date=start_date, end_date=end_date)
            if return_merged:
                merged.append(df)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] skip {code}: {exc}")
            continue

    if return_merged:
        if not merged:
            return pd.DataFrame()
        return pd.concat(merged, ignore_index=True)
    return None


def _main_cli() -> None:
    import argparse

    from src.stock_pool import download_and_cache_all_stocks, get_surviving_stocks

    parser = argparse.ArgumentParser(description="A-share daily data fetcher")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Build surviving pool and download daily bars to data/raw/",
    )
    parser.add_argument("--start-date", default="2014-01-01", help="Pool filter & download start")
    parser.add_argument("--end-date", default="2024-12-31", help="Pool filter & download end")
    parser.add_argument(
        "--refresh-pool",
        action="store_true",
        help="Rebuild stock pool cache (surviving_stocks_*.parquet)",
    )
    args = parser.parse_args()
    if not args.download:
        parser.print_help()
        return

    pool = get_surviving_stocks(
        start_date=args.start_date,
        end_date=args.end_date,
        refresh_cache=args.refresh_pool,
    )
    print(f"Surviving pool size: {len(pool)}")
    download_and_cache_all_stocks(pool, args.start_date, args.end_date)


if __name__ == "__main__":
    _main_cli()
