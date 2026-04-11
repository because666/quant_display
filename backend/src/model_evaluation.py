"""
测试集上评估 LightGBM / XGBoost 排序效果：NDCG、MAP、按截面 NDCG@10 曲线、特征重要性对比。

用法（在 backend 目录）::

    python -m src.model_evaluation
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .data_loader import DATA_OUT_DIR, load_test_data
from .model_lightgbm import future_return_to_relevance, load_lightgbm_model
from .model_xgboost import load_xgboost_model

import lightgbm as lgb
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_LGB_PATH = MODELS_DIR / "lightgbm.pkl"
DEFAULT_XGB_PATH = MODELS_DIR / "xgboost.pkl"
METRICS_JSON = MODELS_DIR / "evaluation_metrics.json"
NDCG_CURVE_PNG = MODELS_DIR / "ndcg_curve.png"
NDCG_CURVE_JSON = MODELS_DIR / "ndcg_curve.json"
FEATURE_CMP_PNG = MODELS_DIR / "feature_importance_compare.png"
LGB_IMP_JSON = MODELS_DIR / "lightgbm_feature_importance.json"
XGB_IMP_JSON = MODELS_DIR / "xgboost_feature_importance.json"

logger = logging.getLogger(__name__)


def _configure_matplotlib_fonts() -> None:
    """避免中文标题在默认 DejaVu 下无法显示。"""
    if sys.platform == "win32":
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False


def _rank_order_desc(score: np.ndarray) -> np.ndarray:
    """按预测分降序的稳定排序（同分按原始下标打破平局，避免随机噪声）。"""
    s = np.asarray(score, dtype=np.float64)
    n = s.size
    return np.lexsort((np.arange(n, dtype=np.int64), -s))


def _dcg_from_relevance_sorted(rels_sorted_high_first: np.ndarray, k: int) -> float:
    rels = np.asarray(rels_sorted_high_first, dtype=np.float64)[:k]
    if rels.size == 0:
        return 0.0
    gains = np.power(2.0, rels) - 1.0
    discounts = np.log2(np.arange(2, rels.size + 2, dtype=np.float64))
    return float(np.sum(gains / discounts))


def calculate_ndcg(
    y_true: np.ndarray,
    y_score: np.ndarray,
    group: list[int],
    k: int,
) -> float:
    """
    按 query 组计算 NDCG@K，再对组取平均。
    y_true 为与训练一致的整数 relevance（如 future_return_to_relevance 输出）。
    """
    y_true = np.asarray(y_true, dtype=np.float64).ravel()
    y_score = np.asarray(y_score, dtype=np.float64).ravel()

    pos = 0
    ndcgs: list[float] = []
    for gsz in group:
        if gsz <= 0:
            continue
        sl = slice(pos, pos + gsz)
        rel = np.asarray(y_true[sl], dtype=np.float64)
        score = y_score[sl]
        kk = min(k, gsz)
        order = _rank_order_desc(score)
        sorted_rel = rel[order]
        ideal = _rank_order_desc(rel)
        ideal_rel = rel[ideal]
        dcg = _dcg_from_relevance_sorted(sorted_rel, kk)
        idcg = _dcg_from_relevance_sorted(ideal_rel, kk)
        if idcg <= 0:
            ndcgs.append(0.0)
        else:
            ndcgs.append(dcg / idcg)
        pos += gsz
    if not ndcgs:
        return 0.0
    return float(np.mean(ndcgs))


def _average_precision_binary(y_true_binary: np.ndarray, y_score: np.ndarray) -> float:
    """单 query：二值相关下的 AP。"""
    rel = np.asarray(y_true_binary, dtype=np.int32)
    score = np.asarray(y_score, dtype=np.float64)
    n_rel = int(np.sum(rel))
    if n_rel == 0:
        return 0.0
    order = _rank_order_desc(score)
    rel_sorted = rel[order]
    precisions = []
    hits = 0
    for i, r in enumerate(rel_sorted, start=1):
        if r:
            hits += 1
            precisions.append(hits / i)
    return float(np.sum(precisions) / n_rel) if precisions else 0.0


def calculate_map(
    y_true: np.ndarray,
    y_score: np.ndarray,
    group: list[int],
) -> float:
    """
    平均精度均值：每组内将未来收益高于截面中位数的样本视为相关，再算 AP 并对 query 平均。
    """
    y_true = np.asarray(y_true, dtype=np.float64).ravel()
    y_score = np.asarray(y_score, dtype=np.float64).ravel()

    pos = 0
    aps: list[float] = []
    for gsz in group:
        if gsz <= 0:
            continue
        sl = slice(pos, pos + gsz)
        fr = y_true[sl]
        sc = y_score[sl]
        med = np.median(fr)
        binary = (fr > med).astype(np.int32)
        if np.sum(binary) == 0:
            # 全相等时退化为前一半为相关
            thr = np.sort(fr)[max(0, gsz // 2 - 1)]
            binary = (fr >= thr).astype(np.int32)
        aps.append(_average_precision_binary(binary, sc))
        pos += gsz
    return float(np.mean(aps)) if aps else 0.0


def _load_test_section_dates(data_dir: Path, groups: list[int]) -> list[str]:
    """与 load_test_data 行序一致：按 date、stock_code 排序后的各截面日期（每组一个日期字符串）。"""
    path = Path(data_dir) / "test.parquet"
    if not path.exists():
        raise FileNotFoundError(f"test.parquet not found: {path}")
    df = pd.read_parquet(path, columns=["date", "stock_code"])
    df = df.sort_values(["date", "stock_code"]).reset_index(drop=True)
    if sum(groups) != len(df):
        raise ValueError(f"group 总和 {sum(groups)} 与 test 行数 {len(df)} 不一致")
    dates: list[str] = []
    pos = 0
    for gsz in groups:
        if gsz <= 0:
            continue
        d = df.iloc[pos]["date"]
        if hasattr(d, "strftime"):
            dates.append(pd.Timestamp(d).strftime("%Y-%m-%d"))
        else:
            dates.append(str(d)[:10])
        pos += gsz
    return dates


def _ndcg_per_group_at_k(
    y_rel: np.ndarray,
    y_score: np.ndarray,
    group: list[int],
    k: int,
) -> list[float]:
    """每个 query 一个 NDCG@k（用于按截面曲线）。"""
    y_rel = np.asarray(y_rel, dtype=np.float64).ravel()
    y_score = np.asarray(y_score, dtype=np.float64).ravel()
    out: list[float] = []
    pos = 0
    for gsz in group:
        if gsz <= 0:
            continue
        sl = slice(pos, pos + gsz)
        rel = np.asarray(y_rel[sl], dtype=np.float64)
        score = y_score[sl]
        kk = min(k, gsz)
        order = _rank_order_desc(score)
        sorted_rel = rel[order]
        ideal = _rank_order_desc(rel)
        ideal_rel = rel[ideal]
        dcg = _dcg_from_relevance_sorted(sorted_rel, kk)
        idcg = _dcg_from_relevance_sorted(ideal_rel, kk)
        out.append(0.0 if idcg <= 0 else dcg / idcg)
        pos += gsz
    return out


def _predict_lightgbm(bst: lgb.Booster, X: pd.DataFrame) -> np.ndarray:
    X_m = np.ascontiguousarray(X.to_numpy(dtype=np.float32, copy=True))
    return bst.predict(X_m)


def _predict_xgboost(bst: xgb.Booster, X: pd.DataFrame, feature_names: list[str]) -> np.ndarray:
    X_m = np.ascontiguousarray(X.to_numpy(dtype=np.float32, copy=True))
    d = xgb.DMatrix(X_m, feature_names=feature_names)
    return bst.predict(d)


def _plot_ndcg_curve(
    dates: list[str],
    lgb_ndcg: list[float],
    xgb_ndcg: list[float],
    png_path: Path,
) -> None:
    _configure_matplotlib_fonts()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    x = np.arange(len(dates))
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(x, lgb_ndcg, label="LightGBM", linewidth=1.2, alpha=0.9)
    ax.plot(x, xgb_ndcg, label="XGBoost", linewidth=1.2, alpha=0.9)
    ax.set_ylabel("NDCG@10")
    ax.set_xlabel("测试截面（按时间顺序）")
    ax.set_title("各测试截面 NDCG@10")
    n = len(dates)
    if n > 30:
        step = max(1, n // 20)
        tick_idx = list(range(0, n, step))
        ax.set_xticks(tick_idx)
        ax.set_xticklabels([dates[i] for i in tick_idx], rotation=45, ha="right", fontsize=8)
    else:
        ax.set_xticks(x)
        ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)


def _plot_feature_importance_compare(
    lgb_imp: dict[str, float],
    xgb_imp: dict[str, float],
    top_n: int,
    png_path: Path,
) -> None:
    names = sorted(set(lgb_imp.keys()) | set(xgb_imp.keys()))
    lgb_vals = np.array([lgb_imp.get(n, 0.0) for n in names], dtype=np.float64)
    xgb_vals = np.array([xgb_imp.get(n, 0.0) for n in names], dtype=np.float64)
    # 按两者之和排序取 top
    total = lgb_vals + xgb_vals
    order = np.argsort(-total)[:top_n]
    names_t = [names[i] for i in order]
    lgb_t = lgb_vals[order]
    xgb_t = xgb_vals[order]

    def _norm(v: np.ndarray) -> np.ndarray:
        s = v.sum()
        return v / s if s > 0 else v

    lgb_n = _norm(lgb_t)
    xgb_n = _norm(xgb_t)

    y = np.arange(len(names_t))
    h = 0.35
    _configure_matplotlib_fonts()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(names_t))))
    ax.barh(y - h / 2, lgb_n, h, label="LightGBM", alpha=0.85)
    ax.barh(y + h / 2, xgb_n, h, label="XGBoost", alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(names_t, fontsize=9)
    ax.set_xlabel("归一化 gain 重要性（组内）")
    ax.set_title("特征重要性对比（Top %d）" % top_n)
    ax.legend(loc="lower right")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)


def run_evaluation(
    *,
    data_dir: Path = DATA_OUT_DIR,
    lgb_path: Path = DEFAULT_LGB_PATH,
    xgb_path: Path = DEFAULT_XGB_PATH,
    fill_missing: bool = True,
) -> dict[str, Any]:
    X_test, y_test, groups_test = load_test_data(data_dir=data_dir, fill_missing=fill_missing)
    y_rel = future_return_to_relevance(y_test, groups_test)

    print("加载模型…")
    bst_lgb = load_lightgbm_model(lgb_path)
    bst_xgb = load_xgboost_model(xgb_path)
    feat_names = list(X_test.columns)

    pred_lgb = _predict_lightgbm(bst_lgb, X_test)
    pred_xgb = _predict_xgboost(bst_xgb, X_test, feat_names)

    ks = (5, 10, 20)
    metrics: dict[str, Any] = {
        "lightgbm": {},
        "xgboost": {},
        "settings": {
            "fill_missing": fill_missing,
            "k_list": list(ks),
            "test_rows": int(len(X_test)),
            "num_queries": int(len(groups_test)),
        },
    }

    for name, pred in [("lightgbm", pred_lgb), ("xgboost", pred_xgb)]:
        m: dict[str, float] = {}
        for kk in ks:
            key = f"ndcg@{kk}"
            m[key] = calculate_ndcg(y_rel, pred, groups_test, kk)
        m["map"] = calculate_map(y_test, pred, groups_test)
        metrics[name] = m
        print(f"\n[{name}]")
        for kk in ks:
            print(f"  NDCG@{kk}: {m[f'ndcg@{kk}']:.6f}")
        print(f"  MAP: {m['map']:.6f}")

    section_dates = _load_test_section_dates(data_dir, groups_test)
    lgb_curve = _ndcg_per_group_at_k(y_rel, pred_lgb, groups_test, 10)
    xgb_curve = _ndcg_per_group_at_k(y_rel, pred_xgb, groups_test, 10)

    curve_payload = {
        "dates": section_dates,
        "lightgbm_ndcg10": lgb_curve,
        "xgboost_ndcg10": xgb_curve,
    }
    NDCG_CURVE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(NDCG_CURVE_JSON, "w", encoding="utf-8") as f:
        json.dump(curve_payload, f, ensure_ascii=False, indent=2)

    _plot_ndcg_curve(section_dates, lgb_curve, xgb_curve, NDCG_CURVE_PNG)
    print(f"\nNDCG 曲线已保存: {NDCG_CURVE_PNG} / {NDCG_CURVE_JSON}")

    with open(LGB_IMP_JSON, encoding="utf-8") as f:
        lgb_imp = json.load(f)
    with open(XGB_IMP_JSON, encoding="utf-8") as f:
        xgb_imp = json.load(f)
    top_n = min(20, max(len(lgb_imp), len(xgb_imp)))
    _plot_feature_importance_compare(lgb_imp, xgb_imp, top_n, FEATURE_CMP_PNG)
    print(f"特征重要性对比图: {FEATURE_CMP_PNG}")

    def _web_rel(p: Path) -> str:
        return str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")

    metrics["ndcg_curve"] = {
        "png": _web_rel(NDCG_CURVE_PNG),
        "json": _web_rel(NDCG_CURVE_JSON),
    }
    metrics["feature_importance_compare_png"] = _web_rel(FEATURE_CMP_PNG)

    METRICS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"\n指标已写入: {METRICS_JSON}")

    return metrics


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Evaluate LightGBM and XGBoost on test set.")
    parser.add_argument("--data-dir", type=str, default=str(DATA_OUT_DIR))
    parser.add_argument("--lgb-model", type=str, default=str(DEFAULT_LGB_PATH))
    parser.add_argument("--xgb-model", type=str, default=str(DEFAULT_XGB_PATH))
    args = parser.parse_args()
    run_evaluation(
        data_dir=Path(args.data_dir),
        lgb_path=Path(args.lgb_model),
        xgb_path=Path(args.xgb_model),
    )


if __name__ == "__main__":
    main()
