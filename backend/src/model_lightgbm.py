"""
LightGBM LambdaRank 训练与 Optuna 超参搜索。

用法（在 backend 目录且 PYTHONPATH 含当前项目根）::

    python -m src.model_lightgbm --trials 20

说明：lambdarank 需离散 relevance 标签，本模块将截面 future_return 映射为 0–30；
验证集 NDCG 高度依赖标签与因子质量，未必总能超过 0.5。
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lightgbm as lgb
from lightgbm.basic import LightGBMError
import numpy as np
import optuna
from .data_loader import DATA_OUT_DIR, load_training_data, load_validation_data


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "lightgbm.pkl"
DEFAULT_IMPORTANCE_PATH = MODELS_DIR / "lightgbm_feature_importance.json"
DEFAULT_LOG_PATH = MODELS_DIR / "lightgbm_training.log"
DEFAULT_TUNE_LOG_PATH = MODELS_DIR / "lightgbm_optuna_trials.jsonl"

RANDOM_STATE = 42
N_OPTUNA_TRIALS = 20
EARLY_STOPPING_ROUNDS = 20
MAX_BOOST_ROUND = 2000


def _setup_file_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("quant_lightgbm")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def future_return_to_relevance(y: np.ndarray, group_sizes: list[int], max_label: int = 30) -> np.ndarray:
    """
    将连续 future_return 按 query 内分位映射为整数 relevance，满足 LightGBM lambdarank 标签要求（0..max_label）。
    同组内收益越高，relevance 越大。
    """
    y = np.asarray(y, dtype=np.float64)
    out = np.zeros(len(y), dtype=np.int32)
    pos = 0
    for gsz in group_sizes:
        if gsz <= 0:
            continue
        sl = slice(pos, pos + gsz)
        seg = y[sl]
        if gsz == 1:
            out[sl] = max_label // 2
        else:
            order = np.argsort(-seg, kind="mergesort")
            rank = np.empty(gsz, dtype=np.int64)
            rank[order] = np.arange(gsz)
            rel = (max_label * (1.0 - rank / (gsz - 1.0))).round().astype(np.int32)
            out[sl] = np.clip(rel, 0, max_label)
        pos += gsz
    return out


def get_base_params() -> dict[str, Any]:
    """训练基础参数（固定随机种子 42，可复现）。"""
    return {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_eval_at": [5, 10, 20],
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "seed": RANDOM_STATE,
        "bagging_seed": RANDOM_STATE,
        "feature_fraction_seed": RANDOM_STATE,
        "deterministic": True,
        # Optuna 会改变 min_child_samples，需关闭预过滤以免 C API 报错
        "feature_pre_filter": False,
    }


def build_datasets(
    *,
    data_dir: Path = DATA_OUT_DIR,
    fill_missing: bool = True,
) -> tuple[lgb.Dataset, lgb.Dataset, list[str], np.ndarray, np.ndarray]:
    """
    从 data_loader 构建带 group 的 lgb.Dataset（训练 / 验证）。
    返回 (train_set, valid_set, feature_names, y_train_raw, y_val_raw)。
    """
    X_tr, y_tr, g_tr = load_training_data(data_dir=data_dir, fill_missing=fill_missing)
    X_va, y_va, g_va = load_validation_data(data_dir=data_dir, fill_missing=fill_missing)

    if sum(g_tr) != len(X_tr) or sum(g_va) != len(X_va):
        raise ValueError(
            f"group 大小之和与样本数不一致: train {sum(g_tr)} vs {len(X_tr)}, "
            f"val {sum(g_va)} vs {len(X_va)}"
        )

    feat_names = list(X_tr.columns)
    X_tr_m = np.ascontiguousarray(X_tr.to_numpy(dtype=np.float32, copy=True))
    X_va_m = np.ascontiguousarray(X_va.to_numpy(dtype=np.float32, copy=True))

    y_tr_rel = future_return_to_relevance(y_tr, g_tr)
    y_va_rel = future_return_to_relevance(y_va, g_va)

    train_set = lgb.Dataset(
        X_tr_m,
        label=y_tr_rel,
        group=g_tr,
        feature_name=feat_names,
        free_raw_data=False,
    )
    valid_set = lgb.Dataset(
        X_va_m,
        label=y_va_rel,
        group=g_va,
        feature_name=feat_names,
        reference=train_set,
        free_raw_data=False,
    )
    return train_set, valid_set, feat_names, y_tr, y_va


def _ndcg_from_best_score(bst: lgb.Booster, split: str) -> dict[str, float]:
    od = bst.best_score.get(split, {})
    return {
        "ndcg@5": float(od.get("ndcg@5", float("nan"))),
        "ndcg@10": float(od.get("ndcg@10", float("nan"))),
        "ndcg@20": float(od.get("ndcg@20", float("nan"))),
    }


def train_booster(
    params: dict[str, Any],
    train_set: lgb.Dataset,
    valid_set: lgb.Dataset,
    *,
    num_boost_round: int = MAX_BOOST_ROUND,
    early_stopping_rounds: int = EARLY_STOPPING_ROUNDS,
    log_evaluation_period: int = 0,
) -> lgb.Booster:
    """验证集优先用于早停；同时记录训练集 NDCG。"""
    callbacks = [
        lgb.early_stopping(early_stopping_rounds, first_metric_only=True, verbose=False),
        lgb.log_evaluation(log_evaluation_period),
    ]
    return lgb.train(
        params,
        train_set,
        num_boost_round=num_boost_round,
        valid_sets=[valid_set, train_set],
        valid_names=["val", "train"],
        callbacks=callbacks,
    )


@dataclass
class TuneResult:
    best_params: dict[str, Any]
    best_val_ndcg10: float
    n_trials: int


def tune_lightgbm(
    train_set: lgb.Dataset,
    valid_set: lgb.Dataset,
    *,
    base_params: dict[str, Any] | None = None,
    n_trials: int = N_OPTUNA_TRIALS,
    early_stopping_rounds: int = EARLY_STOPPING_ROUNDS,
    seed: int = RANDOM_STATE,
    trials_log_path: Path | None = DEFAULT_TUNE_LOG_PATH,
    logger: logging.Logger | None = None,
) -> TuneResult:
    """
    Optuna 超参搜索：最大化验证集 ndcg@10；每 trial 使用 early_stopping_rounds 早停。
    搜索空间：num_leaves, learning_rate, min_child_samples, feature_fraction。
    """
    base = dict(get_base_params() if base_params is None else base_params)

    def objective(trial: optuna.Trial) -> float:
        params = {
            **base,
            "num_leaves": trial.suggest_int("num_leaves", 10, 255),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
        }
        bst = train_booster(
            params,
            train_set,
            valid_set,
            early_stopping_rounds=early_stopping_rounds,
            log_evaluation_period=0,
        )
        score = float(bst.best_score["val"]["ndcg@10"])
        trial.set_user_attr("best_iteration", int(bst.best_iteration))
        trial.set_user_attr("val_ndcg@5", float(bst.best_score["val"]["ndcg@5"]))
        trial.set_user_attr("val_ndcg@20", float(bst.best_score["val"]["ndcg@20"]))
        if trials_log_path is not None:
            trials_log_path.parent.mkdir(parents=True, exist_ok=True)
            rec = {
                "trial": trial.number,
                "value": score,
                "params": {
                    "num_leaves": params["num_leaves"],
                    "learning_rate": params["learning_rate"],
                    "min_child_samples": params["min_child_samples"],
                    "feature_fraction": params["feature_fraction"],
                },
                "user_attrs": dict(trial.user_attrs),
            }
            with open(trials_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return score

    if trials_log_path is not None and trials_log_path.exists():
        trials_log_path.unlink()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=seed),
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best = study.best_trial
    best_params = {
        **base,
        "num_leaves": best.params["num_leaves"],
        "learning_rate": best.params["learning_rate"],
        "min_child_samples": best.params["min_child_samples"],
        "feature_fraction": best.params["feature_fraction"],
    }
    msg = (
        f"Optuna 完成: n_trials={n_trials}, best_val_ndcg@10={best.value:.6f}, "
        f"best_params={best.params}"
    )
    if logger:
        logger.info(msg)
    else:
        print(msg)

    return TuneResult(best_params=best_params, best_val_ndcg10=float(best.value), n_trials=n_trials)


def save_feature_importance_json(bst: lgb.Booster, feature_names: list[str], path: Path) -> None:
    imp = bst.feature_importance(importance_type="gain")
    arr = np.asarray(imp, dtype=float)
    payload = {str(n): float(v) for n, v in zip(feature_names, arr)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def train_final_lightgbm(
    *,
    data_dir: Path = DATA_OUT_DIR,
    model_path: Path = DEFAULT_MODEL_PATH,
    importance_path: Path = DEFAULT_IMPORTANCE_PATH,
    log_path: Path = DEFAULT_LOG_PATH,
    tune: bool = True,
    n_trials: int = N_OPTUNA_TRIALS,
    fill_missing: bool = True,
) -> tuple[lgb.Booster, dict[str, Any]]:
    """
    可选 Optuna 调优后，用最佳参数在全量训练流程上训练并保存模型与特征重要性。
    """
    logger = _setup_file_logger(log_path)
    logger.info("开始 LightGBM LambdaRank：加载数据（fill_missing=%s）", fill_missing)
    train_set, valid_set, feat_names, _y_tr, _y_va = build_datasets(data_dir=data_dir, fill_missing=fill_missing)

    base = get_base_params()
    if tune:
        logger.info("超参数搜索：%d 次 trial，目标=验证集 NDCG@10，early_stopping=%d", n_trials, EARLY_STOPPING_ROUNDS)
        tune_res = tune_lightgbm(
            train_set,
            valid_set,
            base_params=base,
            n_trials=n_trials,
            logger=logger,
        )
        final_params = tune_res.best_params
        logger.info("最优超参: %s", final_params)
        with open(MODELS_DIR / "lightgbm_best_params.json", "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in final_params.items() if isinstance(v, (int, float, str, bool, list))}, f, indent=2)
    else:
        final_params = base
        logger.info("跳过调优，使用基础参数")

    logger.info("使用最终参数训练并早停（early_stopping_rounds=%d）", EARLY_STOPPING_ROUNDS)
    bst = train_booster(
        final_params,
        train_set,
        valid_set,
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        log_evaluation_period=50,
    )

    val_m = _ndcg_from_best_score(bst, "val")
    tr_m = _ndcg_from_best_score(bst, "train")
    logger.info(
        "验证集 NDCG: @5=%.6f @10=%.6f @20=%.6f | 训练集 NDCG: @5=%.6f @10=%.6f @20=%.6f | best_iteration=%d",
        val_m["ndcg@5"],
        val_m["ndcg@10"],
        val_m["ndcg@20"],
        tr_m["ndcg@5"],
        tr_m["ndcg@10"],
        tr_m["ndcg@20"],
        bst.best_iteration,
    )

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        str(model_path.resolve()).encode("ascii")
        bst.save_model(str(model_path.resolve()))
    except (UnicodeEncodeError, LightGBMError):
        # 非 ASCII 路径或 C API 写盘失败时，使用与 save_model 等价的文本格式写入
        model_path.write_text(bst.model_to_string(), encoding="utf-8")
    logger.info("模型已保存: %s", model_path)

    save_feature_importance_json(bst, feat_names, importance_path)
    logger.info("特征重要性已保存: %s", importance_path)

    meta = {
        "val_ndcg": val_m,
        "train_ndcg": tr_m,
        "best_iteration": int(bst.best_iteration),
        "feature_count": len(feat_names),
        "features": feat_names,
    }
    with open(MODELS_DIR / "lightgbm_metrics.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return bst, final_params


def load_lightgbm_model(path: Path | None = None) -> lgb.Booster:
    p = path or DEFAULT_MODEL_PATH
    if not p.exists():
        raise FileNotFoundError(str(p))
    try:
        str(p.resolve()).encode("ascii")
        return lgb.Booster(model_file=str(p.resolve()))
    except (UnicodeEncodeError, LightGBMError):
        return lgb.Booster(model_str=p.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LightGBM LambdaRank with optional Optuna tuning.")
    parser.add_argument("--trials", type=int, default=N_OPTUNA_TRIALS, help="Optuna trials (default 20)")
    parser.add_argument("--no-tune", action="store_true", help="Skip hyperparameter search, use base params only")
    args = parser.parse_args()
    train_final_lightgbm(tune=not args.no_tune, n_trials=max(1, args.trials))


if __name__ == "__main__":
    main()
