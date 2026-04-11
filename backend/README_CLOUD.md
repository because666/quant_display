# 云GPU训练指南

## 概述

本项目已准备好云GPU训练所需的全部文件。按照以下步骤操作即可。

## 文件清单

### 需要上传到云GPU的文件

```
backend/
├── data/
│   ├── train.parquet      # 训练数据 (~100MB)
│   ├── val.parquet        # 验证数据 (~45MB)
│   ├── test.parquet       # 测试数据 (~50MB)
│   └── factor_columns.pkl # 因子列定义
├── cloud_train.py         # 训练脚本
├── requirements_cloud.txt # 依赖清单
└── README_CLOUD.md        # 本文档
```

**总大小约 200MB**

## 步骤详解

### 第一步：上传文件到云GPU

将上述文件上传到云GPU服务器，保持目录结构：

```bash
# 建议目录结构
/home/user/quant_train/
├── data/
│   ├── train.parquet
│   ├── val.parquet
│   ├── test.parquet
│   └── factor_columns.pkl
├── cloud_train.py
└── requirements_cloud.txt
```

### 第二步：安装依赖

```bash
# 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate

# 安装基础依赖
pip install -r requirements_cloud.txt

# 如果使用GPU，安装GPU版本
pip install lightgbm --install-option=--gpu
pip install xgboost --install-option=--cuda
```

### 第三步：运行训练

```bash
# 基础训练
python cloud_train.py

# 使用GPU
python cloud_train.py --gpu

# 增加超参搜索次数
python cloud_train.py --trials 50 --gpu
```

### 第四步：下载模型

训练完成后，`models/` 目录会生成以下文件：

```
models/
├── lightgbm.txt                    # LightGBM模型
├── lightgbm_metrics.json           # 训练指标
├── lightgbm_feature_importance.json
├── xgboost.json                    # XGBoost模型
├── xgboost_metrics.json            # 训练指标
├── xgboost_feature_importance.json
└── evaluation_metrics.json         # 测试集评估
```

将整个 `models/` 目录下载到本地项目的 `backend/models/` 目录。

### 第五步：本地验证

```bash
cd d:\量化\V2.0\backend
.\venv\Scripts\python.exe verify_models.py
```

验证通过后，运行回测：

```bash
.\venv\Scripts\python.exe copy_results.py
```

## 预期训练时间

| 环境 | LightGBM | XGBoost | 总计 |
|------|----------|---------|------|
| CPU (8核) | ~30分钟 | ~45分钟 | ~1.5小时 |
| GPU (A10) | ~10分钟 | ~15分钟 | ~30分钟 |

## 模型评估指标说明

| 指标 | 含义 | 目标值 |
|------|------|--------|
| MAP | 平均精度均值 | > 0.45 |
| NDCG@10 | 前10名排序质量 | > 0.10 |
| NDCG@20 | 前20名排序质量 | > 0.15 |

## 常见问题

### Q: 训练中断怎么办？
A: 脚本支持断点续训，重新运行即可。

### Q: GPU内存不足？
A: 减小 `batch_size` 或使用 `--trials 10` 减少试验次数。

### Q: 如何查看训练日志？
A: 训练过程会输出到控制台，可重定向到文件：
```bash
python cloud_train.py --gpu 2>&1 | tee train.log
```

## 联系支持

如有问题，请检查：
1. 数据文件完整性
2. 依赖版本兼容性
3. GPU驱动是否正确安装
