"""
从本地全量周频因子数据（2257只股票×60因子）生成完整的排序学习数据集
替换 query_smoke_out/ 下的冒烟测试数据（仅30只股票）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import generate_query_datasets

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "query_smoke_out"

model_input_path = DATA_DIR / "weekly_model_input.parquet"
if not model_input_path.exists():
    raise FileNotFoundError(f"未找到模型输入数据: {model_input_path}")

print("加载全量模型输入数据...")
df = pd.read_parquet(model_input_path)
df["date"] = pd.to_datetime(df["date"])
df["stock_code"] = df["stock_code"].astype(str)
print(f"  总行数: {len(df):,}")
print(f"  股票数: {df['stock_code'].nunique()}")
print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
print(f"  因子列数: {len([c for c in df.columns if c not in {'date', 'stock_code', 'close'}])}")

print(f"\n生成排序学习数据集 -> {OUTPUT_DIR}")
result = generate_query_datasets(
    df,
    output_dir=OUTPUT_DIR,
    train_end="2020-12-31",
    val_end="2022-12-31",
    forward_weeks=1,
)

for name, path in result.items():
    check = pd.read_parquet(path)
    dates = check["date"].nunique()
    stocks_per_date = int(check.groupby("date")["stock_code"].nunique().mean())
    print(f"  {name}: {len(check):,} 行, {dates} 个截面, 平均 {stocks_per_date} 只/截面")

print("\n完成！已用全量数据替换 query_smoke_out/ 下的冒烟测试数据")
