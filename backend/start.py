#!/usr/bin/env python3
"""
Railway部署启动脚本
处理数据库初始化、模型加载和路径问题
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

os.environ["PYTHONPATH"] = str(project_root)
os.environ["APP_ENV"] = "production"

models_dir = project_root / "models"
lightgbm_model = models_dir / "lightgbm.pkl"
xgboost_model = models_dir / "xgboost.pkl"

print(f"Python版本: {sys.version}")
print(f"工作目录: {Path.cwd()}")
print(f"项目根目录: {project_root}")
print(f"模型目录: {models_dir}")
print(f"LightGBM模型存在: {lightgbm_model.exists()}")
print(f"XGBoost模型存在: {xgboost_model.exists()}")

try:
    from src.database.database import Base, engine
    from src.database.models import AIAdvice, BacktestResult, FactorData, ShadowAccount, Stock
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")
except Exception as e:
    print(f"数据库初始化警告: {e}")

try:
    from src.main import app
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"

    print(f"\n启动服务: {host}:{port}")
    uvicorn.run(app, host=host, port=port)

except Exception as e:
    print(f"\n启动失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
