"""
XGBoost rank:ndcg 训练与 Optuna 超参搜索（与 LightGBM 共用 data_loader 与 relevance 映射）。

用法::

    python -m src.model_xgboost --trials 20
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import xgboost as xgb
from xgboost.core import XGBoostError

from .data_loader import DATA_OUT_DIR, load_training_data, load_validation_data
from .model_lightgbm import future_return_to_relevance


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "xgboost.pkl"
DEFAULT_IMPORTANCE_PATH = MODELS_DIR / "xgboost_feature_importance.json"
DEFAULT_LOG_PATH = MODELS_DIR / "xgboost_training.log"
DEFAULT_TUNE_LOG_PATH = MODELS_DIR / "xgboost_optuna_trials.jsonl"

RANDOM_STATE = 42
N_OPTUNA_TRIALS = 20
EARLY_STOPPING_ROUNDS = 20
MAX_BOOST_ROUND = 2000


def _setup_file_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("quant_xgboost")
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


def get_base_params() -> dict[str, Any]:
    """
    基础参数（seed=42）。
    eval_metric 使用列表且将 ndcg@10 置于最后，以便与 early_stopping 监控的验证指标一致；
    同时输出 ndcg@5 / ndcg@20 供日志记录。
    """
    return {
        "objective": "rank:ndcg",
        "eval_metric": ["ndcg@5", "ndcg@20", "ndcg@10"],
        "booster": "gbtree",
        "eta": 0.05,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "seed": RANDOM_STATE,
    }


def build_dmats(
    *,
    data_dir: Path = DATA_OUT_DIR,
    fill_missing: bool = True,
) -> tuple[xgb.DMatrix, xgb.DMatrix, list[str], np.ndarray, np.ndarray]:
    """与 LightGBM 相同数据源；group 为各 query 样本数列表。"""
    X_tr, y_tr, g_tr = load_training_data(data_dir=data_dir, fill_missing=fill_missing)
    X_va, y_va, g_va = load_validation_data(data_dir=data_dir, fill_missing=fill_missing)

    if sum(g_tr) != len(X_tr) or sum(g_va) != len(X_va):
        raise ValueError(
            f"group 与样本数不一致: train {sum(g_tr)} vs {len(X_tr)}, val {sum(g_va)} vs {len(X_va)}"
        )

    feat_names = list(X_tr.columns)
    X_tr_m = np.ascontiguousarray(X_tr.to_numpy(dtype=np.float32, copy=True))
    X_va_m = np.ascontiguousarray(X_va.to_numpy(dtype=np.float32, copy=True))

    y_tr_rel = future_return_to_relevance(y_tr, g_tr)
    y_va_rel = future_return_to_relevance(y_va, g_va)

    group_tr = np.asarray(g_tr, dtype=np.uint32)
    group_va = np.asarray(g_va, dtype=np.uint32)

    dtrain = xgb.DMatrix(X_tr_m, label=y_tr_rel, feature_names=feat_names)
    dtrain.set_group(group_tr)
    dval = xgb.DMatrix(X_va_m, label=y_va_rel, feature_names=feat_names)
    dval.set_group(group_va)
    return dtrain, dval, feat_names, y_tr, y_va


def _ndcg_at_best_iteration(evals_result: dict[str, Any], split: str, best_iteration: int) -> dict[str, float]:
    sp = evals_result[split]
    i = int(best_iteration)
    i = max(0, min(i, len(sp["ndcg@10"]) - 1))
    return {
        "ndcg@5": float(sp["ndcg@5"][i]),
        "ndcg@10": float(sp["ndcg@10"][i]),
        "ndcg@20": float(sp["ndcg@20"][i]),
    }


def train_booster(
    params: dict[str, Any],
    dtrain: xgb.DMatrix,
    dval: xgb.DMatrix,
    *,
    num_boost_round: int = MAX_BOOST_ROUND,
    early_stopping_rounds: int = EARLY_STOPPING_ROUNDS,
    verbose_eval: bool | int = False,
) -> tuple[xgb.Booster, dict[str, Any]]:
    """
    evals 顺序：train 在前、val 在后，使早停依据最后一项验证集（XGBoost 约定）。
    """
    evals_result: dict[str, Any] = {}
    bst = xgb.train(
        params,
        dtrain,
        num_boost_round=num_boost_round,
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=early_stopping_rounds,
        verbose_eval=verbose_eval,
        evals_result=evals_result,
    )
    return bst, evals_result


@dataclass
class TuneResult:
    best_params: dict[str, Any]
    best_val_ndcg10: float
    n_trials: int


def tune_xgboost(
    dtrain: xgb.DMatrix,
    dval: xgb.DMatrix,
    *,
    base_params: dict[str, Any] | None = None,
    n_trials: int = N_OPTUNA_TRIALS,
    early_stopping_rounds: int = EARLY_STOPPING_ROUNDS,
    seed: int = RANDOM_STATE,
    trials_log_path: Path | None = DEFAULT_TUNE_LOG_PATH,
    logger: logging.Logger | None = None,
) -> TuneResult:
    """Optuna 最大化验证集 NDCG@10；每 trial 使用 early_stopping_rounds。"""
    base = dict(get_base_params() if base_params is None else base_params)

    def objective(trial: optuna.Trial) -> float:
        params = {
            **base,
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "eta": trial.suggest_float("eta", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 10.0),
        }
        bst, er = train_booster(
            params,
            dtrain,
            dval,
            early_stopping_rounds=early_stopping_rounds,
            verbose_eval=False,
        )
        bi = int(bst.best_iteration)
        score = float(er["val"]["ndcg@10"][bi])
        trial.set_user_attr("best_iteration", bi)
        trial.set_user_attr("val_ndcg@5", float(er["val"]["ndcg@5"][bi]))
        trial.set_user_attr("val_ndcg@20", float(er["val"]["ndcg@20"][bi]))
        if trials_log_path is not None:
            trials_log_path.parent.mkdir(parents=True, exist_ok=True)
            rec = {
                "trial": trial.number,
                "value": score,
                "params": {
                    "max_depth": params["max_depth"],
                    "eta": params["eta"],
                    "subsample": params["subsample"],
                    "colsample_bytree": params["colsample_bytree"],
                    "min_child_weight": params["min_child_weight"],
                },
                "user_attrs": dict(trial.user_attrs),
            }
            with open(trials_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return score

    if trials_log_path is not None and trials_log_path.exists():
        trials_log_path.unlink()

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best = study.best_trial
    best_params = {
        **base,
        "max_depth": best.params["max_depth"],
        "eta": best.params["eta"],
        "subsample": best.params["subsample"],
        "colsample_bytree": best.params["colsample_bytree"],
        "min_child_weight": best.params["min_child_weight"],
    }
    msg = f"Optuna 完成: n_trials={n_trials}, best_val_ndcg@10={best.value:.6f}, best_params={best.params}"
    if logger:
        logger.info(msg)
    else:
        print(msg)

    return TuneResult(best_params=best_params, best_val_ndcg10=float(best.value), n_trials=n_trials)


def save_feature_importance_json(bst: xgb.Booster, feature_names: list[str], path: Path) -> None:
    raw = bst.get_score(importance_type="gain")
    payload = {str(n): float(raw.get(str(n), 0.0)) for n in feature_names}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _save_xgb_model(bst: xgb.Booster, model_path: Path) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        str(model_path.resolve()).encode("ascii")
        bst.save_model(str(model_path.resolve()))
    except (UnicodeEncodeError, OSError, XGBoostError):
        model_path.write_bytes(bst.save_raw())


def train_final_xgboost(
    *,
    data_dir: Path = DATA_OUT_DIR,
    model_path: Path = DEFAULT_MODEL_PATH,
    importance_path: Path = DEFAULT_IMPORTANCE_PATH,
    log_path: Path = DEFAULT_LOG_PATH,
    tune: bool = True,
    n_trials: int = N_OPTUNA_TRIALS,
    fill_missing: bool = True,
) -> tuple[xgb.Booster, dict[str, Any]]:
    logger = _setup_file_logger(log_path)
    logger.info("开始 XGBoost rank:ndcg：加载数据（fill_missing=%s）", fill_missing)
    dtrain, dval, feat_names, _, _ = build_dmats(data_dir=data_dir, fill_missing=fill_missing)

    base = get_base_params()
    if tune:
        logger.info("超参数搜索：%d 次 trial，目标=验证集 NDCG@10，early_stopping=%d", n_trials, EARLY_STOPPING_ROUNDS)
        tune_res = tune_xgboost(
            dtrain,
            dval,
            base_params=base,
            n_trials=n_trials,
            logger=logger,
        )
        final_params = tune_res.best_params
        logger.info("最优超参: %s", final_params)
        with open(MODELS_DIR / "xgboost_best_params.json", "w", encoding="utf-8") as f:
            json.dump(
                {k: v for k, v in final_params.items() if isinstance(v, (int, float, str, bool, list))},
                f,
                indent=2,
            )
    else:
        final_params = base
        logger.info("跳过调优，使用基础参数")

    logger.info("使用最终参数训练并早停（early_stopping_rounds=%d）", EARLY_STOPPING_ROUNDS)
    bst, er = train_booster(
        final_params,
        dtrain,
        dval,
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        verbose_eval=50,
    )
    bi = int(bst.best_iteration)
    val_m = _ndcg_at_best_iteration(er, "val", bi)
    tr_m = _ndcg_at_best_iteration(er, "train", bi)
    logger.info(
        "验证集 NDCG: @5=%.6f @10=%.6f @20=%.6f | 训练集 NDCG: @5=%.6f @10=%.6f @20=%.6f | best_iteration=%d",
        val_m["ndcg@5"],
        val_m["ndcg@10"],
        val_m["ndcg@20"],
        tr_m["ndcg@5"],
        tr_m["ndcg@10"],
        tr_m["ndcg@20"],
        bi,
    )

    _save_xgb_model(bst, model_path)
    logger.info("模型已保存: %s", model_path)

    save_feature_importance_json(bst, feat_names, importance_path)
    logger.info("特征重要性已保存: %s", importance_path)

    meta = {
        "val_ndcg": val_m,
        "train_ndcg": tr_m,
        "best_iteration": bi,
        "feature_count": len(feat_names),
        "features": feat_names,
    }
    with open(MODELS_DIR / "xgboost_metrics.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return bst, final_params


def load_xgboost_model(path: Path | None = None) -> xgb.Booster:
    p = path or DEFAULT_MODEL_PATH
    if not p.exists():
        raise FileNotFoundError(str(p))
    try:
        return xgb.Booster(model_file=str(p.resolve()))
    except XGBoostError:
        return xgb.Booster(model_file=p.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description="Train XGBoost rank:ndcg with optional Optuna tuning.")
    parser.add_argument("--trials", type=int, default=N_OPTUNA_TRIALS, help="Optuna trials (default 20)")
    parser.add_argument("--no-tune", action="store_true", help="Skip hyperparameter search")
    args = parser.parse_args()
    train_final_xgboost(tune=not args.no_tune, n_trials=max(1, args.trials))


if __name__ == "__main__":
    main()
