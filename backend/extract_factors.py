"""
从模型特征重要性文件中提取因子列名，生成 factor_columns.pkl
"""
import json
import pickle
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"

def main():
    # 从lightgbm特征重要性文件中读取因子名
    fi_path = MODELS_DIR / "lightgbm_feature_importance.json"
    with open(fi_path, "r", encoding="utf-8") as f:
        fi = json.load(f)
    
    factor_cols = list(fi.keys())
    print(f"从模型中提取的因子列 ({len(factor_cols)} 个):")
    for i, col in enumerate(factor_cols, 1):
        print(f"  {i}. {col}")
    
    # 保存为pkl文件
    output_path = DATA_DIR / "factor_columns.pkl"
    with open(output_path, "wb") as f:
        pickle.dump(factor_cols, f)
    
    print(f"\n已保存到: {output_path}")

if __name__ == "__main__":
    main()
