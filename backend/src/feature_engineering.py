from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, TypeVar

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
WEEKLY_FACTORS_OUT_PATH = OUT_DIR / "weekly_factors.parquet"

# 可选：numba 加速滚动最大回撤（无 numba 时回退 pandas rolling.apply）
try:
    from numba import njit
except ImportError:
    njit = None  # type: ignore[misc, assignment]

T = TypeVar("T")


def _timed(label: str, log_fn: Callable[[str], None] | None) -> None:
    """在 log_fn 非空时记录自上一条计时点以来的耗时（秒）。"""
    if log_fn is None:
        return
    now = time.perf_counter()
    t0 = getattr(_timed, "_t0", now)
    log_fn(f"[FCT][timing] {label}: {now - t0:.3f}s")
    _timed._t0 = now  # type: ignore[attr-defined]


def _reset_timing() -> None:
    _timed._t0 = time.perf_counter()  # type: ignore[attr-defined]


def profile_if_requested(fn: Callable[..., T]) -> Callable[..., T]:
    """
    可选性能装饰器：设置环境变量 QUANT_LINE_PROFILE=1 且已安装 line_profiler 时生效。
    """
    if os.environ.get("QUANT_LINE_PROFILE", "").strip() in ("1", "true", "yes"):
        try:
            from line_profiler import profile as _lp_profile  # type: ignore[import-not-found]

            return _lp_profile(fn)  # type: ignore[return-value]
        except ImportError:
            pass
    return fn


def _drop_group_level_index(s: pd.Series) -> pd.Series:
    """groupby().rolling / ewm 在 pandas 3 常返回 (stock_code, row) 二级索引，对齐回默认行索引。"""
    if isinstance(s.index, pd.MultiIndex):
        return s.reset_index(level=0, drop=True)
    return s


def _require_columns(df: pd.DataFrame, candidates: Iterable[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"Required one of columns {list(candidates)} not found. Got: {list(df.columns)}")


def _safe_std(s: pd.Series) -> float:
    return float(s.std(ddof=0))


def apply_cross_sectional_transforms(
    df: pd.DataFrame,
    factor_cols: list[str],
    *,
    industry_col: str | None = None,
) -> pd.DataFrame:
    """
    预留跨股票联合变换（如行业中性化、对市值回归残差等）。

    当前版本不修改数据；未来可在此按 industry_col 分组去均值或接回归残差，
    再进入截面 Z-score。传入非 None 的 industry_col 时应实现具体逻辑并删除 NotImplemented。
    """
    if industry_col is not None:
        raise NotImplementedError(
            "Industry / multi-stock neutralization is not implemented; pass industry_col=None."
        )
    return df


def _zscore_by_date(df: pd.DataFrame, factor_cols: list[str]) -> pd.DataFrame:
    """
    对每个因子做截面（date）Z-score；一次 groupby + transform，避免按列重复 groupby。
    """
    df_out = df.copy()
    if not factor_cols:
        return df_out

    g = df_out.groupby("date", sort=False)[factor_cols]
    mean = g.transform("mean")
    std = g.transform(lambda x: x.std(ddof=0))
    z = (df_out[factor_cols] - mean) / std.replace(0, np.nan)
    z = z.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    df_out[factor_cols] = z.clip(-10, 10)
    return df_out


def _max_drawdown_magnitude(window_prices: np.ndarray) -> float:
    """
    在一个价格窗口内计算最大回撤幅度（>=0）。
    相对运行峰值：drawdown = p/peak - 1，返回 -min(drawdown)。
    """
    peak = np.maximum.accumulate(window_prices)
    drawdown = window_prices / peak - 1.0
    return float(-np.min(drawdown))


if njit is not None:  # pragma: no cover - optional dependency

    @njit(cache=True)  # type: ignore[misc]
    def _rolling_max_drawdown_numba(prices: np.ndarray, window: int, out: np.ndarray) -> None:
        n = len(prices)
        for i in range(n):
            if i < window - 1:
                out[i] = np.nan
                continue
            peak = prices[i - window + 1]
            worst_dd = 0.0
            for j in range(i - window + 1, i + 1):
                pj = prices[j]
                if pj > peak:
                    peak = pj
                dd = pj / peak - 1.0
                if dd < worst_dd:
                    worst_dd = dd
            out[i] = -worst_dd


else:
    _rolling_max_drawdown_numba = None  # type: ignore[assignment,misc]


def _assign_rolling_max_drawdown(
    df: pd.DataFrame,
    *,
    price_col: str,
    window: int,
    out_col: str,
    log_fn: Callable[[str], None] | None = None,
) -> None:
    """
    按股票分组计算滚动窗口最大回撤；优先 numba 分块写入，否则回退 rolling.apply。
    要求 df 已按 stock_code、date 排序，使每组行连续。
    """
    prices = df[price_col].to_numpy(dtype=np.float64, copy=False)
    out = np.full(len(df), np.nan, dtype=np.float64)
    sizes = df.groupby("stock_code", sort=False).size().to_numpy(dtype=np.int64)
    if _rolling_max_drawdown_numba is not None:
        start = 0
        for sz in sizes:
            sl = slice(start, start + int(sz))
            chunk = prices[sl].copy()
            local = np.empty(int(sz), dtype=np.float64)
            _rolling_max_drawdown_numba(chunk, int(window), local)
            out[sl] = local
            start += int(sz)
        df[out_col] = out
        return

    if log_fn:
        log_fn("[FCT] numba unavailable; max drawdown uses rolling.apply (slower).")
    grp = df.groupby("stock_code", sort=False)[price_col]
    df[out_col] = (
        grp.rolling(int(window), min_periods=int(window))
        .apply(_max_drawdown_magnitude, raw=True)
        .reset_index(level=0, drop=True)
    )


def _compute_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return rsi


def _compute_macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_diff = macd - macd_signal
    return macd_diff, macd, macd_signal


@dataclass(frozen=True)
class FactorSelectionResult:
    selected_factors: list[str]
    mean_abs_pair_corr: float
    max_abs_pair_corr: float


def _pairwise_corr_stats(df: pd.DataFrame, factor_cols: list[str]) -> tuple[float, float]:
    if not factor_cols:
        return 0.0, 0.0
    corr = df[factor_cols].corr()
    corr_abs = corr.abs()
    mask = ~np.eye(len(factor_cols), dtype=bool)
    off_vals = corr_abs.values[mask]
    return float(np.nanmean(off_vals)), float(np.nanmax(off_vals))


def _select_low_correlation_factors(df_z: pd.DataFrame, factor_cols: list[str]) -> FactorSelectionResult:
    """
    依据“平均相关性”剔除高相关因子，并尽量满足 15-20 个及相关性约束。
    """
    valid = [c for c in factor_cols if df_z[c].notna().any()]
    if len(valid) < 15:
        mean_corr, max_corr = _pairwise_corr_stats(df_z, valid)
        return FactorSelectionResult(valid, mean_corr, max_corr)

    corr = df_z[valid].corr()
    corr_abs = corr.abs()
    mean_abs: dict[str, float] = {}
    for c in valid:
        s = corr_abs[c].drop(labels=[c])
        mean_abs[c] = float(s.mean(skipna=True))

    thresholds = [0.7, 0.65, 0.6, 0.55, 0.5]
    best: FactorSelectionResult | None = None

    min_keep = 15
    max_keep = 20
    max_abs_pair_corr_thr = 0.7

    for thr in thresholds:
        keep = [c for c in valid if mean_abs[c] <= thr]
        keep = sorted(keep, key=lambda x: mean_abs[x])

        if len(keep) > max_keep:
            keep = keep[:max_keep]
        if len(keep) < min_keep:
            keep = sorted(valid, key=lambda x: mean_abs[x])[:min_keep]

        keep_refined = keep.copy()

        prev_max = float("inf")
        no_improve = 0
        for _ in range(200):
            mean_pair, max_pair = _pairwise_corr_stats(df_z, keep_refined)
            if max_pair <= max_abs_pair_corr_thr:
                break
            if max_pair >= prev_max - 1e-12:
                no_improve += 1
            else:
                no_improve = 0
                prev_max = max_pair
            if no_improve >= 15:
                break

            corr_abs = df_z[keep_refined].corr().abs()
            upper_mask = np.triu(np.ones_like(corr_abs.values, dtype=bool), k=1)
            high_pairs = corr_abs.where(upper_mask).stack()
            high_pairs = high_pairs[high_pairs > max_abs_pair_corr_thr]
            if high_pairs.empty:
                break

            involved = set()
            for (a, b) in high_pairs.index:
                involved.add(a)
                involved.add(b)

            subset_mean_abs = {c: float(corr_abs[c].drop(labels=[c]).mean(skipna=True)) for c in involved}
            remove_col = max(subset_mean_abs, key=lambda x: subset_mean_abs[x])

            if len(keep_refined) > min_keep:
                keep_refined = [c for c in keep_refined if c != remove_col]
                continue

            temp_keep = [c for c in keep_refined if c != remove_col]
            remaining = [c for c in valid if c not in temp_keep]
            if not remaining:
                break

            best_add: str | None = None
            best_max = float("inf")
            for cand in remaining:
                cand_keep = temp_keep + [cand]
                _, cand_max = _pairwise_corr_stats(df_z, cand_keep)
                if cand_max < best_max:
                    best_max = cand_max
                    best_add = cand

            if best_add is None:
                break

            keep_refined = temp_keep + [best_add]

        mean_pair, max_pair = _pairwise_corr_stats(df_z, keep_refined)
        candidate = FactorSelectionResult(keep_refined, mean_pair, max_pair)

        if best is None:
            best = candidate
        else:
            if candidate.max_abs_pair_corr < best.max_abs_pair_corr - 1e-9 or (
                abs(candidate.max_abs_pair_corr - best.max_abs_pair_corr) <= 1e-9
                and candidate.mean_abs_pair_corr < best.mean_abs_pair_corr
            ):
                best = candidate

        if candidate.mean_abs_pair_corr < 0.5 and candidate.max_abs_pair_corr <= max_abs_pair_corr_thr:
            return candidate

    return best  # type: ignore[return-value]


@profile_if_requested
def compute_factors(
    weekly_df: pd.DataFrame,
    *,
    output_path: Path = WEEKLY_FACTORS_OUT_PATH,
    min_factor_count: int = 15,
    max_factor_count: int = 20,
    selected_factor_cols: list[str] | None = None,
    industry_col: str | None = None,
    verbose_timing: bool | None = None,
) -> pd.DataFrame:
    """
    根据周频截面数据计算基础因子，并进行低相关性筛选。

    输入 weekly_df 期望至少包含：
    - date
    - stock_code
    - close（或“收盘”）
    - volume（可选但用于流动性）
    - turnover（可选用于流动性）

    verbose_timing: 为 True 或环境变量 QUANT_FACTOR_TIMING=1 时打印各阶段耗时。
    industry_col: 预留；非 None 时在 apply_cross_sectional_transforms 中触发 NotImplemented。
    """
    if weekly_df.empty:
        raise ValueError("weekly_df is empty.")

    if verbose_timing is None:
        verbose_timing = os.environ.get("QUANT_FACTOR_TIMING", "").strip() in ("1", "true", "yes")

    def _log(msg: str) -> None:
        if verbose_timing:
            print(msg, flush=True)

    _reset_timing()
    t_all = time.perf_counter()

    df = weekly_df.copy()
    date_col = _require_columns(df, ["date", "日期"])
    df["date"] = pd.to_datetime(df[date_col])
    df["stock_code"] = df[_require_columns(df, ["stock_code", "股票代码", "code"])].astype(str)

    close_col = _require_columns(df, ["close", "收盘"])
    volume_col = "volume" if "volume" in df.columns else ("成交量" if "成交量" in df.columns else None)
    turnover_col = "turnover" if "turnover" in df.columns else ("换手率" if "换手率" in df.columns else None)

    df = df.rename(columns={close_col: "close"})
    if volume_col is not None:
        df = df.rename(columns={volume_col: "volume"})
    if turnover_col is not None:
        df = df.rename(columns={turnover_col: "turnover"})

    df = df.sort_values(["stock_code", "date"]).reset_index(drop=True)
    _timed("prep_sort", _log if verbose_timing else None)

    g = df.groupby("stock_code", sort=False, group_keys=False)

    df["ret_wk"] = g["close"].pct_change()
    ret_lag = g["ret_wk"].shift(1)
    df["ret_lag"] = ret_lag

    close_lag = g["close"].shift(1)
    if "volume" in df.columns:
        df["volume_lag"] = g["volume"].shift(1)
    else:
        df["volume_lag"] = np.nan

    if "turnover" in df.columns:
        df["turnover_lag"] = g["turnover"].shift(1)
    else:
        df["turnover_lag"] = np.nan

    _timed("base_lags", _log if verbose_timing else None)

    gb = df.groupby("stock_code", sort=False)
    # 动量：∏(1+r)-1 = expm1(Σ log(1+r))；pandas RollingGroupby 无 prod，用向量化 rolling sum
    one_plus = 1.0 + df["ret_lag"]
    df["_log_one_plus_ret"] = np.where(np.isfinite(one_plus) & (one_plus > 0), np.log(one_plus), np.nan)
    for window, name in [(4, "mom_1m"), (12, "mom_3m"), (24, "mom_6m"), (8, "mom_2m"), (16, "mom_4m")]:
        rolled = gb["_log_one_plus_ret"].rolling(int(window), min_periods=int(window)).sum()
        df[name] = np.expm1(rolled.reset_index(level=0, drop=True))

    _timed("momentum", _log if verbose_timing else None)

    for window in [4, 8, 12]:
        df[f"volatility_{window}w"] = (
            gb["ret_lag"].rolling(int(window), min_periods=int(window)).std(ddof=0).reset_index(level=0, drop=True)
        )

    _timed("volatility", _log if verbose_timing else None)

    df["close_lag"] = close_lag
    for window in [4, 8]:
        _assign_rolling_max_drawdown(
            df,
            price_col="close_lag",
            window=int(window),
            out_col=f"max_retreat_{window}w",
            log_fn=_log if verbose_timing else None,
        )

    _timed("max_drawdown", _log if verbose_timing else None)

    if "volume_lag" in df.columns:
        for window in [4, 8]:
            df[f"avg_volume_{window}w"] = (
                gb["volume_lag"].rolling(int(window), min_periods=int(window)).mean().reset_index(level=0, drop=True)
            )

    for window in [4, 8]:
        df[f"turnover_avg_{window}w"] = (
            gb["turnover_lag"].rolling(int(window), min_periods=int(window)).mean().reset_index(level=0, drop=True)
        )

    _timed("liquidity", _log if verbose_timing else None)

    delta = gb["close"].diff()
    df["_rsi_gain"] = delta.clip(lower=0)
    df["_rsi_loss"] = (-delta).clip(lower=0)
    gb2 = df.groupby("stock_code", sort=False)
    for period in [7, 14, 21]:
        avg_gain = _drop_group_level_index(
            gb2["_rsi_gain"].ewm(alpha=1 / period, adjust=False).mean()
        )
        avg_loss = _drop_group_level_index(
            gb2["_rsi_loss"].ewm(alpha=1 / period, adjust=False).mean()
        )
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi_raw = 100 - 100 / (1 + rs)
        df[f"_rsi_raw_{period}"] = rsi_raw
        df[f"rsi_{period}"] = df.groupby("stock_code", sort=False)[f"_rsi_raw_{period}"].shift(1)

    _timed("rsi", _log if verbose_timing else None)

    ema_fast = _drop_group_level_index(gb2["close"].ewm(span=12, adjust=False).mean())
    ema_slow = _drop_group_level_index(gb2["close"].ewm(span=26, adjust=False).mean())
    df["_macd_level_raw"] = ema_fast.to_numpy() - ema_slow.to_numpy()
    macd_signal_raw = _drop_group_level_index(
        df.groupby("stock_code", sort=False)["_macd_level_raw"].ewm(span=9, adjust=False).mean()
    )
    df["_macd_signal_raw"] = macd_signal_raw
    df["_macd_diff_raw"] = df["_macd_level_raw"] - df["_macd_signal_raw"]

    gb3 = df.groupby("stock_code", sort=False)
    df["macd_diff"] = gb3["_macd_diff_raw"].shift(1)
    df["macd_level"] = gb3["_macd_level_raw"].shift(1)
    df["macd_signal"] = gb3["_macd_signal_raw"].shift(1)

    _timed("macd", _log if verbose_timing else None)

    for window in [4, 12]:
        ma = _drop_group_level_index(
            gb2["close_lag"].rolling(int(window), min_periods=int(window)).mean()
        )
        df[f"ma_ratio_{window}w"] = df["close_lag"] / ma - 1.0

    _timed("ma_ratio", _log if verbose_timing else None)

    if "pb" in df.columns:
        df["pb"] = gb3["pb"].shift(1)
    if "pe" in df.columns:
        df["pe"] = gb3["pe"].shift(1)

    factor_cols: list[str] = [
        "mom_1m",
        "mom_3m",
        "mom_6m",
        "mom_2m",
        "mom_4m",
        "volatility_4w",
        "volatility_8w",
        "volatility_12w",
        "max_retreat_4w",
        "max_retreat_8w",
        "avg_volume_4w",
        "avg_volume_8w",
        "turnover_avg_4w",
        "turnover_avg_8w",
        "rsi_7",
        "rsi_14",
        "rsi_21",
        "macd_diff",
        "macd_level",
        "macd_signal",
        "ma_ratio_4w",
        "ma_ratio_12w",
    ]
    if "pb" in df.columns:
        factor_cols.append("pb")
    if "pe" in df.columns:
        factor_cols.append("pe")

    factor_cols = [c for c in factor_cols if c in df.columns]

    df = apply_cross_sectional_transforms(df, factor_cols, industry_col=industry_col)
    df_z = _zscore_by_date(df, factor_cols)

    _timed("zscore", _log if verbose_timing else None)

    selected_cols: list[str]
    selection_stats: FactorSelectionResult | None = None
    if selected_factor_cols is not None:
        selected_cols = [c for c in selected_factor_cols if c in df_z.columns]
    else:
        selection_stats = _select_low_correlation_factors(df_z, factor_cols)
        selected_cols = selection_stats.selected_factors

    if selection_stats is not None:
        print(
            f"[FCT] selected={len(selected_cols)} mean_abs_pair_corr={selection_stats.mean_abs_pair_corr:.4f} "
            f"max_abs_pair_corr={selection_stats.max_abs_pair_corr:.4f}"
        )
    else:
        print(f"[FCT] selected={len(selected_cols)} (forced by training factor_columns.pkl)")

    out_df = df_z[["date", "stock_code", *selected_cols]].copy()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(output_path, index=False)

    _timed("selection_io", _log if verbose_timing else None)
    if verbose_timing:
        print(f"[FCT][timing] total: {time.perf_counter() - t_all:.3f}s", flush=True)

    return out_df
