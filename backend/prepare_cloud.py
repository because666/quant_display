"""
准备云GPU训练所需的文件
运行此脚本生成打包说明
"""
from pathlib import Path

print("=" * 60)
print("云GPU训练准备")
print("=" * 60)

# 检查必要文件
data_dir = Path("data")
models_dir = Path("models")

print("\n必要数据文件:")
required_files = [
    "train.parquet",
    "val.parquet", 
    "test.parquet",
    "factor_columns.pkl"
]

for f in required_files:
    path = data_dir / f
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  ✓ {f}: {size_mb:.1f} MB")
    else:
        print(f"  ✗ {f}: 不存在")

print("\n训练脚本:")
print("  ✓ cloud_train.py")
print("  ✓ requirements_cloud.txt")
print("  ✓ README_CLOUD.md")

print("\n" + "=" * 60)
print("上传清单")
print("=" * 60)
print("""
将以下文件上传到云GPU服务器：

data/
├── train.parquet      (约 100MB)
├── val.parquet        (约 45MB)
├── test.parquet       (约 50MB)
└── factor_columns.pkl (约 1KB)

cloud_train.py
requirements_cloud.txt
README_CLOUD.md

总计约 200MB
""")

print("=" * 60)
print("云GPU训练步骤")
print("=" * 60)
print("""
1. 上传文件到云GPU

2. 安装依赖:
   pip install -r requirements_cloud.txt

3. 运行训练:
   python cloud_train.py --gpu

4. 下载模型文件:
   下载 models/ 目录下所有文件到本地 backend/models/

5. 本地验证:
   python verify_models.py
""")

print("=" * 60)
