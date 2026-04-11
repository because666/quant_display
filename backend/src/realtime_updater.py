from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import akshare as ak
import numpy as np
import pandas as pd
from tqdm import tqdm

from src.data_fetcher import META_DATA_DIR, RAW_DATA_DIR, cache_daily_data, download_daily_data
from src.feature_engineering import compute_factors
from src.stock_pool import get_surviving_stocks


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FACTOR_COLUMNS_PATH = DATA_DIR / "factor_columns.pkl"


def _load_factor_columns(required: bool = True) -> list[str]:
    if not FACTOR_COLUMNS_PATH.exists():
        if required:
            raise FileNotFoundError(
                f"factor_columns.pkl not found at {FACTOR_COLUMNS_PATH}. Run task4/feature preparation first."
            )
        return []
    import pickle

    with open(FACTOR_COLUMNS_PATH, "rb") as f:
        cols = pickle.load(f)
    if not isinstance(cols, list) or not all(isinstance(x, str) for x in cols):
        raise TypeError("factor_columns.pkl format invalid.")
    return cols


def get_latest_trading_day() -> str:
    """
    返回最近一个交易日（YYYY-MM-DD 字符串）。
    """
    trade_df = ak.tool_trade_date_hist_sina()
    if trade_df is None or trade_df.empty or "trade_date" not in trade_df.columns:
        raise RuntimeError("ak.tool_trade_date_hist_sina() returned no trade_date.")

    trade_dates = pd.to_datetime(trade_df["trade_date"], errors="coerce")
    trade_dates = trade_dates.dropna().sort_values()

    today = pd.Timestamp.today().normalize()
    eligible = trade_dates[trade_dates <= today]
    if eligible.empty:
        raise RuntimeError("No eligible trading date found (check system clock/timezone).")

    latest = eligible.iloc[-1]
    return latest.strftime("%Y-%m-%d")


def _read_daily_parquet(stock_code: str) -> pd.DataFrame | None:
    code = str(stock_code).strip().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    path = RAW_DATA_DIR / f"{code}.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    return df


def _write_daily_parquet(stock_code: str, df: pd.DataFrame) -> None:
    cache_daily_data(stock_code, df)


def fetch_latest_data(stock_list: pd.DataFrame, latest_date: str) -> pd.DataFrame:
    """
    获取 latest_date 日所有股票的日线数据，并增量更新本地缓存。
    返回：合并后的 DataFrame（包含 latest_date 的记录）。
    """
    if stock_list is None or stock_list.empty:
        return pd.DataFrame()

    date_ts = pd.to_datetime(latest_date)
    latest_str = date_ts.strftime("%Y-%m-%d")

    codes = stock_list["code"].astype(str).tolist() if "code" in stock_list.columns else stock_list.iloc[:, 0].astype(str).tolist()
    combined: list[pd.DataFrame] = []

    for code in tqdm(codes, desc=f"Fetch daily bars for {latest_str}"):
        try:
            existing = _read_daily_parquet(code)
            need_download = True
            if existing is not None and not existing.empty and "date" in existing.columns:
                existing_max = pd.to_datetime(existing["date"], errors="coerce").max()
                if pd.notna(existing_max) and existing_max.normalize() >= date_ts:
                    need_download = False

            if not need_download:
                df_latest = existing[existing["date"] == date_ts].copy()
                if not df_latest.empty:
                    combined.append(df_latest)
                continue

            df_new = download_daily_data(code, latest_str, latest_str)
            if df_new.empty:
                continue

            # merge & dedupe
            if existing is None or existing.empty:
                merged = df_new
            else:
                merged = pd.concat([existing, df_new], ignore_index=True)
                merged["date"] = pd.to_datetime(merged["date"], errors="coerce")
                merged = merged.dropna(subset=["date"]).sort_values("date")
                merged = merged.drop_duplicates(subset=["date", "stock_code"], keep="last")

            _write_daily_parquet(code, merged)
            combined.append(df_new)
        except Exception as exc:  # noqa: BLE001
            logger.exception("fetch_latest_data failed for %s: %s", code, exc)
            continue

    if not combined:
        return pd.DataFrame()
    return pd.concat(combined, ignore_index=True)


def update_weekly_cross_section(latest_date: str, stock_codes: Iterable[str] | None = None, *, history_weeks: int = 60) -> pd.DataFrame:
    """
    生成用于“当前预测”的最新周频截面：
    - 从本地 daily parquet 读取每只股票最近 history_weeks 的日线
    - 将每周取最后一个交易日作为周频截面（date=该交易日）
    """
    latest_ts = pd.to_datetime(latest_date)
    start_ts = latest_ts - pd.Timedelta(weeks=history_weeks)

    # 如果 latest_date 不是周五，则取“最近一个周五”作为截面周末。
    weekday = latest_ts.weekday()  # Mon=0 ... Fri=4
    delta_days = (weekday - 4) % 7
    latest_week_end_ts = latest_ts - pd.Timedelta(days=delta_days)

    if stock_codes is None:
        pool = get_surviving_stocks()
        stock_codes = pool["code"].astype(str).tolist()

    rows: list[pd.DataFrame] = []
    for code in tqdm(list(stock_codes), desc="Build weekly cross-section"):
        daily = _read_daily_parquet(code)
        if daily is None or daily.empty:
            # 如果缺历史，至少拉取需要的窗口
            daily = download_daily_data(
                code,
                start_ts.strftime("%Y-%m-%d"),
                latest_ts.strftime("%Y-%m-%d"),
            )
            if not daily.empty:
                _write_daily_parquet(code, daily)

        if daily is None or daily.empty:
            continue

        daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
        daily = daily.dropna(subset=["date"])
        daily = daily[(daily["date"] >= start_ts) & (daily["date"] <= latest_ts)].copy()
        if daily.empty:
            continue

        # week period ends on Friday: W-FRI, group by that and take the last row.
        daily["week_period"] = daily["date"].dt.to_period("W-FRI")
        weekly_last = (
            daily.sort_values(["date"])
            .groupby("week_period", as_index=False)
            .tail(1)
        )

        weekly_last = weekly_last.drop(columns=["week_period"], errors="ignore")
        # 丢弃未完成周（latest_date 所在周，除非 latest_date 本身就是周五）
        weekly_last = weekly_last[weekly_last["date"] <= latest_week_end_ts].copy()
        if weekly_last.empty:
            continue
        rows.append(weekly_last)

    if not rows:
        return pd.DataFrame()

    weekly_df = pd.concat(rows, ignore_index=True)
    # Keep minimal set; compute_factors will require close/volume/turnover if available.
    keep_cols = [c for c in ["date", "stock_code", "close", "volume", "amount", "turnover"] if c in weekly_df.columns]
    weekly_df = weekly_df[keep_cols].sort_values(["stock_code", "date"]).reset_index(drop=True)
    return weekly_df


def compute_current_factors(
    latest_date: str,
    *,
    history_weeks: int = 60,
    stock_codes: Iterable[str] | None = None,
) -> pd.DataFrame:
    """
    基于最新截面计算因子，并输出最新一周的因子表。
    """
    factor_cols = _load_factor_columns(required=False)
    weekly_df = update_weekly_cross_section(
        latest_date, stock_codes=stock_codes, history_weeks=history_weeks
    )
    if weekly_df.empty:
        raise RuntimeError("weekly_df is empty when computing current factors.")

    out_path = DATA_DIR / "current_weekly_factors.parquet"
    factors_df = compute_factors(
        weekly_df,
        output_path=out_path,
        selected_factor_cols=factor_cols if factor_cols else None,
    )

    # 如果 factor_columns.pkl 与当前计算结果不匹配（交集为空），
    # 回退到“自动选择低相关因子”，避免无因子输出。
    if factor_cols and not any(c in factors_df.columns for c in factor_cols):
        factors_df = compute_factors(
            weekly_df,
            output_path=out_path,
            selected_factor_cols=None,
        )

    latest_ts = pd.to_datetime(latest_date)
    # compute_factors 输出的 date 是“周频最后交易日”
    latest_week_ts = pd.to_datetime(factors_df["date"]).max()
    latest_week_df = factors_df[factors_df["date"] == latest_week_ts].copy()
    return latest_week_df


def get_current_prediction_data(
    stock_list: pd.DataFrame | None = None,
    latest_date: str | None = None,
    *,
    history_weeks: int = 60,
) -> pd.DataFrame:
    """
    返回可直接用于模型预测的最新因子矩阵：
    - date：最新周频截面对应的周末交易日
    - stock_code
    - 因子列（与 factor_columns.pkl 一致）
    """
    if latest_date is None:
        latest_date = get_latest_trading_day()

    if stock_list is None:
        stock_list = get_surviving_stocks()

    # 增量拉取最新交易日日线，更新本地缓存
    fetch_latest_data(stock_list, latest_date=latest_date)

    codes = stock_list["code"].astype(str).tolist() if "code" in stock_list.columns else []
    factors_df = compute_current_factors(
        latest_date,
        history_weeks=history_weeks,
        stock_codes=codes if codes else None,
    )
    factor_cols = _load_factor_columns(required=False)

    if factor_cols:
        missing = [c for c in factor_cols if c not in factors_df.columns]
        if missing:
            print(f"[WARN] factor_columns mismatch, missing={missing}")

    date_val = factors_df["date"].iloc[0]
    if factor_cols:
        available = [c for c in factor_cols if c in factors_df.columns]
        out = factors_df[["stock_code", *available]].copy()
    else:
        # fallback: use whatever compute_factors selected on the latest window
        out = factors_df.drop(columns=["date"]).copy()
    out.insert(0, "date", date_val)
    return out

