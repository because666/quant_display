# 云GPU训练指南

## 1. 需要上传的文件

### 数据文件 (放到 `data/` 目录)
```
data/
├── train.parquet          # 训练数据
├── val.parquet            # 验证数据
├── test.parquet           # 测试数据
└── factor_columns.pkl     # 因子列定义
```

### 训练脚本
```
cloud_train.py             # 主训练脚本
requirements_cloud.txt     # Python依赖
```

## 2. 云GPU环境设置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements_cloud.txt

# 如果使用GPU，安装GPU版本
pip install lightgbm --install-option=--gpu
pip install xgboost --install-option=--cuda
```

## 3. 运行训练

```bash
# 基础训练（CPU）
python cloud_train.py

# 使用GPU
python cloud_train.py --gpu

# 增加Optuna试验次数
python cloud_train.py --trials 50 --gpu
```

## 4. 训练输出

训练完成后，`models/` 目录会生成以下文件：

```
models/
├── lightgbm.txt                    # LightGBM模型
├── lightgbm_metrics.json           # LightGBM训练指标
├── lightgbm_feature_importance.json
├── xgboost.json                    # XGBoost模型
├── xgboost_metrics.json            # XGBoost训练指标
├── xgboost_feature_importance.json
└── evaluation_metrics.json         # 测试集评估
```

## 5. 下载模型到本地

将 `models/` 目录下的所有文件下载到本地项目的 `backend/models/` 目录。

## 6. 数据文件说明

| 文件 | 说明 |
|------|------|
| train.parquet | 训练集，约109万行 |
| val.parquet | 验证集，约47万行 |
| test.parquet | 测试集，约53万行 |
| factor_columns.pkl | 15个因子列名 |

## 7. 预期训练时间

| 环境 | LightGBM | XGBoost | 总计 |
|------|----------|---------|------|
| CPU (8核) | ~30分钟 | ~45分钟 | ~1.5小时 |
| GPU (A10) | ~10分钟 | ~15分钟 | ~30分钟 |

## 8. 模型评估指标

训练完成后查看 `evaluation_metrics.json`：

```json
{
  "lightgbm": {
    "ndcg@10": 0.15,
    "map": 0.48
  },
  "xgboost": {
    "ndcg@10": 0.16,
    "map": 0.49
  }
}
```

- **NDCG@10**: 排序质量指标，越高越好（通常0.1-0.3）
- **MAP**: 平均精度，越高越好（通常0.3-0.6）
