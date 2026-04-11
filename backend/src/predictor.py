"""
统一预测接口：加载 LightGBM / XGBoost 排序模型，对单截面因子输出得分与 Top N。

用法::

    python -m src.predictor
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

import lightgbm as lgb
import xgboost as xgb

from .config import get_settings
from .data_loader import fill_missing_factors, load_current_snapshot, load_factor_columns
from .model_lightgbm import load_lightgbm_model
from .model_xgboost import load_xgboost_model

logger = logging.getLogger(__name__)

ModelKind = Literal["lightgbm", "xgboost"]
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_backend_paths() -> tuple[Path, Path, Path]:
    s = get_settings()
    data_dir = Path(s.quant_data_dir) if s.quant_data_dir.strip() else PROJECT_ROOT / "data"
    lgb_p = Path(s.lightgbm_model_path) if s.lightgbm_model_path.strip() else PROJECT_ROOT / "models" / "lightgbm.pkl"
    xgb_p = Path(s.xgboost_model_path) if s.xgboost_model_path.strip() else PROJECT_ROOT / "models" / "xgboost.pkl"
    return data_dir, lgb_p, xgb_p


class ModelPredictor:
    """按训练时因子顺序对齐列，缺失值列内中位数填充（与 data_loader.fill_missing_factors 一致）。"""

    def __init__(
        self,
        model_type: ModelKind,
        *,
        data_dir: Path | None = None,
        model_path: Path | None = None,
    ) -> None:
        self.model_type: ModelKind = model_type
        cfg_data, cfg_lgb, cfg_xgb = _resolve_backend_paths()
        self._data_dir = Path(data_dir) if data_dir is not None else cfg_data

        if model_type == "lightgbm":
            mp = Path(model_path) if model_path is not None else cfg_lgb
            self._booster: lgb.Booster | xgb.Booster = load_lightgbm_model(mp)
        elif model_type == "xgboost":
            mp = Path(model_path) if model_path is not None else cfg_xgb
            self._booster = load_xgboost_model(mp)
        else:
            raise ValueError("model_type 必须为 'lightgbm' 或 'xgboost'")

        self._factor_cols: list[str] = load_factor_columns(data_dir=self._data_dir)
        self._model_path = mp

    def get_model_trained_at(self) -> str | None:
        """模型文件修改时间（训练落盘时间近似），ISO8601 字符串。"""
        try:
            p = self._model_path
            if p.exists():
                return datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
        except OSError:
            pass
        return None

    def get_feature_importance(self) -> dict[str, float]:
        """当前模型全局 gain 特征重要性（与训练落盘 JSON 同源逻辑）。"""
        if self.model_type == "lightgbm":
            bst = self._booster
            assert isinstance(bst, lgb.Booster)
            imp = bst.feature_importance(importance_type="gain")
            names = bst.feature_name() or self._factor_cols
            arr = np.asarray(imp, dtype=float)
            if len(names) != len(arr):
                names = self._factor_cols[: len(arr)]
            return {str(n): float(v) for n, v in zip(names, arr)}
        bst = self._booster
        assert isinstance(bst, xgb.Booster)
        raw = bst.get_score(importance_type="gain")
        fkey_to_name = {f"f{i}": name for i, name in enumerate(self._factor_cols)}
        result = {}
        for name in self._factor_cols:
            fkey = fkey_to_name.get(name, name)
            result[name] = float(raw.get(fkey, raw.get(name, 0.0)))
        return result

    def _align_factor_frame(self, factor_df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
        if factor_df.empty:
            raise ValueError("factor_df 为空")
        if "stock_code" not in factor_df.columns:
            raise ValueError("factor_df 必须包含 stock_code 列")
        codes = factor_df["stock_code"].astype(str)
        X = pd.DataFrame(
            {c: factor_df[c] if c in factor_df.columns else np.nan for c in self._factor_cols},
            index=factor_df.index,
        )
        X = fill_missing_factors(X, factor_cols=self._factor_cols, method="median")
        return codes, X

    def _matrix(self, X: pd.DataFrame) -> np.ndarray:
        return np.ascontiguousarray(X[self._factor_cols].to_numpy(dtype=np.float32, copy=True))

    def predict(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """
        输入含 stock_code 与（部分或全部）因子列的 DataFrame。
        返回与训练因子列顺序一致的矩阵（含中位数填充后的因子值）、stock_code、score，按 score 降序。
        """
        codes, X = self._align_factor_frame(factor_df)
        X_m = self._matrix(X)
        if self.model_type == "lightgbm":
            scores = self._booster.predict(X_m)
        else:
            dm = xgb.DMatrix(X_m, feature_names=self._factor_cols)
            scores = self._booster.predict(dm)
        out = X.copy()
        out.insert(0, "stock_code", codes.values)
        out["score"] = np.asarray(scores, dtype=np.float64)
        return out.sort_values("score", ascending=False, kind="mergesort").reset_index(drop=True)

    def predict_panel(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """
        多调仓日批量推理：每行含 date、stock_code 及（部分）因子列；返回与输入行对齐的
        date、stock_code、score。模型固定时一次 predict 全样本，避免按周重复调用开销。
        """
        if factor_df.empty:
            return pd.DataFrame(columns=["date", "stock_code", "score"])
        if "date" not in factor_df.columns:
            raise ValueError("predict_panel 需要 date 列")
        work = factor_df.reset_index(drop=True)
        dt_arr = pd.to_datetime(work["date"], errors="coerce")
        factor_part = work[["stock_code"] + [c for c in self._factor_cols if c in work.columns]]
        codes, X = self._align_factor_frame(factor_part)
        X_m = self._matrix(X)
        if self.model_type == "lightgbm":
            scores = self._booster.predict(X_m)
        else:
            dm = xgb.DMatrix(X_m, feature_names=self._factor_cols)
            scores = self._booster.predict(dm)
        return pd.DataFrame(
            {
                "date": dt_arr,
                "stock_code": codes.astype(str).to_numpy(),
                "score": np.asarray(scores, dtype=np.float64),
            }
        )

    def _row_contributions(self, X_m: np.ndarray) -> list[dict[str, float]] | None:
        """逐样本特征贡献（近似树模型局部解释）；失败时返回 None。"""
        try:
            if self.model_type == "lightgbm":
                bst = self._booster
                assert isinstance(bst, lgb.Booster)
                raw = bst.predict(X_m, pred_contrib=True)
                arr = np.asarray(raw, dtype=np.float64)
                if arr.ndim == 1:
                    return None
                # (n_samples, n_features + 1)，最后一列为 bias
                nfeat = arr.shape[1] - 1
                if nfeat == len(self._factor_cols):
                    names = list(self._factor_cols)
                else:
                    names = bst.feature_name() or self._factor_cols
                    if len(names) < nfeat:
                        names = [f"f{i}" for i in range(nfeat)]
                    else:
                        names = [str(names[i]) for i in range(nfeat)]
                rows: list[dict[str, float]] = []
                for i in range(arr.shape[0]):
                    rows.append({names[j]: float(arr[i, j]) for j in range(nfeat)})
                return rows
            dm = xgb.DMatrix(X_m, feature_names=self._factor_cols)
            raw = self._booster.predict(dm, pred_contribs=True)
            arr = np.asarray(raw, dtype=np.float64)
            if arr.ndim == 1:
                return None
            nfeat = arr.shape[1] - 1
            rows = []
            for i in range(arr.shape[0]):
                rows.append({self._factor_cols[j]: float(arr[i, j]) for j in range(min(nfeat, len(self._factor_cols)))})
            return rows
        except Exception as e:
            logger.warning("特征贡献计算跳过: %s", e)
            return None

    def get_top_stocks(
        self,
        factor_df: pd.DataFrame,
        top_n: int = 20,
        *,
        with_contributions: bool = True,
    ) -> pd.DataFrame:
        """
        得分最高的 top_n 只股票：stock_code、score；
        with_contributions=True 时增加 feature_contrib（每行一个 dict：特征 -> 该样本上的贡献值）。
        """
        if top_n < 1:
            raise ValueError("top_n 至少为 1")
        codes, X = self._align_factor_frame(factor_df)
        X_m = self._matrix(X)
        if self.model_type == "lightgbm":
            scores = np.asarray(self._booster.predict(X_m), dtype=np.float64)
        else:
            dm = xgb.DMatrix(X_m, feature_names=self._factor_cols)
            scores = np.asarray(self._booster.predict(dm), dtype=np.float64)

        order = np.lexsort((np.arange(len(scores), dtype=np.int64), -scores))
        take = order[:top_n]

        rows: list[dict[str, Any]] = []
        contribs: list[dict[str, float]] | None = None
        if with_contributions:
            contribs = self._row_contributions(X_m)

        for rank, idx in enumerate(take):
            row: dict[str, Any] = {
                "stock_code": str(codes.iloc[int(idx)]),
                "score": float(scores[int(idx)]),
                "rank": rank + 1,
            }
            if with_contributions:
                if contribs is not None and int(idx) < len(contribs):
                    row["feature_contrib"] = contribs[int(idx)]
                else:
                    row["feature_contrib"] = None
            rows.append(row)

        return pd.DataFrame(rows)

    def get_advice_context(
        self,
        top_n: int = 10,
        *,
        factor_df: pd.DataFrame | None = None,
        section_date: str | None = None,
    ) -> dict[str, Any]:
        """
        供 AI 推荐服务使用的结构化上下文：Top 股票代码与得分、全局特征重要性、截面日期。
        factor_df 为 None 时自动 load_prediction_data（实时截面，失败则 test.parquet）。
        """
        if factor_df is None:
            factor_df, section_date = load_prediction_data(data_dir=self._data_dir)
        if section_date is None:
            section_date = date.today().isoformat()
        top = self.get_top_stocks(factor_df, top_n=top_n, with_contributions=False)
        stocks = [{"code": str(r["stock_code"]), "score": float(r["score"])} for _, r in top.iterrows()]
        return {
            "top_stocks": stocks,
            "feature_importance": self.get_feature_importance(),
            "section_date": section_date,
            "model_type": self.model_type,
        }

    def __repr__(self) -> str:
        return f"ModelPredictor({self.model_type!r}, model={self._model_path})"


def _fallback_frame_from_test_parquet(
    data_dir: Path,
    max_rows: int = 2000,
    *,
    include_date: bool = False,
) -> pd.DataFrame:
    """无实时行情时的离线样本：与训练同分布的 test.parquet 片段。"""
    path = data_dir / "test.parquet"
    if not path.exists():
        raise FileNotFoundError(str(path))
    factor_cols = load_factor_columns(data_dir=data_dir)
    df = pd.read_parquet(path)
    cols = ["stock_code"]
    if include_date and "date" in df.columns:
        cols.append("date")
    cols += [c for c in factor_cols if c in df.columns]
    return df[cols].head(max_rows)


def load_prediction_data(
    *,
    data_dir: Path | None = None,
    latest_date: str | None = None,
) -> tuple[pd.DataFrame, str]:
    """
    加载当前用于预测的因子截面：优先 load_current_snapshot；失败则回退 test.parquet。
    返回 (仅含因子 + stock_code 的 DataFrame, 截面日期 YYYY-MM-DD)。
    """
    data_dir = Path(data_dir) if data_dir else _resolve_backend_paths()[0]
    try:
        X, codes = load_current_snapshot(data_dir=data_dir, latest_date=latest_date, refresh=False)
        df = X.copy()
        df.insert(0, "stock_code", codes)
        ts = latest_date or date.today().isoformat()
        return df, ts
    except Exception as e:
        logger.warning("load_current_snapshot 不可用，回退 test.parquet: %s", e)
        raw = _fallback_frame_from_test_parquet(data_dir, max_rows=8000, include_date=True)
        section = date.today().isoformat()
        if "date" in raw.columns:
            section = str(pd.Timestamp(raw["date"].max()).date())
            out = raw.drop(columns=["date"])
        else:
            out = raw
        return out, section


def _demo_synthetic_frame(factor_cols: list[str], n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    data = {c: rng.standard_normal(n) for c in factor_cols}
    data["stock_code"] = [f"{i:06d}" for i in range(n)]
    return pd.DataFrame(data)


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data_dir, _, _ = _resolve_backend_paths()
    factor_cols = load_factor_columns(data_dir=data_dir)

    print("=== ModelPredictor 模拟数据 ===")
    demo = _demo_synthetic_frame(factor_cols, n=30)
    for kind in ("lightgbm", "xgboost"):
        try:
            p = ModelPredictor(kind)
        except FileNotFoundError as e:
            print(f"跳过 {kind}: {e}")
            continue
        pred = p.predict(demo)
        print(f"\n[{kind}] predict 前5:\n", pred.head())
        top = p.get_top_stocks(demo, top_n=5, with_contributions=True)
        print(f"[{kind}] get_top_stocks(5):\n", top[["stock_code", "score", "rank"]])

    print("\n=== 截面 Top10（LightGBM；默认 load_current_snapshot，异常或 PREDICTOR_OFFLINE=1 时用 test.parquet）===")
    mp = ModelPredictor("lightgbm")
    snap_df: pd.DataFrame | None = None
    offline = os.environ.get("PREDICTOR_OFFLINE", "").strip().lower() in ("1", "true", "yes")
    if offline:
        try:
            snap_df = _fallback_frame_from_test_parquet(data_dir)
            print(f"PREDICTOR_OFFLINE：使用 test.parquet 前 {len(snap_df)} 行。")
        except Exception as e:
            print("离线样本不可用:", e)
    else:
        try:
            X_snap, codes = load_current_snapshot(data_dir=data_dir, refresh=False)
            snap_df = X_snap.copy()
            snap_df.insert(0, "stock_code", codes)
        except Exception as e:
            print("load_current_snapshot 不可用:", e)
            try:
                snap_df = _fallback_frame_from_test_parquet(data_dir)
                print(f"已改用离线样本 test.parquet 前 {len(snap_df)} 行。")
            except Exception as e2:
                print("离线样本亦不可用:", e2)
    if snap_df is not None:
        top10 = mp.get_top_stocks(snap_df, top_n=10, with_contributions=False)
        print(top10[["stock_code", "score", "rank"]].to_string(index=False))
        gi = mp.get_feature_importance()
        print("全局特征重要性（前5项）:", dict(list(gi.items())[:5]))


if __name__ == "__main__":
    _main()
