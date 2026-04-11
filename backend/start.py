#!/usr/bin/env python3
"""
Railway部署启动脚本
处理模型加载和路径问题
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ["PYTHONPATH"] = str(project_root)
os.environ["APP_ENV"] = "production"

# 检查模型文件是否存在
models_dir = project_root / "models"
lightgbm_model = models_dir / "lightgbm.pkl"
xgboost_model = models_dir / "xgboost.pkl"

print(f"Python版本: {sys.version}")
print(f"工作目录: {Path.cwd()}")
print(f"项目根目录: {project_root}")
print(f"模型目录: {models_dir}")
print(f"LightGBM模型存在: {lightgbm_model.exists()}")
print(f"XGBoost模型存在: {xgboost_model.exists()}")

# 导入并启动应用
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
