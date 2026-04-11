"""
验证从云GPU下载的模型
在本地运行此脚本验证模型是否正确加载
"""
import sys
sys.path.insert(0, '.')

import json
import pickle
from pathlib import Path

import pandas as pd
import numpy as np
import lightgbm as lgb
import xgboost as xgb

DATA_DIR = Path("data")
MODELS_DIR = Path("models")


def verify_models():
    """验证模型文件"""
    print("=" * 60)
    print("验证模型文件")
    print("=" * 60)
    
    # 检查模型文件
    print("\n1. 检查模型文件...")
    required_files = [
        "lightgbm.txt",
        "lightgbm_metrics.json",
        "lightgbm_feature_importance.json",
        "xgboost.json",
        "xgboost_metrics.json",
        "xgboost_feature_importance.json",
        "evaluation_metrics.json"
    ]
    
    all_exist = True
    for f in required_files:
        path = MODELS_DIR / f
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  ✓ {f}: {size_kb:.1f} KB")
        else:
            print(f"  ✗ {f}: 不存在")
            all_exist = False
    
    if not all_exist:
        print("\n❌ 部分模型文件缺失，请从云GPU下载完整")
        return False
    
    # 加载模型
    print("\n2. 加载模型...")
    try:
        lgb_model = lgb.Booster(model_file=str(MODELS_DIR / "lightgbm.txt"))
        print("  ✓ LightGBM模型加载成功")
        
        xgb_model = xgb.Booster()
        xgb_model.load_model(str(MODELS_DIR / "xgboost.json"))
        print("  ✓ XGBoost模型加载成功")
    except Exception as e:
        print(f"  ✗ 模型加载失败: {e}")
        return False
    
    # 加载因子
    print("\n3. 加载因子列...")
    factor_path = DATA_DIR / "factor_columns.pkl"
    if factor_path.exists():
        with open(factor_path, "rb") as f:
            factor_cols = pickle.load(f)
        print(f"  ✓ 因子数量: {len(factor_cols)}")
    else:
        print("  ✗ factor_columns.pkl 不存在")
        return False
    
    # 测试预测
    print("\n4. 测试预测...")
    try:
        # 创建测试数据
        test_data = pd.DataFrame({
            col: [0.1] for col in factor_cols
        })
        
        # LightGBM预测
        lgb_pred = lgb_model.predict(test_data.values)
        print(f"  ✓ LightGBM预测: {lgb_pred[0]:.6f}")
        
        # XGBoost预测
        dtest = xgb.DMatrix(test_data.values)
        xgb_pred = xgb_model.predict(dtest)
        print(f"  ✓ XGBoost预测: {xgb_pred[0]:.6f}")
    except Exception as e:
        print(f"  ✗ 预测失败: {e}")
        return False
    
    # 显示评估指标
    print("\n5. 模型评估指标...")
    eval_path = MODELS_DIR / "evaluation_metrics.json"
    if eval_path.exists():
        with open(eval_path, "r") as f:
            metrics = json.load(f)
        
        lgb_m = metrics.get("lightgbm", {})
        xgb_m = metrics.get("xgboost", {})
        
        print(f"  LightGBM:")
        print(f"    MAP: {lgb_m.get('map', 0):.4f}")
        print(f"    NDCG@10: {lgb_m.get('ndcg@10', 0):.4f}")
        
        print(f"  XGBoost:")
        print(f"    MAP: {xgb_m.get('map', 0):.4f}")
        print(f"    NDCG@10: {xgb_m.get('ndcg@10', 0):.4f}")
    
    print("\n" + "=" * 60)
    print("✅ 模型验证通过!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = verify_models()
    sys.exit(0 if success else 1)
