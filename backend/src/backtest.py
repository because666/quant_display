"""
周频滚动回测引擎：固定加载已训练模型，按周五截面调仓，显式交易成本与涨跌停约束。

用法::

    python -m src.backtest              # 快速打印测试集回测首尾
    python -m src.backtest --run        # 跑双模型、写 SQLite、导出 data/backtest_results/*.json
    python -m src.backtest --compare    # 双模型对比：comparison.json、comparison_nav.json、可选 Plotly 报告
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

try:
    from tqdm import tqdm as _tqdm_bar
except ImportError:

    def _tqdm_bar(iterable, **_kw):  # type: ignore[no-untyped-def]
        return iterable


from .config import get_settings
from .data_loader import DATA_OUT_DIR, add_future_return, split_by_time
from .db import init_db, session_scope
from .db.models import BacktestResult
from .metrics import aggregate_metrics, metrics_to_json, weekly_nav_to_daily_business_ffill
from .predictor import ModelKind, ModelPredictor

logger = logging.getLogger(__name__)


def _score_panel_with_fallback(
    pred: Any,
    panel_df: pd.DataFrame,
) -> tuple[dict[pd.Timestamp, pd.DataFrame], set[pd.Timestamp]]:
    """
    优先整表 predict_panel；失败则按调仓周逐次 predict。
    返回 {date -> 该日 score 表}，以及预测失败需跳过调仓的日期集合。
    """
    failed: set[pd.Timestamp] = set()
    if panel_df.empty:
        return {}, failed

    scored_full: pd.DataFrame | None = None
    try:
        if hasattr(pred, "predict_panel"):
            scored_full = pred.predict_panel(panel_df)
    except Exception as exc:
        logger.warning("批量预测失败，按调仓周拆分重试: %s", exc)
        scored_full = None

    if scored_full is None:
        parts: list[pd.DataFrame] = []
        for dt, g in panel_df.groupby("date", sort=True):
            try:
                fac = g[["stock_code"] + [c for c in pred._factor_cols if c in g.columns]]
                if fac.empty:
                    failed.add(pd.Timestamp(dt))
                    continue
                sc = pred.predict(fac)
                parts.append(
                    pd.DataFrame(
                        {
                            "date": pd.Timestamp(dt),
                            "stock_code": sc["stock_code"].astype(str).to_numpy(),
                            "score": sc["score"].to_numpy(dtype=np.float64),
                        }
                    )
                )
            except Exception as exc2:
                logger.warning("调仓日 %s 预测失败，跳过本周调仓（保持持仓）: %s", dt, exc2)
                failed.add(pd.Timestamp(dt))
        scored_full = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["date", "stock_code", "score"])

    by_date: dict[pd.Timestamp, pd.DataFrame] = {}
    if not scored_full.empty:
        for d, g in scored_full.groupby("date", sort=False):
            ts = pd.Timestamp(d)
            sub = g[["stock_code", "score"]].copy()
            if sub["score"].isna().all():
                failed.add(ts)
                continue
            by_date[ts] = sub
    return by_date, failed


def _select_target_codes(
    day_scores: pd.DataFrame,
    px: pd.DataFrame,
    top_n: int,
) -> list[str]:
    """向量化合并涨跌停掩码后取 score Top N（可买）。"""
    if day_scores.empty:
        return []
    pxr = px.reset_index()
    merged = day_scores.merge(
        pxr[["stock_code", "buy_blocked_limit_up"]],
        on="stock_code",
        how="inner",
    )
    merged = merged.loc[~merged["buy_blocked_limit_up"]]
    merged = merged.sort_values("score", ascending=False, kind="mergesort")
    return merged["stock_code"].astype(str).head(top_n).tolist()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKTEST_RESULTS_DIR = PROJECT_ROOT / "data" / "backtest_results"
REPORTS_DIR = PROJECT_ROOT / "reports"

# 普通主板涨跌幅简化：10%（科创板/创业板 20% 未区分，与任务说明一致）
LIMIT_UP_MULT = 1.10
LIMIT_DOWN_MULT = 0.90


class BacktestEngine:
    """
    周频回测：每周五（数据中的 date 截面）用当期因子与固定模型打分，持有至下一调仓日。

    交易规则（均在代码中显式实现，便于审计与复现）：
    - T+1：A 股当日买入不可当日卖出；本引擎调仓周期为周，卖出发生在下一调仓周，
      与「买入周」不同，故不存在日内回转，任务要求下可忽略日内 T+1。
    - 佣金 commission：买卖双边按成交额的比率从现金扣除（默认万三 0.0003）。
    - 滑点 slippage：买入成交价=收盘价*(1+slippage)，卖出=收盘价*(1-slippage)（双边默认 0.1%）。
    - 印花税 stamp_tax：仅卖出侧，按卖出成交额比率（默认万五 0.0005），在佣金之外扣除。
    - 涨跌停：涨停价=前一周收盘价*LIMIT_UP_MULT，跌停价=前一周收盘价*LIMIT_DOWN_MULT；
      涨停时视为无法买入；跌停时视为无法卖出。价格序列无日线时，用周收盘价与前一周收盘价比较。
    - 空仓：目标 Top N 全部因涨停无法买入，或剩余现金不足以按规则成交任何一笔加仓时，
      保留现金；若已有持仓则仍按可卖尽卖、可买尽买处理。
    """

    def __init__(
        self,
        model_type: ModelKind,
        top_n: int,
        initial_capital: float = 1_000_000.0,
        commission: float = 0.0003,
        slippage: float = 0.001,
        stamp_tax: float = 0.0005,
        *,
        data_dir: Path | None = None,
    ) -> None:
        if top_n < 1:
            raise ValueError("top_n 至少为 1")
        if initial_capital <= 0:
            raise ValueError("initial_capital 必须为正")
        self.model_type: ModelKind = model_type
        self.top_n = top_n
        self.initial_capital = float(initial_capital)
        self.commission = float(commission)
        self.slippage = float(slippage)
        self.stamp_tax = float(stamp_tax)
        s = get_settings()
        self._data_dir = (
            Path(data_dir)
            if data_dir is not None
            else (Path(s.quant_data_dir) if s.quant_data_dir.strip() else DATA_OUT_DIR)
        )

    def _buy_cash_per_share(self, close: float) -> float:
        """买入 1 股所需现金：含滑点后的单价 * (1+佣金)。"""
        unit = float(close) * (1.0 + self.slippage)
        return unit * (1.0 + self.commission)

    def _cash_from_sell(self, shares: float, close: float) -> float:
        """卖出 shares 后入账现金：含滑点、佣金、印花税。"""
        if shares <= 0:
            return 0.0
        unit = float(close) * (1.0 - self.slippage)
        gross = float(shares) * unit
        return gross * (1.0 - self.commission - self.stamp_tax)

    def load_weekly_data(
        self,
        path: Path | None = None,
        *,
        concat_splits: bool = True,
    ) -> pd.DataFrame:
        """
        加载周频截面：日期、股票代码、因子、未来一周收益率等；按时间升序排列。

        - 若提供 path：读取该 parquet（需含 date、stock_code；若有 close 则直接使用，否则需有
          future_return_1w 以便递推合成收盘价）。
        - 否则 concat_splits=True 时合并 data_dir 下 train/val/test.parquet（与任务 2 落盘一致）。
        """
        if path is not None:
            pp = Path(path)
            with pp.open("rb") as fp:
                raw = pd.read_parquet(fp)
        elif concat_splits:
            parts: list[pd.DataFrame] = []
            for name in ("train", "val", "test"):
                p = self._data_dir / f"{name}.parquet"
                if not p.exists():
                    raise FileNotFoundError(str(p))
                with p.open("rb") as fp:
                    parts.append(pd.read_parquet(fp))
            raw = pd.concat(parts, ignore_index=True)
        else:
            raise ValueError("path 为 None 时需要 concat_splits=True")

        date_col = "date" if "date" in raw.columns else "日期"
        code_col = "stock_code" if "stock_code" in raw.columns else "股票代码"
        if date_col not in raw.columns or code_col not in raw.columns:
            raise KeyError("周频数据需包含 date 与 stock_code（或中文列名）")

        out = raw.copy()
        out["date"] = pd.to_datetime(out[date_col])
        out["stock_code"] = out[code_col].astype(str)
        out = out.sort_values(["date", "stock_code"]).reset_index(drop=True)

        if "future_return_1w" not in out.columns:
            close_src = "close" if "close" in out.columns else ("收盘" if "收盘" in out.columns else None)
            if close_src is None:
                raise KeyError("缺少 future_return_1w，且无法从收盘价构造标签")
            tmp = out.rename(columns={close_src: "close"}).copy()
            out = add_future_return(tmp, forward_weeks=1)

        if "close" not in out.columns and "收盘" not in out.columns:
            out["close"] = _synthetic_close_from_weekly_returns(out)
        else:
            ccol = "close" if "close" in out.columns else "收盘"
            out["close"] = pd.to_numeric(out[ccol], errors="coerce")

        # 向量化：前收、涨跌停参考价（按股票时间 shift）
        out = out.sort_values(["stock_code", "date"])
        out["prev_close"] = out.groupby("stock_code", sort=False)["close"].shift(1)
        out["limit_up_price"] = out["prev_close"] * LIMIT_UP_MULT
        out["limit_down_price"] = out["prev_close"] * LIMIT_DOWN_MULT
        tol = 1e-9
        pc = out["prev_close"]
        out["buy_blocked_limit_up"] = pc.notna() & (out["close"] >= out["limit_up_price"] - tol)
        out["sell_blocked_limit_down"] = pc.notna() & (out["close"] <= out["limit_down_price"] + tol)

        out = out.sort_values(["date", "stock_code"]).reset_index(drop=True)
        return out

    def run_backtest(
        self,
        weekly_df: pd.DataFrame | None = None,
        *,
        predictor: ModelPredictor | None = None,
        use_split: Literal["test", "all"] = "test",
        train_end: str = "2020-12-31",
        val_end: str = "2022-12-31",
        skip_initial_weeks: int = 0,
    ) -> pd.DataFrame:
        """
        主回测流程：每周五截面打分、卖出非目标、再买入目标，记录调仓日净值。

        时点说明（避免未来信息）：date=t 行的因子与收盘价视为周五 t 收盘可知；模型得分用于
        决定从 t 收盘起持有至下一调仓周。标签 future_return_1w 仅用于数据管道，回测下单不使用。

        返回列：date, total_value, cash, holdings（JSON 字符串，股票代码 -> 持仓股数）。

        skip_initial_weeks：在选定样本内跳过前若干调仓周，用于因子滚动窗口尚未就绪、或
        与训练集尾部隔离等场景；默认 0 表示从该样本第一个截面开始回测。

        说明：数据为周频时，每行对应一次调仓日（通常为周五）收盘后的持仓与现金快照；
        非自然日逐日净值；若需日度曲线需接入日频行情并扩展估值循环。流程无随机步骤，可复现。

        性能：整段样本先 ``predict_panel`` 批量打分（模型固定、无未来信息），再逐周撮合；
        批量失败时自动按周 ``predict`` 回退。某周预测失败或截面缺列时跳过调仓、保持持仓。
        进度条依赖 tqdm（未安装则静默遍历）。
        """
        if weekly_df is None:
            weekly_df = self.load_weekly_data()

        df = weekly_df.copy()
        if use_split == "test":
            _, _, test_part = split_by_time(df, train_end=train_end, val_end=val_end)
            if test_part.empty:
                raise ValueError("测试集为空，请检查 train_end/val_end 或数据区间")
            df = test_part.sort_values(["date", "stock_code"]).reset_index(drop=True)

        pred = predictor or ModelPredictor(self.model_type, data_dir=self._data_dir)
        factor_cols = pred._factor_cols

        dates = sorted(df["date"].unique())
        if skip_initial_weeks < 0:
            raise ValueError("skip_initial_weeks 不能为负")
        if skip_initial_weeks:
            dates = dates[int(skip_initial_weeks) :]
        if not dates:
            raise ValueError("skip_initial_weeks 过大或样本无调仓日")
        dates_ts = [pd.Timestamp(d) for d in dates]

        # 按日期索引截面，避免每周全表过滤
        date_to_day: dict[pd.Timestamp, pd.DataFrame] = {
            pd.Timestamp(d): g for d, g in df.groupby("date", sort=False)
        }

        # 批预测：整段样本一次推理（模型固定），失败则按周回退；无未来信息（每行仅用当期因子）
        factor_in_df = [c for c in factor_cols if c in df.columns]
        panel_cols = ["date", "stock_code", *factor_in_df]
        panel_parts: list[pd.DataFrame] = []
        for dt in dates_ts:
            g = date_to_day.get(dt)
            if g is None or g.empty:
                continue
            panel_parts.append(g[panel_cols].copy())
        panel_df = pd.concat(panel_parts, ignore_index=True) if panel_parts else pd.DataFrame(columns=["date", "stock_code"])
        scored_by_date, failed_dates = _score_panel_with_fallback(pred, panel_df)
        del panel_df

        cash = self.initial_capital
        positions: dict[str, float] = {}
        rows: list[dict[str, object]] = []

        for dt in _tqdm_bar(dates_ts, desc="回测", unit="周"):
            day = date_to_day.get(dt)
            if day is None or day.empty:
                continue

            px = day.set_index("stock_code")
            required = ["close", "buy_blocked_limit_up", "sell_blocked_limit_down"]
            missing = [c for c in required if c not in px.columns]
            if missing:
                logger.warning("截面 %s 缺少列 %s，跳过本周调仓", dt, missing)

            for code in list(positions.keys()):
                if code not in px.index:
                    del positions[code]

            skip_trade = bool(missing) or dt in failed_dates or dt not in scored_by_date
            if skip_trade:
                m2m = _portfolio_market_value(positions, px["close"])
                total = cash + m2m
                rows.append(
                    {
                        "date": dt,
                        "total_value": float(total),
                        "cash": float(cash),
                        "holdings": _holdings_json(positions),
                    }
                )
                continue

            day_scores = scored_by_date[dt]
            target = _select_target_codes(day_scores, px, self.top_n)

            for code in list(positions.keys()):
                if code in target:
                    continue
                if code not in px.index:
                    continue
                if bool(px.loc[code, "sell_blocked_limit_down"]):
                    continue
                sh = float(positions.pop(code))
                cl = float(px.loc[code, "close"])
                cash += self._cash_from_sell(sh, cl)

            m2m = _portfolio_market_value(positions, px["close"])
            equity = cash + m2m

            if not target:
                rows.append(
                    {
                        "date": dt,
                        "total_value": float(equity),
                        "cash": cash,
                        "holdings": _holdings_json(positions),
                    }
                )
                continue

            stuck_val = _stuck_non_target_value(positions, target, px["close"])
            deployable = max(0.0, equity - stuck_val)
            per_target = deployable / float(len(target))

            for code in target:
                if code not in px.index:
                    continue
                cl = float(px.loc[code, "close"])
                cur_sh = float(positions.get(code, 0.0))
                cur_val = cur_sh * cl
                if cur_val <= per_target + 1e-6:
                    continue
                if bool(px.loc[code, "sell_blocked_limit_down"]):
                    continue
                tgt_sh = per_target / cl
                delta = cur_sh - tgt_sh
                if delta <= 1e-12:
                    continue
                positions[code] = cur_sh - delta
                if positions[code] <= 1e-12:
                    del positions[code]
                cash += self._cash_from_sell(delta, cl)

            m2m = _portfolio_market_value(positions, px["close"])
            equity = cash + m2m
            stuck_val = _stuck_non_target_value(positions, target, px["close"])
            deployable = max(0.0, equity - stuck_val)
            per_target = deployable / float(len(target))

            for code in target:
                if code not in px.index:
                    continue
                cl = float(px.loc[code, "close"])
                if bool(px.loc[code, "buy_blocked_limit_up"]):
                    continue
                cur_sh = float(positions.get(code, 0.0))
                cur_val = cur_sh * cl
                need = per_target - cur_val
                if need <= 1e-6:
                    continue
                cps = self._buy_cash_per_share(cl)
                max_cash_buy = cash / cps if cps > 0 else 0.0
                buy_sh = min(need / cl, max_cash_buy)
                if buy_sh <= 1e-12:
                    continue
                cash -= buy_sh * cps
                positions[code] = cur_sh + buy_sh

            m2m = _portfolio_market_value(positions, px["close"])
            total = cash + m2m
            rows.append(
                {
                    "date": dt,
                    "total_value": float(total),
                    "cash": float(cash),
                    "holdings": _holdings_json(positions),
                }
            )

        del scored_by_date
        result = pd.DataFrame(rows)
        if result.empty:
            return result
        return result.sort_values("date").reset_index(drop=True)


def _holdings_json(positions: dict[str, float]) -> str:
    d = {k: float(positions[k]) for k in sorted(positions)}
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def _portfolio_market_value(positions: dict[str, float], close_series: pd.Series) -> float:
    s = 0.0
    for code, sh in positions.items():
        if code in close_series.index and sh > 0:
            s += float(sh) * float(close_series.loc[code])
    return s


def _stuck_non_target_value(
    positions: dict[str, float],
    target: list[str],
    close_series: pd.Series,
) -> float:
    """因跌停等未能卖出的非目标持仓市值（仍计入总权益，但不参与 Top N 等额分配）。"""
    tset = set(target)
    s = 0.0
    for code, sh in positions.items():
        if code in tset:
            continue
        if code in close_series.index and sh > 0:
            s += float(sh) * float(close_series.loc[code])
    return s


def _synthetic_close_from_weekly_returns(df: pd.DataFrame) -> pd.Series:
    """
    无 close 列时，用 future_return_1w 在股票内递推周收盘价（首周锚定 100），仅用于回测与涨跌停价。
    与 split_by_time 等生成的 parquet 兼容。
    """
    idx = df.index
    work = df.sort_values(["stock_code", "date"])
    pieces: list[pd.Series] = []
    for _, g in work.groupby("stock_code", sort=False):
        r = pd.to_numeric(g["future_return_1w"], errors="coerce").to_numpy(dtype=np.float64)
        fac = np.ones(len(r), dtype=np.float64)
        for j in range(1, len(r)):
            x = r[j - 1]
            fac[j] = fac[j - 1] * (1.0 if np.isnan(x) else (1.0 + x))
        pieces.append(pd.Series(100.0 * fac, index=g.index))
    s = pd.concat(pieces)
    return s.reindex(idx)


def _engine_params_snapshot(eng: BacktestEngine, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "model_type": eng.model_type,
        "top_n": eng.top_n,
        "initial_capital": eng.initial_capital,
        "commission": eng.commission,
        "slippage": eng.slippage,
        "stamp_tax": eng.stamp_tax,
    }
    if extra:
        base.update(extra)
    return base


def _nav_points_from_result_df(result_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in result_df.iterrows():
        rows.append(
            {
                "date": pd.Timestamp(row["date"]).date().isoformat(),
                "nav": float(row["total_value"]),
            }
        )
    return rows


def _holdings_series_from_result_df(result_df: pd.DataFrame) -> list[dict[str, Any]]:
    """每周持仓明细，与导出的 *_holdings.json 中 series 结构一致。"""
    has_holdings = "holdings" in result_df.columns
    series: list[dict[str, Any]] = []
    for _, row in result_df.iterrows():
        raw = row["holdings"] if has_holdings else None
        holdings = _parse_holdings_cell(raw)
        series.append({"date": pd.Timestamp(row["date"]).date().isoformat(), "holdings": holdings})
    return series


def _parse_holdings_cell(raw: object) -> dict[str, float]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return {}
    if isinstance(raw, str) and raw.strip():
        try:
            return {str(k): float(v) for k, v in json.loads(raw).items()}
        except json.JSONDecodeError:
            return {}
    if isinstance(raw, dict):
        return {str(k): float(v) for k, v in raw.items()}
    return {}


def _price_map_at_date(weekly_df: pd.DataFrame, dt: pd.Timestamp) -> dict[str, float]:
    sub = weekly_df[weekly_df["date"] == dt]
    if sub.empty:
        return {}
    out: dict[str, float] = {}
    for _, r in sub.iterrows():
        c = float(pd.to_numeric(r["close"], errors="coerce") or 0.0)
        if c > 0:
            out[str(r["stock_code"])] = c
    return out


def build_rebalance_turnover_trades(result_df: pd.DataFrame, weekly_df: pd.DataFrame) -> pd.DataFrame:
    """
    由相邻两周持仓差与当周收盘价估算调仓买卖金额，供 turnover_rate 使用（与周频回测口径一致）。
    """
    df = result_df.sort_values("date").reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    prev: dict[str, float] = {}
    for _, row in df.iterrows():
        dt = pd.Timestamp(row["date"])
        curr = _parse_holdings_cell(row["holdings"])
        px = _price_map_at_date(weekly_df, dt)
        buy_amt = 0.0
        sell_amt = 0.0
        for code in set(prev) | set(curr):
            dsh = float(curr.get(code, 0.0) - prev.get(code, 0.0))
            price = px.get(code)
            if price is None or price <= 0 or math.isnan(dsh):
                continue
            if dsh > 0:
                buy_amt += dsh * price
            elif dsh < 0:
                sell_amt += (-dsh) * price
        rows.append(
            {
                "date": dt,
                "buy_amount": buy_amt,
                "sell_amount": sell_amt,
                "total_value": float(row["total_value"]),
            }
        )
        prev = curr
    return pd.DataFrame(rows)


def weekly_portfolio_win_rate(result_df: pd.DataFrame) -> float | None:
    """相邻调仓周组合净值收益 > 0 的周数占比（策略周度胜率）。"""
    if result_df.shape[0] < 2:
        return None
    nav = pd.to_numeric(result_df["total_value"], errors="coerce").astype(float)
    r = nav.pct_change().dropna()
    if r.empty:
        return None
    return float((r > 0).mean())


def average_holding_weeks(result_df: pd.DataFrame) -> float | None:
    """每只股票连续持有周数的简单算术平均（跨所有持有片段）。"""
    if result_df.empty:
        return None
    sets: list[set[str]] = []
    for _, row in result_df.iterrows():
        sets.append(set(_parse_holdings_cell(row["holdings"]).keys()))
    lengths: list[int] = []
    all_codes: set[str] = set()
    for s in sets:
        all_codes |= s
    for code in all_codes:
        in_run = False
        run_len = 0
        for s in sets:
            if code in s:
                if not in_run:
                    in_run = True
                    run_len = 1
                else:
                    run_len += 1
            else:
                if in_run:
                    lengths.append(run_len)
                    in_run = False
                    run_len = 0
        if in_run:
            lengths.append(run_len)
    if not lengths:
        return None
    return float(np.mean(lengths))


def monthly_returns_heatmap_data(dates: list[str], nav_values: list[float]) -> dict[str, Any]:
    """自然月维度：取每月最后一个调仓日净值，计算月度收益率，供热力图矩阵使用。"""
    if len(dates) < 2:
        return {
            "years": [],
            "month_columns": list(range(1, 13)),
            "values": [],
            "note": "样本不足",
        }
    df = pd.DataFrame({"dt": pd.to_datetime(pd.Series(dates)), "nav": nav_values}).sort_values("dt")
    df["ym"] = df["dt"].dt.to_period("M")
    last_nav = df.groupby("ym", sort=True)["nav"].last()
    rets = last_nav.pct_change()
    years = sorted({int(p.year) for p in last_nav.index})
    mat: list[list[float | None]] = []
    for y in years:
        row: list[float | None] = []
        for m in range(1, 13):
            p = pd.Period(year=y, month=m, freq="M")
            if p not in rets.index:
                row.append(None)
                continue
            v = float(rets.loc[p])
            row.append(None if math.isnan(v) else v)
        mat.append(row)
    return {
        "years": years,
        "month_columns": list(range(1, 13)),
        "values": mat,
        "note": "按自然月内最后一个调仓日净值计算月度收益；首月无前值则为空",
    }


def align_comparison_nav_curves(
    result_df_lgb: pd.DataFrame,
    result_df_xgb: pd.DataFrame,
) -> dict[str, Any]:
    """
    两模型净值曲线时间对齐（内连接 date），归一化净值与 LightGBM 相对 XGBoost 的超额（比值为 LGB/XGB-1）。
    """
    if result_df_lgb.empty or result_df_xgb.empty:
        return {
            "granularity": "weekly",
            "dates": [],
            "lightgbm_nav": [],
            "xgboost_nav": [],
            "lightgbm_nav_norm": [],
            "xgboost_nav_norm": [],
            "excess_lightgbm_over_xgb_nav": [],
            "note": "空结果",
        }
    a = result_df_lgb[["date", "total_value"]].rename(columns={"total_value": "nav_lgb"})
    b = result_df_xgb[["date", "total_value"]].rename(columns={"total_value": "nav_xgb"})
    a["date"] = pd.to_datetime(a["date"])
    b["date"] = pd.to_datetime(b["date"])
    m = pd.merge(a, b, on="date", how="inner")
    if m.empty:
        return {
            "granularity": "weekly",
            "dates": [],
            "lightgbm_nav": [],
            "xgboost_nav": [],
            "lightgbm_nav_norm": [],
            "xgboost_nav_norm": [],
            "excess_lightgbm_over_xgb_nav": [],
            "note": "日期交集为空",
        }
    if len(m) != len(a) or len(m) != len(b):
        logger.warning(
            "LightGBM 与 XGBoost 回测调仓日不完全一致，已用交集 %d 条对齐曲线",
            len(m),
        )
    dates = [pd.Timestamp(x).date().isoformat() for x in m["date"]]
    v1 = [float(x) for x in m["nav_lgb"]]
    v2 = [float(x) for x in m["nav_xgb"]]
    if v1[0] <= 0 or v2[0] <= 0:
        n1, n2 = v1, v2
        excess = [0.0] * len(v1)
    else:
        n1 = [x / v1[0] for x in v1]
        n2 = [x / v2[0] for x in v2]
        excess = [a / b - 1.0 if b != 0 else 0.0 for a, b in zip(n1, n2)]
    return {
        "granularity": "weekly",
        "dates": dates,
        "lightgbm_nav": v1,
        "xgboost_nav": v2,
        "lightgbm_nav_norm": n1,
        "xgboost_nav_norm": n2,
        "excess_lightgbm_over_xgb_nav": excess,
        "note": "excess = lightgbm_nav_norm / xgboost_nav_norm - 1",
    }


def metrics_table_with_difference(
    metrics_lightgbm: dict[str, Any],
    metrics_xgboost: dict[str, Any],
) -> list[dict[str, Any]]:
    keys = sorted(set(metrics_lightgbm) | set(metrics_xgboost))
    rows: list[dict[str, Any]] = []
    for k in keys:
        a, b = metrics_lightgbm.get(k), metrics_xgboost.get(k)
        diff: float | None = None
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not math.isnan(float(a)) and not math.isnan(float(b)):
                diff = float(a) - float(b)
        rows.append({"metric": k, "lightgbm": a, "xgboost": b, "difference": diff})
    return rows


def _scrub_for_json_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _scrub_for_json_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_for_json_obj(x) for x in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, (np.floating, np.integer)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    return obj


def _dual_backtest_core(
    *,
    top_n: int = 10,
    initial_capital: float = 1_000_000.0,
    use_split: Literal["test", "all"] = "test",
    train_end: str = "2020-12-31",
    val_end: str = "2022-12-31",
    skip_initial_weeks: int = 0,
    data_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """
    加载同一周频数据，用相同参数跑 LightGBM / XGBoost（保证测试区间与调仓日一致）。
    """
    extra_params: dict[str, Any] = {
        "use_split": use_split,
        "train_end": train_end,
        "val_end": val_end,
        "skip_initial_weeks": skip_initial_weeks,
    }
    first_eng = BacktestEngine("lightgbm", top_n, initial_capital, data_dir=data_dir)
    weekly_df = first_eng.load_weekly_data()
    packs: dict[str, dict[str, Any]] = {}
    for kind in ("lightgbm", "xgboost"):
        eng = BacktestEngine(kind, top_n, initial_capital, data_dir=data_dir)
        result_df = eng.run_backtest(
            weekly_df,
            use_split=use_split,
            train_end=train_end,
            val_end=val_end,
            skip_initial_weeks=skip_initial_weeks,
        )
        params = _engine_params_snapshot(eng, extra=extra_params)
        packs[kind] = {"result_df": result_df, "params": params}
    return weekly_df, packs


def compute_backtest_metrics(
    result_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    *,
    extended: bool = False,
) -> dict[str, Any]:
    """日频填充后的年化/夏普/回撤；extended 时追加换手率、周度胜率、平均持有周数。"""
    if result_df.empty:
        return {}
    nav_w = pd.Series(result_df["total_value"].to_numpy(), index=pd.to_datetime(result_df["date"]))
    nav_d = weekly_nav_to_daily_business_ffill(nav_w)
    if not extended:
        return aggregate_metrics(nav_d)
    trades = build_rebalance_turnover_trades(result_df, weekly_df)
    m = aggregate_metrics(nav_d, trades_df=trades)
    wr = weekly_portfolio_win_rate(result_df)
    m["win_rate"] = wr
    ah = average_holding_weeks(result_df)
    m["avg_holding_weeks"] = ah
    return json.loads(json.dumps(_scrub_for_json_obj(m), ensure_ascii=False, default=str))


def fetch_csi300_benchmark(start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    """
    使用 akshare 拉取沪深300（000300）日线收盘，净值 = 收盘价 / 区间首日收盘价。
    网络失败时返回空序列，source=unavailable，便于离线环境仍完成导出。
    """
    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    dates: list[str] = []
    navs: list[float] = []
    source = "akshare"
    try:
        import akshare as ak

        df = ak.index_zh_a_hist(
            symbol="000300",
            period="daily",
            start_date=start_ts.strftime("%Y%m%d"),
            end_date=end_ts.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            raise ValueError("empty benchmark dataframe")
        dcol = "日期" if "日期" in df.columns else "date"
        ccol = "收盘" if "收盘" in df.columns else ("close" if "close" in df.columns else None)
        if ccol is None:
            raise ValueError("benchmark missing close column")
        sub = (
            pd.DataFrame(
                {
                    "dt": pd.to_datetime(df[dcol]),
                    "close": pd.to_numeric(df[ccol], errors="coerce"),
                }
            )
            .dropna()
            .sort_values("dt")
        )
        if sub.empty:
            raise ValueError("no valid benchmark rows")
        c0 = float(sub["close"].iloc[0])
        if c0 <= 0:
            raise ValueError("invalid first close")
        dates = [pd.Timestamp(t).date().isoformat() for t in sub["dt"]]
        navs = [float(c / c0) for c in sub["close"]]
    except Exception as exc:
        logger.warning("沪深300 基准拉取失败，使用空序列: %s", exc)
        source = "unavailable"
    return {
        "index_code": "000300.SH",
        "name": "沪深300",
        "granularity": "daily",
        "dates": dates,
        "nav_values": navs,
        "source": source,
        "range": {
            "start": start_ts.date().isoformat(),
            "end": end_ts.date().isoformat(),
        },
        "note": "nav 以区间内首个有效交易日收盘价归一为 1.0",
    }


def persist_backtest_result(
    *,
    model_type: str,
    params: dict[str, Any],
    result_df: pd.DataFrame,
    metrics: dict[str, Any],
) -> int:
    """写入 backtest_result 表；返回自增 id。"""
    init_db()
    nav_payload = {
        "granularity": "weekly",
        "nav_points": _nav_points_from_result_df(result_df),
        "holdings_series": _holdings_series_from_result_df(result_df),
        "note": "调仓日净值与持仓；指标基于工作日前向填充后的日频序列计算",
    }
    rec = BacktestResult(
        model_type=model_type,
        params_json=json.dumps(params, ensure_ascii=False, default=str),
        nav_json=json.dumps(nav_payload, ensure_ascii=False, default=str),
        metrics_json=metrics_to_json(metrics),
    )
    with session_scope() as session:
        session.add(rec)
        session.flush()
        rid = int(rec.id)
    logger.info("已写入 backtest_result id=%s model=%s", rid, model_type)
    return rid


def build_comparison_json(metrics_lightgbm: dict[str, Any], metrics_xgboost: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "metrics_table": metrics_table_with_difference(metrics_lightgbm, metrics_xgboost),
    }


def save_results_to_json(
    *,
    out_dir: Path,
    lightgbm_pack: dict[str, Any],
    xgboost_pack: dict[str, Any],
    benchmark: dict[str, Any],
) -> None:
    """
    导出前端静态 JSON：各模型 nav / benchmark / metrics / holdings，以及 comparison.json。
    benchmark 内容按模型各写一份（文件名区分），便于前端单模型目录部署。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def _write_nav(prefix: str, pack: dict[str, Any]) -> None:
        df = pack["result_df"]
        if df.empty:
            return
        obj = {
            "model_type": prefix,
            "granularity": "weekly",
            "dates": [pd.Timestamp(d).date().isoformat() for d in df["date"]],
            "nav_values": [float(x) for x in df["total_value"]],
        }
        (out_dir / f"{prefix}_nav.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_metrics(prefix: str, pack: dict[str, Any]) -> None:
        if pack["result_df"].empty:
            return
        (out_dir / f"{prefix}_metrics.json").write_text(
            json.dumps(pack["metrics"], ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def _write_holdings(prefix: str, pack: dict[str, Any]) -> None:
        df = pack["result_df"]
        if df.empty:
            return
        series = _holdings_series_from_result_df(df)
        obj = {"model_type": prefix, "granularity": "weekly", "series": series}
        (out_dir / f"{prefix}_holdings.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_benchmark(prefix: str) -> None:
        (out_dir / f"{prefix}_benchmark.json").write_text(
            json.dumps(benchmark, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    for prefix, pack in (("lightgbm", lightgbm_pack), ("xgboost", xgboost_pack)):
        _write_nav(prefix, pack)
        _write_metrics(prefix, pack)
        _write_holdings(prefix, pack)
        _write_benchmark(prefix)

    comp = build_comparison_json(lightgbm_pack.get("metrics", {}), xgboost_pack.get("metrics", {}))
    (out_dir / "comparison.json").write_text(
        json.dumps(comp, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("已导出 JSON 至 %s", out_dir.resolve())


def run_backtest_and_export(
    *,
    top_n: int = 10,
    initial_capital: float = 1_000_000.0,
    use_split: Literal["test", "all"] = "test",
    train_end: str = "2020-12-31",
    val_end: str = "2022-12-31",
    skip_initial_weeks: int = 0,
    out_dir: Path | None = None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """
    对 LightGBM / XGBoost 各跑一次回测，写 SQLite，再写入 data/backtest_results/ 下 JSON。
    返回 {"lightgbm": pack, "xgboost": pack, "benchmark": dict, "out_dir": str}
    """
    out = Path(out_dir) if out_dir is not None else BACKTEST_RESULTS_DIR
    weekly_df, packs = _dual_backtest_core(
        top_n=top_n,
        initial_capital=initial_capital,
        use_split=use_split,
        train_end=train_end,
        val_end=val_end,
        skip_initial_weeks=skip_initial_weeks,
        data_dir=data_dir,
    )

    for kind in ("lightgbm", "xgboost"):
        result_df = packs[kind]["result_df"]
        params = packs[kind]["params"]
        if result_df.empty:
            logger.warning("模型 %s 回测结果为空，跳过落库与部分 JSON", kind)
            packs[kind]["metrics"] = {}
            continue
        metrics = compute_backtest_metrics(result_df, weekly_df, extended=False)
        persist_backtest_result(model_type=kind, params=params, result_df=result_df, metrics=metrics)
        packs[kind]["metrics"] = metrics

    all_dates: list[pd.Timestamp] = []
    for p in packs.values():
        df = p["result_df"]
        if not df.empty:
            all_dates.extend(pd.to_datetime(df["date"]).tolist())
    if all_dates:
        bench = fetch_csi300_benchmark(pd.Timestamp(min(all_dates)), pd.Timestamp(max(all_dates)))
    else:
        bench = fetch_csi300_benchmark(pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02"))

    save_results_to_json(
        out_dir=out,
        lightgbm_pack=packs["lightgbm"],
        xgboost_pack=packs["xgboost"],
        benchmark=bench,
    )

    return {
        "lightgbm": packs["lightgbm"],
        "xgboost": packs["xgboost"],
        "benchmark": bench,
        "out_dir": str(out.resolve()),
    }


def write_backtest_comparison_html(nav_pack: dict[str, Any], out_path: Path) -> bool:
    """Plotly 双净值 + 超额曲线；未安装 plotly 时返回 False。"""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        logger.warning("未安装 plotly，跳过 HTML 报告（pip install plotly）")
        return False
    dates = nav_pack.get("dates") or []
    if not dates:
        logger.warning("无对齐净值数据，跳过 HTML")
        return False
    n1 = nav_pack["lightgbm_nav_norm"]
    n2 = nav_pack["xgboost_nav_norm"]
    ex = nav_pack["excess_lightgbm_over_xgb_nav"]
    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.62, 0.38],
        vertical_spacing=0.1,
        subplot_titles=("归一化净值（起点=1）", "LightGBM 相对 XGBoost 超额（LGB/XGB - 1）"),
    )
    fig.add_trace(
        go.Scatter(x=dates, y=n1, name="LightGBM", line=dict(width=1.5)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=dates, y=n2, name="XGBoost", line=dict(width=1.5)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(x=dates, y=ex, name="超额", marker_color="rgba(80,80,120,0.55)"),
        row=2,
        col=1,
    )
    fig.update_layout(
        height=720,
        title_text="LightGBM vs XGBoost 策略对比",
        showlegend=True,
        template="plotly_white",
    )
    fig.update_xaxes(title_text="日期", row=2, col=1)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
    logger.info("已写入 Plotly 报告 %s", out_path.resolve())
    return True


def run_comparison(
    *,
    top_n: int = 10,
    initial_capital: float = 1_000_000.0,
    use_split: Literal["test", "all"] = "test",
    train_end: str = "2020-12-31",
    val_end: str = "2022-12-31",
    skip_initial_weeks: int = 0,
    out_dir: Path | None = None,
    data_dir: Path | None = None,
    write_html: bool = True,
    html_path: Path | None = None,
) -> dict[str, Any]:
    """
    独立对比：同一数据、同一参数跑两模型；扩展指标（换手、胜率、平均持有周数）；
    写 comparison.json（含热力图与并排表）、comparison_nav.json；可选 Plotly HTML。
    """
    out = Path(out_dir) if out_dir is not None else BACKTEST_RESULTS_DIR
    weekly_df, packs = _dual_backtest_core(
        top_n=top_n,
        initial_capital=initial_capital,
        use_split=use_split,
        train_end=train_end,
        val_end=val_end,
        skip_initial_weeks=skip_initial_weeks,
        data_dir=data_dir,
    )

    for kind in ("lightgbm", "xgboost"):
        result_df = packs[kind]["result_df"]
        if result_df.empty:
            packs[kind]["metrics"] = {}
            continue
        packs[kind]["metrics"] = compute_backtest_metrics(result_df, weekly_df, extended=True)

    m_lgb = packs["lightgbm"].get("metrics") or {}
    m_xgb = packs["xgboost"].get("metrics") or {}
    dfl = packs["lightgbm"]["result_df"]
    dfx = packs["xgboost"]["result_df"]

    nav_pack = align_comparison_nav_curves(dfl, dfx)
    heat_lgb = monthly_returns_heatmap_data(
        [pd.Timestamp(x).date().isoformat() for x in dfl["date"]] if not dfl.empty else [],
        [float(x) for x in dfl["total_value"]] if not dfl.empty else [],
    )
    heat_xgb = monthly_returns_heatmap_data(
        [pd.Timestamp(x).date().isoformat() for x in dfx["date"]] if not dfx.empty else [],
        [float(x) for x in dfx["total_value"]] if not dfx.empty else [],
    )

    comparison_doc: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "kind": "strategy_comparison",
        "params_common": packs["lightgbm"].get("params") or packs["xgboost"].get("params"),
        "metrics_lightgbm": m_lgb,
        "metrics_xgboost": m_xgb,
        "metrics_table": metrics_table_with_difference(m_lgb, m_xgb),
        "monthly_returns_heatmap": {
            "lightgbm": heat_lgb,
            "xgboost": heat_xgb,
        },
        "comparison_nav_file": "comparison_nav.json",
        "notes": {
            "nav_alignment": nav_pack.get("note"),
            "win_rate": "周度胜率：相邻调仓周组合净值收益为正的周占比",
            "avg_holding_weeks": "平均持有周数：各标的连续持有周数的算术平均",
        },
    }
    comparison_doc = _scrub_for_json_obj(comparison_doc)

    out.mkdir(parents=True, exist_ok=True)
    (out / "comparison.json").write_text(
        json.dumps(comparison_doc, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    nav_out = _scrub_for_json_obj(nav_pack)
    (out / "comparison_nav.json").write_text(
        json.dumps(nav_out, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("已写入对比 JSON：%s", (out / "comparison.json").resolve())

    html_written = False
    html_resolved: str | None = None
    if write_html:
        hp = Path(html_path) if html_path is not None else REPORTS_DIR / "backtest_comparison.html"
        html_written = write_backtest_comparison_html(nav_pack, hp)
        if html_written:
            html_resolved = str(hp.resolve())

    return {
        "lightgbm": packs["lightgbm"],
        "xgboost": packs["xgboost"],
        "comparison": comparison_doc,
        "comparison_nav": nav_pack,
        "out_dir": str(out.resolve()),
        "html_report": html_resolved,
    }


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    eng = BacktestEngine("lightgbm", top_n=10, initial_capital=1_000_000.0)
    out = eng.run_backtest(use_split="test")
    print(out.head())
    print("...")
    print(out.tail())
    if not out.empty:
        print("final_nav", float(out["total_value"].iloc[-1]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="周频回测：快速预览或 --run 持久化+导出 JSON")
    parser.add_argument(
        "--run",
        action="store_true",
        help="运行 LightGBM+XGBoost 回测，写入 SQLite(backtest_result) 与 data/backtest_results/*.json",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="仅跑双模型对比：扩展指标、comparison.json、comparison_nav.json，可选 Plotly HTML",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="与 --compare 联用：不生成 reports/backtest_comparison.html",
    )
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--initial-capital", type=float, default=1_000_000.0)
    parser.add_argument("--use-split", choices=("test", "all"), default="test")
    parser.add_argument("--train-end", default="2020-12-31")
    parser.add_argument("--val-end", default="2022-12-31")
    parser.add_argument("--skip-initial-weeks", type=int, default=0)
    parser.add_argument("--out-dir", type=str, default="", help="JSON 输出目录，默认 backend/data/backtest_results")
    args = parser.parse_args()
    od = Path(args.out_dir) if args.out_dir.strip() else None
    if args.compare:
        run_comparison(
            top_n=args.top_n,
            initial_capital=args.initial_capital,
            use_split=args.use_split,  # type: ignore[arg-type]
            train_end=args.train_end,
            val_end=args.val_end,
            skip_initial_weeks=args.skip_initial_weeks,
            out_dir=od,
            write_html=not args.no_html,
        )
    elif args.run:
        run_backtest_and_export(
            top_n=args.top_n,
            initial_capital=args.initial_capital,
            use_split=args.use_split,  # type: ignore[arg-type]
            train_end=args.train_end,
            val_end=args.val_end,
            skip_initial_weeks=args.skip_initial_weeks,
            out_dir=od,
        )
    else:
        _main()
