"""测试预测器功能"""
import sys
sys.path.insert(0, '.')

from src.predictor import ModelPredictor, load_prediction_data

def main():
    print("=" * 50)
    print("测试预测器功能")
    print("=" * 50)
    
    # 加载预测器
    predictor = ModelPredictor('lightgbm')
    print(f"预测器已加载: {predictor}")
    
    # 获取特征重要性
    fi = predictor.get_feature_importance()
    print(f"\n特征重要性 (前5个):")
    for i, (k, v) in enumerate(sorted(fi.items(), key=lambda x: -x[1])[:5], 1):
        print(f"  {i}. {k}: {v:.2f}")
    
    # 尝试加载预测数据
    print("\n尝试加载预测数据...")
    try:
        df, timestamp = load_prediction_data()
        print(f"数据加载成功! 截面日期: {timestamp}")
        print(f"数据形状: {df.shape}")
        print(f"列: {list(df.columns[:5])}...")
        
        # 进行预测
        print("\n进行预测...")
        top_stocks = predictor.get_top_stocks(df, top_n=10, with_contributions=False)
        print(f"\nTop 10 股票:")
        for _, row in top_stocks.iterrows():
            print(f"  {row['rank']}. {row['stock_code']}: {row['score']:.4f}")
    except Exception as e:
        print(f"加载预测数据失败: {e}")
        print("尝试使用测试数据...")
        
        # 尝试加载test.parquet
        from pathlib import Path
        import pandas as pd
        test_path = Path("data/test.parquet")
        if test_path.exists():
            df = pd.read_parquet(test_path)
            print(f"测试数据形状: {df.shape}")
            print(f"列: {list(df.columns[:10])}...")
        else:
            print("测试数据也不存在")

if __name__ == "__main__":
    main()
