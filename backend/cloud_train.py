"""
本地模型训练脚本 - 优化版
修复了之前模型训练过快（早停过早）的问题，增加了Optuna调参

使用方法:
    python cloud_train.py                    # 默认参数训练
    python cloud_train.py --trials 50        # Optuna调参50轮
    python cloud_train.py --gpu              # 使用GPU加速

输出:
    - models/lightgbm.txt
    - models/xgboost.json
    - models/lightgbm_metrics.json
    - models/xgboost_metrics.json
    - models/evaluation_metrics.json
"""
import sys
import os
import json
import pickle
import argparse
import time
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import lightgbm as lgb
import xgboost as xgb
import optuna
from optuna.samplers import TPESampler

optuna.logging.set_verbosity(optuna.logging.WARNING)

DATA_DIR = Path("data")
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

RANDOM_STATE = 42


def load_data():
    """加载训练数据，并自动筛选低相关性因子"""
    print("加载数据...")
    
    train_df = pd.read_parquet(DATA_DIR / "train.parquet")
    val_df = pd.read_parquet(DATA_DIR / "val.parquet")
    test_df = pd.read_parquet(DATA_DIR / "test.parquet")
    
    with open(DATA_DIR / "factor_columns.pkl", "rb") as f:
        factor_cols = pickle.load(f)
    
    print(f"  训练集: {len(train_df):,} 行")
    print(f"  验证集: {len(val_df):,} 行")
    print(f"  测试集: {len(test_df):,} 行")
    print(f"  原始因子数: {len(factor_cols)}")
    
    factor_cols = _select_low_corr_factors(train_df, factor_cols, max_corr=0.75, min_factors=40)
    print(f"  筛选后因子数: {len(factor_cols)}")
    
    with open(DATA_DIR / "factor_columns.pkl", "wb") as f:
        pickle.dump(factor_cols, f)
    
    return train_df, val_df, test_df, factor_cols


def _select_low_corr_factors(df, factor_cols, max_corr=0.75, min_factors=40):
    """从因子列表中筛选低相关性因子
    
    算法：按平均相关性排序，逐步剔除高相关因子中平均相关性更高的那个
    """
    available = [c for c in factor_cols if c in df.columns and df[c].notna().any()]
    if len(available) <= min_factors:
        return available
    
    sample_dates = df["date"].unique()
    sample_date = sample_dates[len(sample_dates) // 2]
    sample = df[df["date"] == sample_date][available].copy()
    
    corr = sample.corr().abs()
    
    mean_corr = {}
    for c in available:
        mean_corr[c] = float(corr[c].drop(c).mean())
    
    keep = list(available)
    while len(keep) > min_factors:
        corr_sub = corr.loc[keep, keep]
        upper = corr_sub.where(np.triu(np.ones_like(corr_sub, dtype=bool), k=1))
        high_pairs = upper.stack()
        high_pairs = high_pairs[high_pairs > max_corr]
        
        if high_pairs.empty:
            break
        
        involved = set()
        for (a, b) in high_pairs.index:
            involved.add(a)
            involved.add(b)
        
        worst = max(involved, key=lambda x: mean_corr.get(x, 0))
        keep.remove(worst)
    
    print(f"  低相关筛选: {len(available)} -> {len(keep)} 因子")
    
    pair_corr = corr.loc[keep, keep].values
    mask = ~np.eye(len(keep), dtype=bool)
    print(f"  筛选后平均绝对相关: {np.nanmean(pair_corr[mask]):.4f}")
    print(f"  筛选后最大绝对相关: {np.nanmax(pair_corr[mask]):.4f}")
    
    return keep


def prepare_ranking_data(df, factor_cols):
    """准备排序学习训练数据"""
    df = df.dropna(subset=["future_return_1w"])
    df = df[df["future_return_1w"].abs() < 1.0]
    
    X = df[factor_cols].fillna(0).values
    y = df["future_return_1w"].values
    dates = df["date"].values
    unique_dates = np.unique(dates)
    groups = [int(np.sum(dates == d)) for d in unique_dates]
    
    return X, y, groups, unique_dates


def to_relevance(y, groups, max_label=5):
    """将连续收益率转换为排序相关性标签（0~max_label）
    
    使用分位数分组而非简单排名，减少极端值影响
    max_label=5 表示5级相关性（0,1,2,3,4,5），适合排序学习
    """
    out = np.zeros(len(y), dtype=np.int32)
    pos = 0
    for g in groups:
        if g <= 0:
            continue
        sl = slice(pos, pos + g)
        seg = y[sl]
        if g == 1:
            out[sl] = max_label // 2
        else:
            percentiles = np.percentile(seg, [20, 40, 60, 80])
            for i in range(g):
                if seg[i] >= percentiles[3]:
                    out[pos + i] = max_label
                elif seg[i] >= percentiles[2]:
                    out[pos + i] = max_label * 3 // 4
                elif seg[i] >= percentiles[1]:
                    out[pos + i] = max_label // 2
                elif seg[i] >= percentiles[0]:
                    out[pos + i] = max_label // 4
                else:
                    out[pos + i] = 0
        pos += g
    return out


def train_lightgbm_optuna(X_train, y_train, groups_train, X_val, y_val, groups_val, factor_cols, n_trials=30):
    """使用Optuna调参训练LightGBM LambdaRank模型"""
    print("\n" + "=" * 60)
    print("训练 LightGBM LambdaRank 模型（Optuna调参）")
    print("=" * 60)
    
    train_label = to_relevance(y_train, groups_train)
    val_label = to_relevance(y_val, groups_val)
    
    train_data = lgb.Dataset(X_train, label=train_label, group=groups_train, feature_name=factor_cols, free_raw_data=False)
    val_data = lgb.Dataset(X_val, label=val_label, group=groups_val, reference=train_data, feature_name=factor_cols, free_raw_data=False)
    
    def objective(trial):
        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [5, 10, 20],
            "boosting_type": "gbdt",
            "num_leaves": trial.suggest_int("num_leaves", 15, 127),
            "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.05, log=True),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 0.9),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 0.9),
            "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
            "min_child_samples": trial.suggest_int("min_child_samples", 50, 500),
            "lambda_l1": trial.suggest_float("lambda_l1", 1e-4, 10.0, log=True),
            "lambda_l2": trial.suggest_float("lambda_l2", 1e-4, 10.0, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "min_gain_to_split": trial.suggest_float("min_gain_to_split", 1e-4, 1.0, log=True),
            "verbose": -1,
            "seed": RANDOM_STATE,
            "feature_pre_filter": False,
        }
        
        model = lgb.train(
            params,
            train_data,
            num_boost_round=3000,
            valid_sets=[val_data],
            callbacks=[
                lgb.early_stopping(stopping_rounds=100),
                lgb.log_evaluation(period=0)
            ]
        )
        
        val_pred = model.predict(X_val)
        from sklearn.metrics import ndcg_score
        ndcg_10 = ndcg_score([val_label], [val_pred], k=10)
        return ndcg_10
    
    print(f"  开始Optuna调参，共{n_trials}轮...")
    t0 = time.time()
    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_STATE))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    print(f"  Optuna调参完成，耗时 {time.time()-t0:.1f}s")
    print(f"  最佳NDCG@10: {study.best_value:.4f}")
    print(f"  最佳参数: {json.dumps(study.best_params, indent=2)}")
    
    best_params = study.best_params.copy()
    best_params.update({
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_eval_at": [5, 10, 20],
        "boosting_type": "gbdt",
        "verbose": -1,
        "seed": RANDOM_STATE,
        "feature_pre_filter": False,
    })
    
    with open(MODELS_DIR / "lightgbm_best_params.json", "w") as f:
        json.dump({k: v for k, v in best_params.items()}, f, indent=2, default=str)
    
    print("\n  使用最佳参数重新训练最终模型...")
    final_model = lgb.train(
        best_params,
        train_data,
        num_boost_round=5000,
        valid_sets=[val_data],
        callbacks=[
            lgb.early_stopping(stopping_rounds=150),
            lgb.log_evaluation(period=50)
        ]
    )
    
    print(f"  最终模型 best_iteration: {final_model.best_iteration}")
    
    val_pred = final_model.predict(X_val)
    from sklearn.metrics import ndcg_score
    ndcg_5 = ndcg_score([val_label], [val_pred], k=5)
    ndcg_10 = ndcg_score([val_label], [val_pred], k=10)
    ndcg_20 = ndcg_score([val_label], [val_pred], k=20)
    
    metrics = {
        "val_ndcg": {
            "ndcg@5": float(ndcg_5),
            "ndcg@10": float(ndcg_10),
            "ndcg@20": float(ndcg_20)
        },
        "best_iteration": int(final_model.best_iteration),
        "optuna_best_ndcg10": float(study.best_value),
        "feature_count": len(factor_cols),
        "features": factor_cols
    }
    
    final_model.save_model(str(MODELS_DIR / "lightgbm.txt"))
    
    importance = {k: int(v) for k, v in zip(factor_cols, final_model.feature_importance())}
    with open(MODELS_DIR / "lightgbm_feature_importance.json", "w") as f:
        json.dump(importance, f, indent=2)
    
    with open(MODELS_DIR / "lightgbm_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"  LightGBM完成! NDCG@5={ndcg_5:.4f}, NDCG@10={ndcg_10:.4f}, NDCG@20={ndcg_20:.4f}")
    return final_model, metrics


def train_xgboost_optuna(X_train, y_train, groups_train, X_val, y_val, groups_val, factor_cols, n_trials=30):
    """使用Optuna调参训练XGBoost rank:ndcg模型"""
    print("\n" + "=" * 60)
    print("训练 XGBoost rank:ndcg 模型（Optuna调参）")
    print("=" * 60)
    
    train_label = to_relevance(y_train, groups_train)
    val_label = to_relevance(y_val, groups_val)
    
    dtrain = xgb.DMatrix(X_train, label=train_label)
    dtrain.set_group(groups_train)
    dval = xgb.DMatrix(X_val, label=val_label)
    dval.set_group(groups_val)
    
    def objective(trial):
        params = {
            "objective": "rank:ndcg",
            "eval_metric": "ndcg@10",
            "eta": trial.suggest_float("eta", 0.005, 0.05, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "subsample": trial.suggest_float("subsample", 0.5, 0.9),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 0.9),
            "min_child_weight": trial.suggest_int("min_child_weight", 10, 300),
            "alpha": trial.suggest_float("alpha", 1e-4, 10.0, log=True),
            "lambda": trial.suggest_float("lambda", 1e-4, 10.0, log=True),
            "gamma": trial.suggest_float("gamma", 1e-4, 1.0, log=True),
            "seed": RANDOM_STATE,
        }
        
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=3000,
            evals=[(dval, "val")],
            early_stopping_rounds=100,
            verbose_eval=False
        )
        
        val_pred = model.predict(dval)
        from sklearn.metrics import ndcg_score
        ndcg_10 = ndcg_score([val_label], [val_pred], k=10)
        return ndcg_10
    
    print(f"  开始Optuna调参，共{n_trials}轮...")
    t0 = time.time()
    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_STATE))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    print(f"  Optuna调参完成，耗时 {time.time()-t0:.1f}s")
    print(f"  最佳NDCG@10: {study.best_value:.4f}")
    print(f"  最佳参数: {json.dumps(study.best_params, indent=2)}")
    
    best_params = study.best_params.copy()
    best_params.update({
        "objective": "rank:ndcg",
        "eval_metric": ["ndcg@5", "ndcg@10", "ndcg@20"],
        "seed": RANDOM_STATE,
    })
    
    with open(MODELS_DIR / "xgboost_best_params.json", "w") as f:
        json.dump({k: v for k, v in best_params.items()}, f, indent=2, default=str)
    
    print("\n  使用最佳参数重新训练最终模型...")
    final_model = xgb.train(
        best_params,
        dtrain,
        num_boost_round=5000,
        evals=[(dval, "val")],
        early_stopping_rounds=150,
        verbose_eval=50
    )
    
    print(f"  最终模型 best_iteration: {final_model.best_iteration}")
    
    val_pred = final_model.predict(dval)
    from sklearn.metrics import ndcg_score
    ndcg_5 = ndcg_score([val_label], [val_pred], k=5)
    ndcg_10 = ndcg_score([val_label], [val_pred], k=10)
    ndcg_20 = ndcg_score([val_label], [val_pred], k=20)
    
    metrics = {
        "val_ndcg": {
            "ndcg@5": float(ndcg_5),
            "ndcg@10": float(ndcg_10),
            "ndcg@20": float(ndcg_20)
        },
        "best_iteration": int(final_model.best_iteration),
        "optuna_best_ndcg10": float(study.best_value),
        "feature_count": len(factor_cols),
        "features": factor_cols
    }
    
    final_model.save_model(str(MODELS_DIR / "xgboost.json"))
    
    importance = {k: float(v) for k, v in final_model.get_score(importance_type="gain").items()}
    with open(MODELS_DIR / "xgboost_feature_importance.json", "w") as f:
        json.dump(importance, f, indent=2)
    
    with open(MODELS_DIR / "xgboost_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"  XGBoost完成! NDCG@5={ndcg_5:.4f}, NDCG@10={ndcg_10:.4f}, NDCG@20={ndcg_20:.4f}")
    return final_model, metrics


def evaluate_on_test(lgb_model, xgb_model, X_test, y_test, groups_test):
    """在测试集上评估模型"""
    print("\n" + "=" * 60)
    print("测试集评估")
    print("=" * 60)
    
    test_label = to_relevance(y_test, groups_test)
    
    def compute_per_group_ndcg(y_true, y_pred, groups, k=10):
        pos = 0
        ndcgs = []
        for g in groups:
            if g <= k:
                pos += g
                continue
            true_slice = y_true[pos:pos+g]
            pred_slice = y_pred[pos:pos+g]
            order = np.argsort(-pred_slice)[:k]
            sorted_true = true_slice[order]
            dcg = sum((2**rel - 1) / np.log2(i + 2) for i, rel in enumerate(sorted_true))
            ideal = np.sort(true_slice)[::-1][:k]
            idcg = sum((2**rel - 1) / np.log2(i + 2) for i, rel in enumerate(ideal))
            ndcgs.append(dcg / idcg if idcg > 0 else 0.0)
            pos += g
        return np.mean(ndcgs) if ndcgs else 0.0
    
    from sklearn.metrics import ndcg_score
    
    lgb_pred = lgb_model.predict(X_test)
    lgb_ndcg5 = compute_per_group_ndcg(test_label, lgb_pred, groups_test, k=5)
    lgb_ndcg10 = compute_per_group_ndcg(test_label, lgb_pred, groups_test, k=10)
    lgb_ndcg20 = compute_per_group_ndcg(test_label, lgb_pred, groups_test, k=20)
    lgb_map = compute_per_group_ndcg(test_label, lgb_pred, groups_test, k=len(groups_test))
    
    dtest = xgb.DMatrix(X_test)
    xgb_pred = xgb_model.predict(dtest)
    xgb_ndcg5 = compute_per_group_ndcg(test_label, xgb_pred, groups_test, k=5)
    xgb_ndcg10 = compute_per_group_ndcg(test_label, xgb_pred, groups_test, k=10)
    xgb_ndcg20 = compute_per_group_ndcg(test_label, xgb_pred, groups_test, k=20)
    xgb_map = compute_per_group_ndcg(test_label, xgb_pred, groups_test, k=len(groups_test))
    
    eval_metrics = {
        "lightgbm": {
            "ndcg@5": float(lgb_ndcg5),
            "ndcg@10": float(lgb_ndcg10),
            "ndcg@20": float(lgb_ndcg20),
            "map": float(lgb_map)
        },
        "xgboost": {
            "ndcg@5": float(xgb_ndcg5),
            "ndcg@10": float(xgb_ndcg10),
            "ndcg@20": float(xgb_ndcg20),
            "map": float(xgb_map)
        },
        "settings": {
            "test_rows": int(len(y_test)),
            "num_queries": int(len(groups_test))
        }
    }
    
    with open(MODELS_DIR / "evaluation_metrics.json", "w") as f:
        json.dump(eval_metrics, f, indent=2)
    
    print(f"  LightGBM - NDCG@5: {lgb_ndcg5:.4f}, NDCG@10: {lgb_ndcg10:.4f}, NDCG@20: {lgb_ndcg20:.4f}, MAP: {lgb_map:.4f}")
    print(f"  XGBoost  - NDCG@5: {xgb_ndcg5:.4f}, NDCG@10: {xgb_ndcg10:.4f}, NDCG@20: {xgb_ndcg20:.4f}, MAP: {xgb_map:.4f}")
    
    return eval_metrics


FIXED_LGB_PARAMS = {
    "objective": "lambdarank",
    "metric": "ndcg",
    "ndcg_eval_at": [5, 10, 20],
    "boosting_type": "gbdt",
    "num_leaves": 83,
    "learning_rate": 0.0074,
    "feature_fraction": 0.433,
    "bagging_fraction": 0.880,
    "bagging_freq": 7,
    "min_child_samples": 414,
    "lambda_l1": 0.00333,
    "lambda_l2": 0.000307,
    "max_depth": 8,
    "min_gain_to_split": 0.00576,
    "verbose": -1,
    "seed": RANDOM_STATE,
    "feature_pre_filter": False,
}

FIXED_XGB_PARAMS = {
    "objective": "rank:ndcg",
    "eval_metric": ["ndcg@5", "ndcg@10", "ndcg@20"],
    "eta": 0.0254,
    "max_depth": 3,
    "subsample": 0.887,
    "colsample_bytree": 0.749,
    "min_child_weight": 279,
    "alpha": 9.101,
    "lambda": 0.0452,
    "gamma": 0.576,
    "seed": RANDOM_STATE,
}


def train_lightgbm_fixed(X_train, y_train, groups_train, X_val, y_val, groups_val, factor_cols):
    """使用固定参数训练LightGBM LambdaRank模型（可复现）"""
    print("\n" + "=" * 60)
    print("训练 LightGBM LambdaRank 模型（固定参数）")
    print("=" * 60)
    
    train_label = to_relevance(y_train, groups_train)
    val_label = to_relevance(y_val, groups_val)
    
    train_data = lgb.Dataset(X_train, label=train_label, group=groups_train, feature_name=factor_cols, free_raw_data=False)
    val_data = lgb.Dataset(X_val, label=val_label, group=groups_val, reference=train_data, feature_name=factor_cols, free_raw_data=False)
    
    t0 = time.time()
    model = lgb.train(
        FIXED_LGB_PARAMS,
        train_data,
        num_boost_round=5000,
        valid_sets=[val_data],
        callbacks=[
            lgb.early_stopping(stopping_rounds=150),
            lgb.log_evaluation(period=50)
        ]
    )
    print(f"  训练完成，耗时 {time.time()-t0:.1f}s, best_iteration={model.best_iteration}")
    
    val_pred = model.predict(X_val)
    from sklearn.metrics import ndcg_score
    ndcg_5 = ndcg_score([val_label], [val_pred], k=5)
    ndcg_10 = ndcg_score([val_label], [val_pred], k=10)
    ndcg_20 = ndcg_score([val_label], [val_pred], k=20)
    
    metrics = {
        "val_ndcg": {"ndcg@5": float(ndcg_5), "ndcg@10": float(ndcg_10), "ndcg@20": float(ndcg_20)},
        "best_iteration": int(model.best_iteration),
        "feature_count": len(factor_cols),
        "features": factor_cols,
        "params": "fixed",
    }
    
    model.save_model(str(MODELS_DIR / "lightgbm.txt"))
    importance = {k: int(v) for k, v in zip(factor_cols, model.feature_importance())}
    with open(MODELS_DIR / "lightgbm_feature_importance.json", "w") as f:
        json.dump(importance, f, indent=2)
    with open(MODELS_DIR / "lightgbm_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"  LightGBM完成! NDCG@5={ndcg_5:.4f}, NDCG@10={ndcg_10:.4f}, NDCG@20={ndcg_20:.4f}")
    return model, metrics


def train_xgboost_fixed(X_train, y_train, groups_train, X_val, y_val, groups_val, factor_cols):
    """使用固定参数训练XGBoost rank:ndcg模型（可复现）"""
    print("\n" + "=" * 60)
    print("训练 XGBoost rank:ndcg 模型（固定参数）")
    print("=" * 60)
    
    train_label = to_relevance(y_train, groups_train)
    val_label = to_relevance(y_val, groups_val)
    
    dtrain = xgb.DMatrix(X_train, label=train_label, feature_names=factor_cols)
    dtrain.set_group(groups_train)
    dval = xgb.DMatrix(X_val, label=val_label, feature_names=factor_cols)
    dval.set_group(groups_val)
    
    t0 = time.time()
    model = xgb.train(
        FIXED_XGB_PARAMS,
        dtrain,
        num_boost_round=5000,
        evals=[(dval, "val")],
        early_stopping_rounds=150,
        verbose_eval=50,
    )
    print(f"  训练完成，耗时 {time.time()-t0:.1f}s, best_iteration={model.best_iteration}")
    
    val_pred = model.predict(dval)
    from sklearn.metrics import ndcg_score
    ndcg_5 = ndcg_score([val_label], [val_pred], k=5)
    ndcg_10 = ndcg_score([val_label], [val_pred], k=10)
    ndcg_20 = ndcg_score([val_label], [val_pred], k=20)
    
    metrics = {
        "val_ndcg": {"ndcg@5": float(ndcg_5), "ndcg@10": float(ndcg_10), "ndcg@20": float(ndcg_20)},
        "best_iteration": int(model.best_iteration),
        "feature_count": len(factor_cols),
        "features": factor_cols,
        "params": "fixed",
    }
    
    model.save_model(str(MODELS_DIR / "xgboost.json"))
    importance = {k: float(v) for k, v in model.get_score(importance_type="gain").items()}
    with open(MODELS_DIR / "xgboost_feature_importance.json", "w") as f:
        json.dump(importance, f, indent=2)
    with open(MODELS_DIR / "xgboost_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"  XGBoost完成! NDCG@5={ndcg_5:.4f}, NDCG@10={ndcg_10:.4f}, NDCG@20={ndcg_20:.4f}")
    return model, metrics


def main():
    parser = argparse.ArgumentParser(description="本地模型训练脚本（优化版）")
    parser.add_argument("--trials", type=int, default=30, help="Optuna调参轮数（默认30）")
    parser.add_argument("--fixed", action="store_true", help="使用固定参数训练（跳过Optuna调参，可复现）")
    parser.add_argument("--gpu", action="store_true", help="使用GPU")
    args = parser.parse_args()
    
    print("=" * 60)
    print("量化选股排序学习模型训练")
    print("=" * 60)
    print(f"开始时间: {datetime.now()}")
    if args.fixed:
        print("模式: 固定参数训练（可复现）")
    else:
        print(f"Optuna调参轮数: {args.trials}")
    
    train_df, val_df, test_df, factor_cols = load_data()
    
    print("\n准备训练数据...")
    X_train, y_train, groups_train, _ = prepare_ranking_data(train_df, factor_cols)
    X_val, y_val, groups_val, _ = prepare_ranking_data(val_df, factor_cols)
    X_test, y_test, groups_test, _ = prepare_ranking_data(test_df, factor_cols)
    
    print(f"  训练: {X_train.shape}, {len(groups_train)} 组")
    print(f"  验证: {X_val.shape}, {len(groups_val)} 组")
    print(f"  测试: {X_test.shape}, {len(groups_test)} 组")
    
    if args.fixed:
        lgb_model, lgb_metrics = train_lightgbm_fixed(
            X_train, y_train, groups_train,
            X_val, y_val, groups_val,
            factor_cols
        )
        xgb_model, xgb_metrics = train_xgboost_fixed(
            X_train, y_train, groups_train,
            X_val, y_val, groups_val,
            factor_cols
        )
    else:
        lgb_model, lgb_metrics = train_lightgbm_optuna(
            X_train, y_train, groups_train,
            X_val, y_val, groups_val,
            factor_cols, n_trials=args.trials
        )
        xgb_model, xgb_metrics = train_xgboost_optuna(
            X_train, y_train, groups_train,
            X_val, y_val, groups_val,
            factor_cols, n_trials=args.trials
        )
    
    eval_metrics = evaluate_on_test(
        lgb_model, xgb_model,
        X_test, y_test, groups_test
    )
    
    print("\n" + "=" * 60)
    print("训练完成!")
    print(f"结束时间: {datetime.now()}")
    print("=" * 60)
    
    print("\n输出文件:")
    for f in MODELS_DIR.glob("*"):
        if f.suffix in [".pkl", ".json", ".txt"]:
            print(f"  - {f.name}")


if __name__ == "__main__":
    main()
