# Railway部署指南

## 概述

本指南帮助你在Railway平台上部署量化投资选股策略系统。

## 部署架构

```
┌─────────────────┐     ┌─────────────────┐
│   Railway.app   │     │   Railway.app   │
│                 │     │                 │
│  Frontend       │────▶│  Backend API    │
│  (React)        │     │  (FastAPI)      │
│                 │     │                 │
└─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   SQLite DB     │
                        │   Models        │
                        │   Data Files    │
                        └─────────────────┘
```

## 快速部署步骤

### 1. 准备工作

确保你的代码已经推送到GitHub：
```bash
git push origin main
```

### 2. 在Railway上创建项目

1. 访问 https://railway.app
2. 点击 "New Project"
3. 选择 "Deploy from GitHub repo"
4. 选择你的仓库 `because666/quant_display`

### 3. 配置后端服务

#### 3.1 添加后端服务

1. 在项目页面点击 "New"
2. 选择 "GitHub Repo"
3. 选择同一个仓库
4. 设置服务名称：`quant-display-backend`

#### 3.2 配置环境变量

在服务的 "Variables" 标签页添加以下变量：

```
# 基础配置
PORT=8000
PYTHONPATH=/app

# 应用配置
APP_NAME=Quant Display API
APP_VERSION=1.0.0
LOG_LEVEL=INFO

# 数据库
DATABASE_URL=sqlite:///./app.db

# CORS配置
CORS_ALLOW_ORIGINS=["*"]

# 模型配置
DEFAULT_PREDICT_MODEL=lightgbm
LIGHTGBM_MODEL_PATH=models/lightgbm.pkl
XGBOOST_MODEL_PATH=models/xgboost.pkl

# DeepSeek API（如果需要AI推荐功能）
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

#### 3.3 配置启动命令

在 "Settings" 中设置：
- **Build Command**: `cd backend && pip install -r requirements.txt`
- **Start Command**: `cd backend && uvicorn src.main:app --host 0.0.0.0 --port $PORT`

### 4. 配置前端服务（可选）

如果你希望前端也部署在Railway上：

#### 4.1 添加前端服务

1. 点击 "New" → "GitHub Repo"
2. 选择同一个仓库
3. 设置服务名称：`quant-display-frontend`

#### 4.2 配置环境变量

```
BACKEND_URL=https://quant-display-backend.railway.app
```

#### 4.3 配置启动命令

- **Build Command**: `cd frontend && npm ci && npm run build`
- **Start Command**: `cd frontend && npx serve -s dist -l $PORT`

### 5. 配置域名

#### 5.1 后端域名

1. 进入后端服务
2. 点击 "Settings" → "Domains"
3. 点击 "Generate Domain"
4. 记录下域名，例如：`quant-display-backend.railway.app`

#### 5.2 前端域名（可选）

1. 进入前端服务
2. 点击 "Settings" → "Domains"
3. 点击 "Generate Domain"

### 6. 更新前端API配置

修改 `frontend/src/services/api.ts`：

```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 
                 'https://quant-display-backend.railway.app/api/v1';
```

## 部署配置说明

### 已创建的配置文件

| 文件 | 用途 |
|------|------|
| `railway.json` | Railway主配置文件 |
| `Procfile` | 服务启动命令 |
| `runtime.txt` | Python版本 |
| `nixpacks.toml` | Nixpacks构建配置 |
| `backend/Dockerfile` | 后端Docker镜像 |
| `backend/.dockerignore` | Docker忽略文件 |
| `frontend/Dockerfile` | 前端Docker镜像 |
| `frontend/nginx.conf` | Nginx配置 |
| `frontend/.env.production` | 前端生产环境变量 |

## 常见问题

### 1. 模型文件太大

如果模型文件（.pkl）超过100MB，GitHub会拒绝推送。解决方案：

**方案A：使用Git LFS**
```bash
git lfs install
git lfs track "*.pkl"
git add .gitattributes
git commit -m "Add Git LFS"
git push
```

**方案B：在部署时下载模型**
在 `backend/src/config.py` 中添加模型下载逻辑：
```python
import os
import requests

def download_model_if_needed(model_path, model_url):
    if not os.path.exists(model_path):
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        response = requests.get(model_url)
        with open(model_path, 'wb') as f:
            f.write(response.content)
```

**方案C：使用Railway Volume存储模型**
1. 在Railway中创建Volume
2. 将模型文件上传到Volume
3. 在代码中从Volume读取模型

### 2. 内存不足

Railway免费版有内存限制（512MB）。如果启动失败：

1. 优化模型加载方式（延迟加载）
2. 减少并发 workers 数量
3. 升级Railway套餐

### 3. 数据库持久化

SQLite在容器重启后会丢失数据。建议：

**方案A：使用Railway PostgreSQL**
1. 点击 "New" → "Database" → "Add PostgreSQL"
2. 修改后端代码使用PostgreSQL

**方案B：使用Railway Volume**
1. 创建Volume并挂载到 `/app/data`
2. 修改数据库路径为 `/app/data/app.db`

### 4. CORS错误

如果前端无法访问后端API：

1. 检查 `CORS_ALLOW_ORIGINS` 环境变量
2. 确保包含前端域名
3. 或者设置为 `["*"]` 允许所有来源（仅开发环境）

## 监控和日志

### 查看日志

1. 进入服务页面
2. 点击 "Deployments"
3. 选择最新的部署
4. 查看 "Logs" 标签页

### 设置健康检查

在 `railway.json` 中添加：
```json
{
  "healthcheck": {
    "path": "/health",
    "port": 8000
  }
}
```

## 更新部署

每次推送代码到GitHub，Railway会自动重新部署：

```bash
git add .
git commit -m "Update code"
git push origin main
```

## 费用说明

Railway免费版限制：
- 每月 $5 或 500 小时运行时间
- 512MB 内存
- 1GB 磁盘空间
- 100GB 出站流量

如果超出限制，需要升级到付费版。

## 获取帮助

- Railway文档：https://docs.railway.app
- Railway Discord：https://discord.gg/railway
- 项目Issues：https://github.com/because666/quant_display/issues
