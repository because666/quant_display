# 基于排序学习的量化投资选股策略设计与应用

## 项目结构

- `backend/`：FastAPI 后端、数据处理与模型服务
- `frontend/`：React + TypeScript + Vite 前端网站

## 快速开始

### 一键启动（推荐）

- **Windows**：在项目根目录双击或执行 `start.bat`，会分别打开两个终端窗口启动后端与前端。
- **Linux / macOS**：在项目根目录执行：
  - `chmod +x start.sh`
  - `./start.sh`

启动成功后：

- 后端 API：`http://127.0.0.1:8000`（健康检查：`GET /health`）
- 前端页面：`http://127.0.0.1:5173`（页面会请求 `GET /api/v1/test` 验证联调）

### 分别启动（开发联调）

#### 后端

1. 进入目录：`cd backend`
2. 激活虚拟环境（PowerShell）：`.\venv\Scripts\Activate.ps1`
3. 启动服务：`python -m uvicorn src.main:app --reload`  
   （也可使用 `uvicorn main:app --reload`，`main.py` 会转发到 `src.main:app`）

#### 前端

1. 进入目录：`cd frontend`
2. 安装依赖：`npm install`
3. 启动开发环境：`npm run dev`

### 联调说明

- 前端 Axios 默认 `baseURL` 为 `http://localhost:8000/api/v1`（见 `frontend/src/services/api.ts`）。
- 后端已配置 CORS，允许 `http://localhost:5173` 与 `http://127.0.0.1:5173`。
- 若希望走 Vite 代理避免浏览器跨域，可在 `frontend` 下创建 `.env` 并设置：
  - `VITE_API_BASE_URL=/api/v1`  
  开发服务器会将 `/api` 代理到 `http://127.0.0.1:8000`（见 `frontend/vite.config.ts`）。

### 模型预测 API（排序得分 / AI 推荐上下文）

后端启动后（`python -m uvicorn src.main:app --reload`，工作目录为 `backend` 且已配置 `PYTHONPATH`），基址为 `http://127.0.0.1:8000`。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/predict` | 可选请求体：`stock_codes`（限定股票）、`date`（截面日期 YYYY-MM-DD）、`top_n`（默认 20）。返回 `code`、`data.top_stocks`（`code`+`score`）、`data.feature_importance`、`data.timestamp`。 |
| `GET` | `/api/v1/model/info` | 返回当前默认模型类型、`trained_at`（模型文件更新时间）、`feature_importance` 与按重要性排序的 `feature_importance_list`。 |

- **默认模型**：环境变量或 `.env` 中 `DEFAULT_PREDICT_MODEL`（`lightgbm` / `xgboost`），缺省为 `lightgbm`。模型与因子路径见 `backend/src/config.py`（`LIGHTGBM_MODEL_PATH`、`XGBOOST_MODEL_PATH`、`QUANT_DATA_DIR` 等）。
- **单例加载**：`ModelPredictor` 通过 `src.api.v1.deps.get_predictor` 缓存，进程内只加载一次。
- **Python 侧 AI 上下文**：`ModelPredictor.get_advice_context(top_n=10)` 返回字典，包含 Top 股票 `code`/`score`、全局 `feature_importance`、`section_date`、`model_type`（见 `backend/src/predictor.py`）。

示例：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/predict -H "Content-Type: application/json" -d "{\"top_n\": 10}"
curl -s http://127.0.0.1:8000/api/v1/model/info
```

**单元测试**（需安装 `pytest`）：

```bash
cd backend
set PYTHONPATH=.
python -m pytest tests/test_predict_api.py -v
```

### 批量下载日线数据（阶段2）

在 `backend` 目录下执行（需已配置虚拟环境并安装依赖）：

```bash
# Windows PowerShell
$env:PYTHONPATH="."
python -m src.data_fetcher --download --start-date 2014-01-01 --end-date 2024-12-31
```

- 首次会构建「存活股票池」并缓存到 `backend/data/meta/surviving_stocks_*.parquet`（约 3000 只量级，需逐只拉取东财资料，耗时较长）。
- 日线写入 `backend/data/raw/{股票代码}.parquet`；失败代码写入 `backend/data/meta/download_failed_codes.txt`，详细日志见 `backend/logs/data_download.log`。
- 强制重建股票池时加参数：`--refresh-pool`。

## 工程化说明

- 后端依赖锁定在 `backend/requirements.txt`
- 前端使用 ESLint + Prettier，配置文件为 `frontend/.eslintrc.cjs` 与 `frontend/.prettierrc`
- 前端源码按模块放置在 `frontend/src/components`、`frontend/src/pages`、`frontend/src/hooks`、`frontend/src/types`、`frontend/src/services`、`frontend/src/utils`、`frontend/src/styles`
