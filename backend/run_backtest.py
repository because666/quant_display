"""运行回测并导出数据到前端"""
import sys
sys.path.insert(0, '.')

import json
import shutil
from pathlib import Path
from src.backtest import run_backtest_and_export

def main():
    print("=" * 60)
    print("运行回测并导出数据")
    print("=" * 60)
    
    # 运行回测 - 使用较小的top_n加快速度
    print("\n1. 运行LightGBM回测 (Top 10)...")
    try:
        results = run_backtest_and_export(
            top_n=10,
            initial_capital=1_000_000.0,
            use_split="test",
        )
        print("   回测完成!")
        print(f"   输出目录: {results.get('out_dir')}")
    except Exception as e:
        print(f"   回测失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 检查结果
    print("\n2. 检查回测结果...")
    out_dir = Path("data/backtest_results")
    if out_dir.exists():
        for f in out_dir.glob("*.json"):
            print(f"   - {f.name}")
    
    # 复制到前端
    print("\n3. 复制到前端...")
    frontend_data_dir = Path("../frontend/public/data")
    if not frontend_data_dir.exists():
        frontend_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制回测结果
    backtest_json = out_dir / "backtest_results.json"
    if backtest_json.exists():
        shutil.copy(backtest_json, frontend_data_dir / "backtest_results.json")
        print(f"   已复制: backtest_results.json")
        
        # 读取并显示关键指标
        with open(backtest_json, "r") as f:
            data = json.load(f)
            metrics = data.get("metrics", {})
            print("\n   === 关键指标 ===")
            print(f"   年化收益: {metrics.get('annualReturn', 0):.2f}%")
            print(f"   夏普比率: {metrics.get('sharpeRatio', 0):.2f}")
            print(f"   最大回撤: {metrics.get('maxDrawdown', 0):.2f}%")
            print(f"   胜率: {metrics.get('winRate', 0):.2f}%")
    
    # 复制评估指标
    models_dir = Path("models")
    for f in models_dir.glob("evaluation_metrics.json"):
        shutil.copy(f, frontend_data_dir / f.name)
        print(f"   已复制: {f.name}")
    
    for f in models_dir.glob("*_feature_importance.json"):
        shutil.copy(f, frontend_data_dir / f.name)
        print(f"   已复制: {f.name}")
    
    for f in models_dir.glob("ndcg_curve.json"):
        shutil.copy(f, frontend_data_dir / f.name)
        print(f"   已复制: {f.name}")
    
    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
