"""
扩展因子计算脚本 - 60+因子体系
在现有15个因子基础上扩展至60+个低相关性因子

因子分类:
1. 动量类 (10): 多窗口累计收益率 + 动量加速度 + 动量反转
2. 波动率类 (8): 多窗口标准差 + 下行波动率 + 波动率变化率
3. 流动性类 (8): 均量/均换手 + 量变化率 + 换手变化率 + 成交额
4. 技术指标类 (12): RSI多窗口 + KDJ + Bollinger带宽 + 威廉指标 + CCI
5. 均线类 (8): 多窗口均线偏离 + 均线斜率 + EMA偏离
6. 回撤/风险类 (6): 最大回撤 + 偏度 + 峰度 + 收益率分位数
7. 量价关系类 (8): OBV变化 + 量价相关 + 成交额比 + 上涨天数占比
"""
from __future__ import annotations

import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

_BACKEND = str(Path(__file__).resolve().parent.parent)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

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


def compute_extended_factors(d: pd.DataFrame) -> pd.DataFrame:
    """为单只股票计算全部60+因子"""
    close = pd.to_numeric(d["close"], errors="coerce")
    high = pd.to_numeric(d.get("high", close), errors="coerce")
    low = pd.to_numeric(d.get("low", close), errors="coerce")
    open_ = pd.to_numeric(d.get("open", close), errors="coerce")
    volume = pd.to_numeric(d.get("volume", np.nan), errors="coerce")
    turnover = pd.to_numeric(d.get("turnover", np.nan), errors="coerce")
    amount = pd.to_numeric(d.get("amount", np.nan), errors="coerce")

    ret = close.pct_change()
    ret_lag = ret.shift(1)
    close_lag = close.shift(1)
    high_lag = high.shift(1)
    low_lag = low.shift(1)
    open_lag = open_.shift(1)
    vol_lag = volume.shift(1)
    turnover_lag = turnover.shift(1)
    amount_lag = amount.shift(1)

    out = pd.DataFrame({"date": d["date"], "stock_code": d["stock_code"].iloc[0]})

    # ============================================================
    # 1. 动量类因子 (10个)
    # ============================================================
    log_one_plus = np.log((1 + ret_lag).clip(lower=1e-10))
    for window, name in [(4, "mom_1m"), (8, "mom_2m"), (12, "mom_3m"),
                          (16, "mom_4m"), (24, "mom_6m"), (48, "mom_12m")]:
        out[name] = np.expm1(log_one_plus.rolling(window, min_periods=window).sum())

    out["mom_accel_1m"] = out["mom_1m"] - out["mom_1m"].shift(4)
    out["mom_reversal"] = out["mom_1m"] - out["mom_3m"]
    out["mom_short_long"] = out["mom_1m"] - out["mom_6m"]
    out["mom_1w"] = ret_lag

    # ============================================================
    # 2. 波动率类因子 (8个)
    # ============================================================
    for window in [4, 8, 12, 24]:
        out[f"volatility_{window}w"] = ret_lag.rolling(window, min_periods=window).std(ddof=0)

    neg_ret = ret_lag.clip(upper=0)
    out["downside_vol_8w"] = neg_ret.rolling(8, min_periods=4).std(ddof=0)
    out["vol_ratio_4_12"] = (
        out["volatility_4w"] / out["volatility_12w"].replace(0, np.nan)
    )
    out["vol_change_4w"] = out["volatility_4w"] - out["volatility_4w"].shift(4)
    out["realized_var_8w"] = (ret_lag ** 2).rolling(8, min_periods=4).sum()

    # ============================================================
    # 3. 流动性类因子 (8个)
    # ============================================================
    for window in [4, 8, 12]:
        out[f"avg_volume_{window}w"] = vol_lag.rolling(window, min_periods=window).mean()
        out[f"avg_turnover_{window}w"] = turnover_lag.rolling(window, min_periods=window).mean()

    out["volume_change_1w"] = vol_lag / vol_lag.shift(4).replace(0, np.nan) - 1
    out["turnover_change_1w"] = turnover_lag / turnover_lag.shift(4).replace(0, np.nan) - 1
    out["avg_amount_4w"] = amount_lag.rolling(4, min_periods=2).mean()

    # ============================================================
    # 4. 技术指标类因子 (12个)
    # ============================================================
    for period in [7, 14, 21]:
        out[f"rsi_{period}"] = _compute_rsi(close, period).shift(1)

    lowest_low = low.rolling(9, min_periods=9).min()
    highest_high = high.rolling(9, min_periods=9).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d_val = k.ewm(alpha=1/3, adjust=False).mean()
    j_val = 3 * k - 2 * d_val
    out["kdj_k"] = k.shift(1)
    out["kdj_d"] = d_val.shift(1)
    out["kdj_j"] = j_val.shift(1)

    ma20 = close.rolling(20, min_periods=10).mean()
    std20 = close.rolling(20, min_periods=10).std(ddof=0)
    out["boll_width"] = (2 * std20 / ma20.replace(0, np.nan)).shift(1)
    out["boll_pct"] = ((close - ma20 + std20) / (2 * std20).replace(0, np.nan)).shift(1)

    hh_14 = high.rolling(14, min_periods=7).max()
    ll_14 = low.rolling(14, min_periods=7).min()
    out["willr_14"] = ((hh_14 - close) / (hh_14 - ll_14).replace(0, np.nan) * -100).shift(1)

    tp = (high + low + close) / 3
    ma_tp = tp.rolling(14, min_periods=7).mean()
    md_tp = (tp - ma_tp).abs().rolling(14, min_periods=7).mean()
    out["cci_14"] = ((tp - ma_tp) / (0.015 * md_tp).replace(0, np.nan)).shift(1)

    # ============================================================
    # 5. 均线类因子 (8个)
    # ============================================================
    for window in [4, 8, 12, 24]:
        ma = close_lag.rolling(window, min_periods=window).mean()
        out[f"ma_ratio_{window}w"] = close_lag / ma.replace(0, np.nan) - 1

    for window, name in [(4, "ma_slope_4w"), (12, "ma_slope_12w"), (24, "ma_slope_24w")]:
        ma = close.rolling(window, min_periods=window).mean()
        out[name] = (ma / ma.shift(window).replace(0, np.nan) - 1).shift(1)

    ema12 = close.ewm(span=12, adjust=False).mean()
    out["ema_ratio_12"] = (close / ema12 - 1).shift(1)

    # ============================================================
    # 6. 回撤/风险类因子 (6个)
    # ============================================================
    for window in [4, 8, 12]:
        out[f"max_retreat_{window}w"] = close_lag.rolling(window, min_periods=window).apply(
            _max_drawdown, raw=True
        )

    out["skewness_8w"] = ret_lag.rolling(8, min_periods=4).skew()
    out["kurtosis_12w"] = ret_lag.rolling(12, min_periods=6).kurt()
    out["ret_quantile_25_8w"] = ret_lag.rolling(8, min_periods=4).quantile(0.25)

    # ============================================================
    # 7. 量价关系类因子 (8个)
    # ============================================================
    obv = (volume * np.sign(close.diff())).cumsum()
    obv_lag = obv.shift(1)
    out["obv_change_4w"] = obv_lag / obv_lag.shift(4).replace(0, np.nan) - 1

    vol_change = volume.pct_change().shift(1)
    price_up = (close.diff() > 0).astype(float).shift(1)
    cov_vp = (vol_change * ret_lag).rolling(8, min_periods=4).mean()
    out["vol_price_corr_8w"] = cov_vp

    out["up_ratio_4w"] = price_up.rolling(4, min_periods=2).mean()
    out["up_ratio_12w"] = price_up.rolling(12, min_periods=6).mean()

    out["high_low_range_4w"] = ((high_lag - low_lag) / close_lag.replace(0, np.nan)).rolling(4, min_periods=2).mean()
    out["open_close_ratio_4w"] = ((close_lag - open_lag) / close_lag.replace(0, np.nan)).rolling(4, min_periods=2).mean()

    avg_vol_up = volume[close.diff() > 0].reindex(close.index).shift(1).rolling(8, min_periods=2).mean()
    avg_vol_down = volume[close.diff() <= 0].reindex(close.index).shift(1).rolling(8, min_periods=2).mean()
    out["vol_up_down_ratio"] = avg_vol_up / avg_vol_down.replace(0, np.nan)

    return out


def main() -> None:
    weekly_base_path = DATA_DIR / "weekly_base_real.parquet"
    weekly_factors_path = DATA_DIR / "weekly_factors.parquet"
    weekly_model_input_path = DATA_DIR / "weekly_model_input.parquet"

    if not weekly_base_path.exists():
        raise FileNotFoundError(f"Missing {weekly_base_path}. Run weekly base build first.")

    print("加载周频基础数据...")
    base = pd.read_parquet(weekly_base_path)
    base["date"] = pd.to_datetime(base["date"])
    base["stock_code"] = base["stock_code"].astype(str)
    base = base.sort_values(["stock_code", "date"]).reset_index(drop=True)
    print(f"  数据量: {len(base):,} 行, {base['stock_code'].nunique()} 只股票")

    print("\n计算60+因子（逐股票低内存模式）...")
    t0 = time.time()
    factors_all: list[pd.DataFrame] = []
    for code, gdf in tqdm(base.groupby("stock_code", sort=False), desc="计算因子"):
        d = gdf.copy()
        d = d.sort_values("date").reset_index(drop=True)
        try:
            result = compute_extended_factors(d)
            factors_all.append(result)
        except Exception as e:
            print(f"  股票 {code} 因子计算失败: {e}")
            continue

    factors = pd.concat(factors_all, ignore_index=True)
    factor_cols = [c for c in factors.columns if c not in {"date", "stock_code"}]
    print(f"  因子计算完成，共 {len(factor_cols)} 个因子，耗时 {time.time()-t0:.1f}s")

    print("\n截面Z-score标准化...")
    factors = _zscore_by_date(factors, factor_cols=factor_cols)

    print("\n计算因子相关性统计...")
    sample = factors[factors["date"] == factors["date"].median()].copy()
    if len(sample) > 0:
        corr_matrix = sample[factor_cols].corr().abs()
        mask = ~np.eye(len(factor_cols), dtype=bool)
        off_vals = corr_matrix.values[mask]
        mean_corr = float(np.nanmean(off_vals))
        max_corr = float(np.nanmax(off_vals))
        print(f"  平均绝对相关系数: {mean_corr:.4f}")
        print(f"  最大绝对相关系数: {max_corr:.4f}")

        high_pairs = []
        for i in range(len(factor_cols)):
            for j in range(i + 1, len(factor_cols)):
                if abs(corr_matrix.iloc[i, j]) > 0.7:
                    high_pairs.append((factor_cols[i], factor_cols[j], corr_matrix.iloc[i, j]))
        if high_pairs:
            high_pairs.sort(key=lambda x: -x[2])
            print(f"  高相关因子对(>0.7): {len(high_pairs)} 对")
            for a, b, c in high_pairs[:10]:
                print(f"    {a} vs {b}: {c:.4f}")

    factors.to_parquet(weekly_factors_path, index=False)
    print(f"\n因子数据已保存: {weekly_factors_path} shape={factors.shape}")

    print("\n合并因子与价格数据...")
    model_input = base[["date", "stock_code", "close"]].merge(factors, on=["date", "stock_code"], how="inner")
    model_input = model_input.sort_values(["stock_code", "date"]).reset_index(drop=True)
    model_input.to_parquet(weekly_model_input_path, index=False)
    print(f"模型输入数据已保存: {weekly_model_input_path} shape={model_input.shape}")

    print("\n生成排序学习数据集...")
    out = generate_query_datasets(
        model_input,
        output_dir=DATA_DIR,
        train_end="2020-12-31",
        val_end="2022-12-31",
        forward_weeks=1,
    )
    print(f"数据集生成完成: {out}")

    with open(DATA_DIR / "factor_columns.pkl", "wb") as f:
        pickle.dump(factor_cols, f)
    print(f"因子列名已保存: factor_columns.pkl ({len(factor_cols)} 个因子)")

    print("\n" + "=" * 60)
    print("因子体系构建完成!")
    print(f"总因子数: {len(factor_cols)}")
    print(f"因子列表: {factor_cols}")
    print("=" * 60)


if __name__ == "__main__":
    main()
