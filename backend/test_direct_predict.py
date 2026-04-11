"""直接测试预测器功能"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from pathlib import Path
from src.predictor import ModelPredictor

def main():
    print("=" * 60)
    print("直接测试预测器功能")
    print("=" * 60)
    
    # 加载预测器
    print("\n1. 加载LightGBM预测器...")
    predictor = ModelPredictor('lightgbm')
    print(f"   预测器已加载: {predictor}")
    
    # 获取特征重要性
    print("\n2. 获取特征重要性...")
    fi = predictor.get_feature_importance()
    ranked = sorted(fi.items(), key=lambda x: -x[1])
    print(f"   特征数量: {len(fi)}")
    print("   Top 5 特征:")
    for i, (k, v) in enumerate(ranked[:5], 1):
        print(f"     {i}. {k}: {v:.2f}")
    
    # 加载测试数据
    print("\n3. 加载测试数据...")
    data_dir = Path("data")
    
    # 尝试加载current_weekly_factors.parquet
    current_path = data_dir / "current_weekly_factors.parquet"
    test_path = data_dir / "test.parquet"
    
    df = None
    timestamp = "unknown"
    
    if current_path.exists():
        print(f"   加载 {current_path}...")
        df = pd.read_parquet(current_path)
        timestamp = "current"
    elif test_path.exists():
        print(f"   加载 {test_path}...")
        df = pd.read_parquet(test_path)
        if 'date' in df.columns:
            timestamp = str(df['date'].max())
        else:
            timestamp = "test"
    else:
        print("   错误: 没有可用的数据文件")
        return
    
    print(f"   数据形状: {df.shape}")
    print(f"   列: {list(df.columns[:8])}...")
    
    # 进行预测
    print("\n4. 进行预测 (Top 20)...")
    top_stocks = predictor.get_top_stocks(df, top_n=20, with_contributions=False)
    
    print(f"\n   截面日期: {timestamp}")
    print("   Top 20 股票:")
    print("-" * 40)
    for _, row in top_stocks.iterrows():
        print(f"   {row['rank']:2d}. {row['stock_code']}: {row['score']:.6f}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
