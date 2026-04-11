"""
回测与排序评估常用指标：年化收益、夏普、最大回撤、换手率、胜率、NDCG@K 及汇总字典（可 JSON）。

净值序列假定按交易日（或等间隔）索引；缺失值向前填充后再计算。
"""
from __future__ import annotations

import json
import logging
import math
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TradingDaysPerYear = 252


def _finite_or_none(x: float) -> float | None:
    if x is None or not math.isfinite(x):
        return None
    return float(x)


def weekly_nav_to_daily_business_ffill(nav_series: pd.Series) -> pd.Series:
    """
    周频调仓净值序列 → 区间内所有工作日逐日前向填充，便于按 252 交易日假设计算年化与夏普。
    """
    s = nav_series.sort_index()
    if s.empty:
        return s
    idx = pd.date_range(s.index.min(), s.index.max(), freq="B")
    out = s.reindex(idx).ffill()
    return out.astype(np.float64)


def _prepare_nav_series(nav_series: pd.Series | np.ndarray | list[float]) -> pd.Series:
    """
    转为单调升序 DatetimeIndex（若可解析），数值 forward-fill，剔除前导缺失；
    剔除非正净值（无法取对数）。
    """
    s = pd.Series(nav_series, copy=True)
    if not isinstance(s.index, pd.DatetimeIndex):
        parsed = pd.to_datetime(s.index, errors="coerce")
        if not bool(parsed.isna().all()):
            s.index = parsed
            s = s.loc[~s.index.isna()]
    s = s.sort_index()
    s = pd.to_numeric(s, errors="coerce")
    s = s.ffill()
    s = s[s.first_valid_index() :] if s.first_valid_index() is not None else s
    s = s[s > 0]
    return s.astype(np.float64)


def annualized_return(
    nav_series: pd.Series | np.ndarray | list[float],
    *,
    trading_days_per_year: int = TradingDaysPerYear,
) -> float:
    """
    按总净值变化与样本内「交易日」跨度年化：((NAV_end/NAV_start)^(252/T) - 1)，
    T 为相邻观测间隔数（len-1），与 252 个交易日/年假设一致。
    """
    nav = _prepare_nav_series(nav_series)
    if len(nav) < 2:
        return float("nan")
    r_total = float(nav.iloc[-1] / nav.iloc[0])
    if r_total <= 0:
        return float("nan")
    n_periods = len(nav) - 1
    if n_periods <= 0:
        return float("nan")
    exp = trading_days_per_year / float(n_periods)
    return float(r_total**exp - 1.0)


def sharpe_ratio(
    nav_series: pd.Series | np.ndarray | list[float],
    risk_free_rate: float = 0.03,
    *,
    trading_days_per_year: int = TradingDaysPerYear,
) -> float:
    """
    基于对数收益率的夏普：日对数超额收益均值 / 日对数收益标准差 * sqrt(252)。
    无风险利率为年化简单利率 risk_free_rate（如 0.03），折算为日对数无风险近似
    log(1+r_f)/252，与对数收益可比。
    """
    nav = _prepare_nav_series(nav_series)
    if len(nav) < 3:
        return float("nan")
    lr = np.log(nav / nav.shift(1)).dropna()
    if len(lr) < 2:
        return float("nan")
    daily_rf_log = float(np.log1p(risk_free_rate) / float(trading_days_per_year))
    excess = lr - daily_rf_log
    mu = float(excess.mean())
    sig = float(excess.std(ddof=1))
    if sig <= 0 or np.isnan(sig):
        return float("nan")
    return (mu / sig) * np.sqrt(float(trading_days_per_year))


def max_drawdown(
    nav_series: pd.Series | np.ndarray | list[float],
) -> dict[str, Any]:
    """
    最大回撤（正数比例，如 0.25 表示从峰值到谷底跌 25%）及峰值日、谷底日。

    谷底日：净值相对历史最高点比值最小的时点；峰值日：该谷底之前（含）最后一次
    达到「该历史最高水位」的日期（即本轮回撤的起涨高点）。
    """
    nav = _prepare_nav_series(nav_series)
    if len(nav) < 2:
        return {
            "max_drawdown": float("nan"),
            "peak_date": None,
            "trough_date": None,
        }

    cummax = nav.cummax()
    dd_ratio = nav / cummax - 1.0
    trough_pos = int(np.argmin(dd_ratio.to_numpy()))
    trough_date = nav.index[trough_pos]
    peak_level = float(cummax.iloc[trough_pos])

    window = nav.iloc[: trough_pos + 1].to_numpy(dtype=np.float64)
    tol = max(1e-12, abs(peak_level) * 1e-9)
    match_idx = np.where(np.abs(window - peak_level) <= tol)[0]
    peak_pos = int(match_idx[-1]) if match_idx.size else 0
    peak_date = nav.index[peak_pos]

    mdd = float(-dd_ratio.iloc[trough_pos])
    if mdd < 0:
        mdd = 0.0

    def _iso(ts: pd.Timestamp) -> str:
        if hasattr(ts, "date"):
            return ts.date().isoformat()
        return str(ts)

    return {
        "max_drawdown": mdd,
        "peak_date": _iso(pd.Timestamp(peak_date)),
        "trough_date": _iso(pd.Timestamp(trough_date)),
    }


def turnover_rate(trades_df: pd.DataFrame) -> float:
    """
    平均换手率：每周（每个调仓日）(买入成交额 + 卖出成交额) / 当日总资产，再对调仓日简单平均。

    支持两种列布局（二选一）：
    1) 聚合行：`date`, `buy_amount`, `sell_amount`, `total_value`（金额均为正数）。
    2) 逐笔行：`date`, `side`（'buy'/'sell'）, `gross_amount`（正数）, `total_value`（同日内相同）。
    """
    if trades_df is None or trades_df.empty:
        return float("nan")

    df = trades_df.copy()
    if "date" not in df.columns:
        raise KeyError("trades_df 需包含 date 列")

    df["date"] = pd.to_datetime(df["date"])

    if {"buy_amount", "sell_amount", "total_value"}.issubset(df.columns):
        g = df.groupby("date", sort=True).first()
        num = (g["buy_amount"].astype(float) + g["sell_amount"].astype(float)).to_numpy()
        den = g["total_value"].astype(float).to_numpy()
    elif {"side", "gross_amount", "total_value"}.issubset(df.columns):
        side = df["side"].astype(str).str.lower()
        buy_m = (side == "buy") * df["gross_amount"].astype(float)
        sell_m = (side == "sell") * df["gross_amount"].astype(float)
        agg = df.assign(_buy=buy_m, _sell=sell_m).groupby("date", sort=True).agg(
            buy_amount=("_buy", "sum"),
            sell_amount=("_sell", "sum"),
            total_value=("total_value", "first"),
        )
        num = (agg["buy_amount"] + agg["sell_amount"]).to_numpy(dtype=float)
        den = agg["total_value"].to_numpy(dtype=float)
    else:
        raise KeyError(
            "trades_df 需为 (date,buy_amount,sell_amount,total_value) "
            "或 (date,side,gross_amount,total_value)",
        )

    den = np.where(den <= 0, np.nan, den)
    ratios = num / den
    ratios = ratios[~np.isnan(ratios)]
    if ratios.size == 0:
        return float("nan")
    return float(np.mean(ratios))


def win_rate(trades_df: pd.DataFrame) -> float:
    """
    盈利占比（两种口径，按优先级）：

    1. 存在列 `pnl`（单笔或合并后的已实现盈亏）且至少有一个非空值时：
       盈利次数 / 有效样本数，即 (pnl > 0).mean()。
    2. 否则若存在 `date` 与 `total_value`（与 `build_rebalance_turnover_trades` 输出一致）：
       按调仓日排序，对组合总市值做逐期收益率，统计收益为正的时期占比
       （与回测中 `weekly_portfolio_win_rate` 口径一致）。
    """
    if trades_df is None or trades_df.empty:
        return float("nan")

    if "pnl" in trades_df.columns:
        pnl = pd.to_numeric(trades_df["pnl"], errors="coerce").dropna()
        if not pnl.empty:
            return float((pnl > 0).mean())

    if "date" not in trades_df.columns or "total_value" not in trades_df.columns:
        return float("nan")

    df = trades_df.sort_values("date")
    tv = (
        df.groupby("date", sort=True)["total_value"]
        .first()
        .pipe(pd.to_numeric, errors="coerce")
        .astype(float)
        .dropna()
    )
    if len(tv) < 2:
        return float("nan")
    r = tv.pct_change().dropna()
    if r.empty:
        return float("nan")
    return float((r > 0).mean())


def _dcg_from_relevance_sorted(rels_sorted_high_first: np.ndarray, k: int) -> float:
    """与 model_evaluation 一致：gain=2^rel-1，折扣 log2(i+1)，i 从 1 开始。"""
    rels = np.asarray(rels_sorted_high_first, dtype=np.float64)[:k]
    if rels.size == 0:
        return 0.0
    gains = np.power(2.0, rels) - 1.0
    discounts = np.log2(np.arange(2, rels.size + 2, dtype=np.float64))
    return float(np.sum(gains / discounts))


def _rank_order_desc(score: np.ndarray) -> np.ndarray:
    s = np.asarray(score, dtype=np.float64)
    n = s.size
    return np.lexsort((np.arange(n, dtype=np.int64), -s))


def ndcg_at_k(y_true: np.ndarray | list[float], y_score: np.ndarray | list[float], k: int) -> float:
    """
    单 query 的 NDCG@K；`y_true` 为相关性等级（非负，与训练侧 relevance 一致时可直接用），
    `y_score` 为模型打分（越大越靠前）。
    """
    rel = np.asarray(y_true, dtype=np.float64).ravel()
    score = np.asarray(y_score, dtype=np.float64).ravel()
    if rel.shape != score.shape or rel.size == 0:
        return 0.0
    kk = min(int(k), rel.size)
    if kk <= 0:
        return 0.0

    order = _rank_order_desc(score)
    sorted_rel = rel[order]
    ideal_order = _rank_order_desc(rel)
    ideal_rel = rel[ideal_order]
    dcg = _dcg_from_relevance_sorted(sorted_rel, kk)
    idcg = _dcg_from_relevance_sorted(ideal_rel, kk)
    if idcg <= 0:
        return 0.0
    return float(dcg / idcg)


def aggregate_metrics(
    nav_series: pd.Series | np.ndarray | list[float],
    *,
    risk_free_rate: float = 0.03,
    trades_df: pd.DataFrame | None = None,
    y_true_ndcg: np.ndarray | list[float] | None = None,
    y_score_ndcg: np.ndarray | list[float] | None = None,
    ndcg_k: int = 10,
    trading_days_per_year: int = TradingDaysPerYear,
) -> dict[str, Any]:
    """
    汇总指标为 JSON 可序列化字典（日期为 ISO 字符串，无 numpy 标量残留）。
    """
    ar = annualized_return(nav_series, trading_days_per_year=trading_days_per_year)
    sr = sharpe_ratio(nav_series, risk_free_rate, trading_days_per_year=trading_days_per_year)
    out: dict[str, Any] = {
        "annualized_return": _finite_or_none(ar),
        "sharpe_ratio": _finite_or_none(sr),
    }
    dd = max_drawdown(nav_series)
    mdd = dd["max_drawdown"]
    out["max_drawdown"] = _finite_or_none(float(mdd)) if isinstance(mdd, (int, float, np.floating)) else None
    out["drawdown_peak_date"] = dd["peak_date"]
    out["drawdown_trough_date"] = dd["trough_date"]

    if trades_df is not None and not trades_df.empty:
        out["turnover_rate"] = _finite_or_none(turnover_rate(trades_df))
        out["win_rate"] = _finite_or_none(win_rate(trades_df))
    else:
        out["turnover_rate"] = None
        out["win_rate"] = None

    nk = int(ndcg_k)
    if y_true_ndcg is not None and y_score_ndcg is not None:
        out[f"ndcg_at_{nk}"] = float(ndcg_at_k(y_true_ndcg, y_score_ndcg, nk))
    else:
        out[f"ndcg_at_{nk}"] = None

    return json.loads(json.dumps(out, ensure_ascii=False, default=str))


def metrics_to_json(metrics: dict[str, Any]) -> str:
    """字典转 JSON 字符串（ensure_ascii=False）。"""
    return json.dumps(metrics, ensure_ascii=False, indent=2, default=str)


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    idx = pd.date_range("2024-01-02", periods=252, freq="B")
    rng = np.random.default_rng(0)
    nav = pd.Series(100 * np.cumprod(1 + rng.normal(0.0005, 0.01, size=len(idx))), index=idx)
    nav.iloc[50:55] = np.nan
    m = aggregate_metrics(
        nav,
        trades_df=pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-02-01", "2024-02-01", "2024-03-01"]),
                "side": ["buy", "sell", "buy"],
                "gross_amount": [50_000.0, 20_000.0, 30_000.0],
                "total_value": [1_000_000.0, 1_000_000.0, 1_050_000.0],
            }
        ),
        y_true_ndcg=[3, 2, 1, 0],
        y_score_ndcg=[0.9, 0.7, 0.5, 0.1],
        ndcg_k=3,
    )
    print(metrics_to_json(m))


if __name__ == "__main__":
    _main()
