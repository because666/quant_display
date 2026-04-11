"""
简化版后端API服务器
用于前端集成测试，不依赖模型文件
"""
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(
    title="Quant Stock Ranking API (Mock)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    codes: list[str]
    date: str


class AccountCreate(BaseModel):
    name: str


class HoldingUpdate(BaseModel):
    code: str
    name: str
    quantity: int
    cost_price: float
    current_price: float


class AccountUpdate(BaseModel):
    holdings: list[HoldingUpdate]
    backtest_range: dict
    predict_range: dict


MOCK_ACCOUNTS: dict[str, dict] = {}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/v1/predict")
async def predict(request: PredictRequest):
    import random

    results = []
    for code in request.codes:
        results.append({
            "code": code,
            "score": round(random.uniform(0, 1), 4),
            "rank": random.randint(1, len(request.codes)),
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return {"date": request.date, "predictions": results}


@app.get("/api/v1/account/{name}")
async def get_account(name: str):
    if name not in MOCK_ACCOUNTS:
        return {
            "name": name,
            "total_assets": 1000000,
            "holding_value": 0,
            "available_cash": 1000000,
            "total_profit": 0,
            "return_rate": 0,
            "holdings": [],
            "backtest_range": {"start_date": "2020-01-01", "end_date": "2024-12-31"},
            "predict_range": {"start_date": "2025-01-01", "end_date": "2025-03-31"},
        }
    return MOCK_ACCOUNTS[name]


@app.post("/api/v1/account")
async def create_account(request: AccountCreate):
    if request.name in MOCK_ACCOUNTS:
        raise HTTPException(status_code=400, detail="账户已存在")

    MOCK_ACCOUNTS[request.name] = {
        "name": request.name,
        "total_assets": 1000000,
        "holding_value": 0,
        "available_cash": 1000000,
        "total_profit": 0,
        "return_rate": 0,
        "holdings": [],
        "backtest_range": {"start_date": "2020-01-01", "end_date": "2024-12-31"},
        "predict_range": {"start_date": "2025-01-01", "end_date": "2025-03-31"},
    }
    return {"message": "账户创建成功", "name": request.name}


@app.put("/api/v1/account/{name}")
async def update_account(name: str, request: AccountUpdate):
    if name not in MOCK_ACCOUNTS:
        MOCK_ACCOUNTS[name] = {
            "name": name,
            "total_assets": 1000000,
            "holding_value": 0,
            "available_cash": 1000000,
            "total_profit": 0,
            "return_rate": 0,
            "holdings": [],
        }

    holdings = [h.model_dump() for h in request.holdings]
    total_value = sum(h["quantity"] * h["current_price"] for h in holdings)
    total_cost = sum(h["quantity"] * h["cost_price"] for h in holdings)
    total_profit = total_value - total_cost

    MOCK_ACCOUNTS[name].update({
        "holdings": holdings,
        "holding_value": total_value,
        "total_profit": total_profit,
        "return_rate": total_profit / total_cost if total_cost > 0 else 0,
        "backtest_range": request.backtest_range,
        "predict_range": request.predict_range,
    })

    return {"message": "账户更新成功", "account": MOCK_ACCOUNTS[name]}


@app.get("/api/v1/account/{name}/history")
async def get_account_history(name: str):
    return {
        "name": name,
        "history": [],
    }


@app.get("/api/v1/realtime_advice/{account_name}")
async def get_realtime_advice(account_name: str):
    async def generate_advice() -> AsyncGenerator[str, None]:
        advice_content = f"""# AI投资建议

## 账户分析

当前账户：**{account_name}**

### 市场概况

今日市场整体表现平稳，主要指数小幅波动。

### 持仓建议

1. **贵州茅台 (600519)**
   - 当前持仓：100股
   - 建议操作：持有
   - 目标价位：1850-1900元

2. **招商银行 (600036)**
   - 当前持仓：200股
   - 建议操作：逢低加仓
   - 目标价位：35-38元

### 风险提示

- 市场波动风险
- 政策变化风险
- 流动性风险

### 总结

建议保持当前仓位，关注市场动态，适时调整投资策略。

---
*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        for char in advice_content:
            yield f"data: {json.dumps({'content': char})}\n\n"
            await asyncio.sleep(0.02)

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate_advice(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
