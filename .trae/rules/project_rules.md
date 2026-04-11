# 项目角色定义

## 项目身份
你是一个**量化投资选股策略系统**的开发助手，项目名称为"基于排序学习的量化投资选股策略设计与应用"。

## 技术栈规范

### 前端技术栈
- **框架**: React 18 + TypeScript + Vite
- **可视化**: ECharts / Plotly
- **样式**: TailwindCSS
- **状态管理**: Zustand
- **HTTP请求**: Axios
- **Markdown渲染**: react-markdown

### 后端技术栈
- **框架**: Python 3.8+ + FastAPI
- **数据处理**: Pandas / Numpy
- **机器学习**: LightGBM + XGBoost（排序学习）
- **数据源**: akshare
- **AI服务**: DeepSeek API（聚合站接口）
- **数据库**: SQLite

### 部署
- **平台**: Zeabur

## 开发阶段（共6个阶段）

### 阶段1：项目初始化与全局规范制定
- 前后端项目结构初始化
- 项目开发规范手册制定
- 数据库表结构设计
- 基础数据获取模块（akshare封装）
- DeepSeek API客户端配置

### 阶段2：数据层开发
- 股票池筛选（近10年存续A股约3000只）
- 日线数据清洗（前复权、停牌标记、涨跌停标记）
- 周频截面对齐
- 基础因子计算（10~30个）
- 排序学习数据集构造（query group格式）
- 实时数据更新模块

### 阶段3：模型层开发
- LightGBM LambdaRank训练
- XGBoost rank:ndcg训练
- 模型评估（NDCG@K、MAP）
- 特征重要性分析
- 预测器模块

### 阶段4：回测与评估框架开发
- 回测引擎（T+1、印花税0.05%、佣金0.03%、滑点0.1%）
- 选股逻辑（Top N等权配置）
- 策略评估指标（年化收益、夏普比率、最大回撤、换手率、胜率）
- 模型对比功能

### 阶段5：AI推荐服务与影子账户功能开发
- 影子账户管理（无鉴权，最多10人）
- 实时建议接口
- 买卖价格区间计算（ATR、支撑阻力位）
- DeepSeek流式响应（SSE）
- 提示词工程

### 阶段6：前端网站开发与集成
- 策略概览页面
- 回测仪表盘页面
- 模型分析页面
- 因子探索页面
- AI推荐页面
- 影子账户页面

## 核心模块清单

### 后端模块
| 模块文件 | 功能描述 |
|---------|---------|
| `src/data_fetcher.py` | 数据获取模块（akshare封装） |
| `src/data_loader.py` | 数据加载模块 |
| `src/model_lightgbm.py` | LightGBM训练脚本 |
| `src/model_xgboost.py` | XGBoost训练脚本 |
| `src/predictor.py` | 模型预测模块 |
| `src/backtest.py` | 回测引擎 |
| `src/metrics.py` | 指标计算工具 |
| `src/account.py` | 影子账户管理 |
| `src/price_range.py` | 价格区间计算 |
| `src/prompt_builder.py` | 提示词构造器 |
| `src/deepseek_client.py` | DeepSeek API客户端 |
| `src/deepseek_stream.py` | DeepSeek流式接口 |

### 前端页面
| 页面 | 路由 | 功能描述 |
|-----|------|---------|
| 策略概览 | `/` | 项目简介、模型架构图、数据范围 |
| 回测仪表盘 | `/backtest` | 收益曲线、月度热力图、持仓变动图 |
| 模型分析 | `/model` | 特征重要性、NDCG曲线 |
| 因子探索 | `/factors` | 因子分布散点图、收益相关性 |
| AI推荐 | `/advice` | 实时建议、流式Markdown渲染 |
| 影子账户 | `/account` | 持仓管理、历史建议查看 |

## 关键约束条件

### 回测引擎约束
- **交易规则**: T+1
- **印花税**: 卖出单边0.05%
- **佣金**: 双边0.03%
- **滑点**: 双边0.1%
- **涨跌停限制**: 涨停无法买入、跌停无法卖出
- **支持空仓**: 可观望操作

### AI服务约束
- **API来源**: DeepSeek聚合站（自定义URL+密钥）
- **接口兼容**: OpenAI格式
- **输出格式**: 特定Markdown结构（操作建议、买入区间、卖出区间、风险提示）
- **响应方式**: 流式输出（SSE）

### 影子账户约束
- **鉴权方式**: 无登录鉴权
- **用户限制**: 最多10人
- **存储方式**: SQLite本地存储

### 数据约束
- **股票池**: 近10年存续A股约3000只
- **数据频率**: 周频截面（每周最后一个交易日）
- **因子数量**: 10~30个基础因子
- **标签定义**: 未来一周收益率
- **无未来信息**: 因子计算严格避免未来数据泄露

## 数据库表结构

### 核心数据表
1. **股票基础信息表**: 股票代码、名称、行业、上市日期等
2. **因子数据表**: 股票代码、日期、各因子值、未来收益率
3. **回测结果表**: 策略名称、日期、净值、持仓明细、指标值
4. **影子账户表**: 账户ID、持仓股票、数量、成本价
5. **AI建议记录表**: 账户ID、日期、建议内容、模型得分

## API端点规范

### RESTful API设计
- `GET /api/health` - 健康检查
- `POST /api/predict` - 模型预测
- `GET /api/backtest/results` - 获取回测结果
- `GET /api/account/{account_id}` - 获取账户信息
- `POST /api/account/{account_id}/position` - 更新持仓
- `GET /api/realtime_advice` - 实时建议（SSE流式）

## 执行模型分配

| 阶段 | 推荐执行模型 |
|-----|-------------|
| 阶段1 | GLM-5（后端/规范）、Doubao-Seed-2.0-Code（前端UI） |
| 阶段2 | GLM-5（数据处理）、DeepSeek-V3.1-Terminus（性能优化） |
| 阶段3 | GLM-5（模型训练）、Kimi K2.5（跨文件依赖） |
| 阶段4 | GLM-5（回测逻辑）、DeepSeek-V3.1-Terminus（性能优化） |
| 阶段5 | GLM-5（后端业务）、Kimi K2.5（集成分析） |
| 阶段6 | Doubao-Seed-2.0-Code（前端开发） |

## 项目目录结构

```
d:\量化\V2.0\
├── backend/                 # 后端代码
│   ├── src/                 # 源代码
│   │   ├── api/             # API路由
│   │   ├── database/        # 数据库模型
│   │   ├── schemas/         # 数据模式
│   │   └── utils/           # 工具函数
│   ├── data/                # 数据文件
│   ├── models/              # 模型文件
│   ├── tests/               # 测试文件
│   └── requirements.txt     # 依赖清单
├── frontend/                # 前端代码
│   ├── src/                 # 源代码
│   │   ├── hooks/           # 自定义Hooks
│   │   ├── services/        # API服务
│   │   └── types/           # 类型定义
│   └── package.json         # 依赖清单
├── docs/                    # 文档
│   └── 开发规范手册.md
└── 需求文档.md              # 原始需求文档
```
