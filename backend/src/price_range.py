"""
基于日线 ATR 与近期高低点的价格区间工具：买入参考区间、卖出目标区间。

数据源：`data_fetcher.load_cached_data`（本地 parquet，与实时更新模块一致）。
"""
from __future__ import annotations

import math
import threading
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data_fetcher import RAW_DATA_DIR, _normalize_stock_code, load_cached_data

# (code, period) -> (mtime_ns, size_bytes, atr) — 文件未变时直接返回 atr，避免重复 IO 与滚动计算
_atr_cache: dict[tuple[str, int], tuple[int, int, float]] = {}
_cache_lock = threading.RLock()


def _parquet_stat(path: Path | str) -> tuple[int, int] | None:
    p = Path(path)
    if not p.exists():
        return None
    st = p.stat()
    return (st.st_mtime_ns, st.st_size)


def clear_atr_cache() -> None:
    """单元测试或强制重算时清空 ATR 缓存。"""
    with _cache_lock:
        _atr_cache.clear()


def _prepare_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    need = {"high", "low", "close", "date"}
    if not need.issubset(set(df.columns)):
        raise ValueError(f"日线数据缺少列，需要: {sorted(need)}")
    out = df.sort_values("date").reset_index(drop=True)
    for c in ("high", "low", "close"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["high", "low", "close"])
    return out


def _true_range_series(df: pd.DataFrame) -> pd.Series:
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr


def _compute_atr_from_df(df: pd.DataFrame, period: int) -> float:
    tr = _true_range_series(df)
    atr_s = tr.rolling(window=period, min_periods=period).mean()
    atr = float(atr_s.iloc[-1])
    if not math.isfinite(atr) or atr < 0:
        raise ValueError("ATR 计算结果无效")
    return atr


def _support_resistance_from_df(df: pd.DataFrame, lookback_days: int) -> dict[str, float]:
    if len(df) < lookback_days:
        raise ValueError(f"历史 K 线不足，需要至少 {lookback_days} 根，当前 {len(df)}")
    tail = df.iloc[-lookback_days:]
    lo = float(np.nanmin(tail["low"].astype(float).to_numpy()))
    hi = float(np.nanmax(tail["high"].astype(float).to_numpy()))
    if not math.isfinite(lo) or not math.isfinite(hi):
        raise ValueError("支撑/阻力计算无效")
    return {"support": lo, "resistance": hi}


def calculate_atr(stock_code: str, period: int = 14) -> float:
    """
    基于日线计算 ATR（真实波幅的简单移动平均，周期 ``period``）。
    TR = max(high-low, |high-pre_close|, |low-pre_close|)；ATR 为 TR 的算术平均。

    返回最后一根 K 线对应的 ATR（元）。结果按「最后交易日」缓存，同日重复调用不重复滚动计算。
    """
    if period < 2:
        raise ValueError("period 至少为 2")

    code = _normalize_stock_code(stock_code)
    path = RAW_DATA_DIR / f"{code}.parquet"
    key = (code, period)
    stat_now = _parquet_stat(path)
    if stat_now is not None:
        with _cache_lock:
            hit = _atr_cache.get(key)
            if hit is not None and hit[0] == stat_now[0] and hit[1] == stat_now[1]:
                return hit[2]

    df = _prepare_ohlc(load_cached_data(code))
    if len(df) < period + 1:
        raise ValueError(f"历史 K 线不足，需要至少 {period + 1} 根，当前 {len(df)}")

    atr = _compute_atr_from_df(df, period)

    stat_after = _parquet_stat(path)
    if stat_after is not None:
        with _cache_lock:
            _atr_cache[key] = (stat_after[0], stat_after[1], atr)
    return atr


def calculate_support_resistance(stock_code: str, lookback_days: int = 20) -> dict[str, float]:
    """
    最近 ``lookback_days`` 根日线内的最低价（支撑）与最高价（阻力）。
    """
    if lookback_days < 1:
        raise ValueError("lookback_days 至少为 1")

    code = _normalize_stock_code(stock_code)
    df = _prepare_ohlc(load_cached_data(code))
    return _support_resistance_from_df(df, lookback_days)


def get_price_range(stock_code: str, current_price: float) -> dict[str, Any]:
    """
    根据当前价与 ATR、近期支撑阻力，给出买入/卖出参考区间（元）。

    - 买入参考区间：[current - 0.5*ATR, current - 0.2*ATR]，再与支撑位对齐：
      买入下限不低于近期支撑；上沿不低于下沿。
    - 卖出目标区间：[current + 0.2*ATR, current + 0.5*ATR]，再与阻力位对齐：
      卖出上限不高于近期阻力；下沿不高于上沿。

    返回: ``buy_low``, ``buy_high``, ``sell_low``, ``sell_high``；另附 ``atr``、``support``、``resistance`` 便于排查。
    """
    px = float(current_price)
    if not math.isfinite(px) or px <= 0:
        raise ValueError("current_price 须为正数")

    code = _normalize_stock_code(stock_code)
    path = RAW_DATA_DIR / f"{code}.parquet"
    period, lookback = 14, 20
    need = max(period + 1, lookback)
    key_atr = (code, period)

    df = _prepare_ohlc(load_cached_data(code))
    if len(df) < need:
        raise ValueError(f"历史 K 线不足，需要至少 {need} 根，当前 {len(df)}")

    stat_now = _parquet_stat(path)
    atr: float
    if stat_now is not None:
        with _cache_lock:
            hit = _atr_cache.get(key_atr)
            if hit is not None and hit[0] == stat_now[0] and hit[1] == stat_now[1]:
                atr = hit[2]
            else:
                atr = _compute_atr_from_df(df, period)
                _atr_cache[key_atr] = (stat_now[0], stat_now[1], atr)
    else:
        atr = _compute_atr_from_df(df, period)

    sr = _support_resistance_from_df(df, lookback)
    support = float(sr["support"])
    resistance = float(sr["resistance"])

    buy_low_raw = px - 0.5 * atr
    buy_high_raw = px - 0.2 * atr
    sell_low_raw = px + 0.2 * atr
    sell_high_raw = px + 0.5 * atr

    buy_low = max(buy_low_raw, support)
    buy_high = max(buy_high_raw, buy_low)
    sell_high = min(sell_high_raw, resistance)
    sell_low = min(sell_low_raw, sell_high)

    # 若阻力极低导致 sell 区间退化，保持 sell_low <= sell_high
    if sell_low > sell_high:
        sell_low = sell_high

    out = {
        "buy_low": float(buy_low),
        "buy_high": float(buy_high),
        "sell_low": float(sell_low),
        "sell_high": float(sell_high),
        "atr": float(atr),
        "support": support,
        "resistance": resistance,
    }
    return out


def _main() -> None:
    import argparse

    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="ATR / 价格区间试算")
    p.add_argument("code", help="股票代码，如 000001")
    p.add_argument("--price", type=float, required=True, help="当前价")
    args = p.parse_args()
    r = get_price_range(args.code, args.price)
    for k, v in r.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    _main()
