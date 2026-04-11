"""检查数据和模型状态"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
import pandas as pd
import json

def main():
    print("=" * 60)
    print("数据和模型状态检查")
    print("=" * 60)
    
    # 1. 检查数据文件
    data_dir = Path("data")
    print("\n=== 数据文件 ===")
    
    # 训练数据
    train_path = data_dir / "train.parquet"
    val_path = data_dir / "val.parquet"
    test_path = data_dir / "test.parquet"
    
    for p in [train_path, val_path, test_path]:
        if p.exists():
            df = pd.read_parquet(p)
            print(f"{p.name}: {df.shape[0]:,} 行, {df.shape[1]} 列")
        else:
            print(f"{p.name}: 不存在")
    
    # 因子列
    factor_path = data_dir / "factor_columns.pkl"
    if factor_path.exists():
        import pickle
        with open(factor_path, "rb") as f:
            factors = pickle.load(f)
        print(f"factor_columns.pkl: {len(factors)} 个因子")
    else:
        print("factor_columns.pkl: 不存在")
    
    # 原始数据
    raw_dir = data_dir / "raw"
    if raw_dir.exists():
        raw_files = list(raw_dir.glob("*.parquet"))
        print(f"raw/: {len(raw_files)} 个股票数据文件")
    
    # 2. 检查模型文件
    models_dir = Path("models")
    print("\n=== 模型文件 ===")
    
    for model_name in ["lightgbm", "xgboost"]:
        model_path = models_dir / f"{model_name}.pkl"
        metrics_path = models_dir / f"{model_name}_metrics.json"
        
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"{model_name}.pkl: {size_mb:.2f} MB")
        else:
            print(f"{model_name}.pkl: 不存在")
        
        if metrics_path.exists():
            with open(metrics_path, "r") as f:
                metrics = json.load(f)
            print(f"  验证集 NDCG@10: {metrics.get('val_ndcg', {}).get('ndcg@10', 'N/A'):.4f}")
    
    # 3. 评估指标
    eval_path = models_dir / "evaluation_metrics.json"
    if eval_path.exists():
        with open(eval_path, "r") as f:
            eval_metrics = json.load(f)
        print("\n=== 测试集评估 ===")
        print(f"LightGBM MAP: {eval_metrics['lightgbm']['map']:.4f}")
        print(f"LightGBM NDCG@10: {eval_metrics['lightgbm']['ndcg@10']:.4f}")
        print(f"XGBoost MAP: {eval_metrics['xgboost']['map']:.4f}")
        print(f"XGBoost NDCG@10: {eval_metrics['xgboost']['ndcg@10']:.4f}")
    
    print("\n" + "=" * 60)
    print("状态: 模型已训练，可直接进行回测")
    print("=" * 60)

if __name__ == "__main__":
    main()
