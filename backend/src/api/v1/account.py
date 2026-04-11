"""
影子账户管理 API：CRUD 操作，供前端调用。
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.account import (
    E_ACCOUNT_NOT_FOUND,
    E_DATABASE_ERROR,
    E_DUPLICATE_ACCOUNT_NAME,
    E_INVALID_ACCOUNT_NAME,
    E_INVALID_HOLDINGS,
    E_MAX_ACCOUNTS_EXCEEDED,
    create_account,
    delete_account,
    get_account,
    get_account_by_name,
    list_accounts,
    update_holdings,
    update_ranges,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["account"])


class CreateAccountRequest(BaseModel):
    """创建账户请求"""
    account_name: str = Field(..., min_length=1, max_length=128, description="账户名称")
    holdings: list[dict[str, Any]] | None = Field(default=None, description="初始持仓")
    backtest_start: str | None = Field(default=None, description="回测开始日期 YYYY-MM-DD")
    backtest_end: str | None = Field(default=None, description="回测结束日期 YYYY-MM-DD")
    prediction_start: str | None = Field(default=None, description="预测开始日期 YYYY-MM-DD")
    prediction_end: str | None = Field(default=None, description="预测结束日期 YYYY-MM-DD")


class UpdateHoldingsRequest(BaseModel):
    """更新持仓请求"""
    holdings: list[dict[str, Any]] = Field(..., description="新持仓列表")


class UpdateRangesRequest(BaseModel):
    """更新时间区间请求"""
    backtest_start: str | None = Field(default=None, description="回测开始日期")
    backtest_end: str | None = Field(default=None, description="回测结束日期")
    prediction_start: str | None = Field(default=None, description="预测开始日期")
    prediction_end: str | None = Field(default=None, description="预测结束日期")


def _parse_date(s: str | None) -> date | None:
    """解析日期字符串"""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _error_response(error_code: str, message: str) -> dict[str, Any]:
    """统一错误响应格式"""
    return {"code": 400, "message": message, "error_code": error_code, "data": None}


@router.post("/")
def api_create_account(body: CreateAccountRequest) -> dict[str, Any]:
    """
    创建影子账户
    
    - account_name: 账户名称（唯一）
    - holdings: 初始持仓列表，每项包含 code, name, quantity, cost
    - backtest_start/end: 回测时间范围
    - prediction_start/end: 预测时间范围
    """
    logger.info("POST /account | name=%s", body.account_name)
    
    backtest_range = None
    if body.backtest_start or body.backtest_end:
        backtest_range = (_parse_date(body.backtest_start), _parse_date(body.backtest_end))
    
    prediction_range = None
    if body.prediction_start or body.prediction_end:
        prediction_range = (_parse_date(body.prediction_start), _parse_date(body.prediction_end))
    
    result = create_account(
        account_name=body.account_name,
        holdings=body.holdings,
        backtest_range=backtest_range,
        prediction_range=prediction_range,
    )
    
    if result.ok:
        return {"code": 200, "message": "创建成功", "data": result.value}
    
    if result.error_code == E_DUPLICATE_ACCOUNT_NAME:
        raise HTTPException(status_code=409, detail=result.message)
    if result.error_code == E_MAX_ACCOUNTS_EXCEEDED:
        raise HTTPException(status_code=403, detail=result.message)
    if result.error_code in (E_INVALID_ACCOUNT_NAME, E_INVALID_HOLDINGS):
        raise HTTPException(status_code=400, detail=result.message)
    
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/")
def api_list_accounts() -> dict[str, Any]:
    """
    列出所有影子账户（基本信息）
    """
    logger.info("GET /account")
    result = list_accounts()
    return {"code": 200, "message": "success", "data": result}


@router.get("/{account_id}")
def api_get_account(account_id: int) -> dict[str, Any]:
    """
    获取账户详情（含持仓）
    """
    logger.info("GET /account/%s", account_id)
    result = get_account(account_id)
    
    if result.ok:
        return {"code": 200, "message": "success", "data": result.value}
    
    if result.error_code == E_ACCOUNT_NOT_FOUND:
        raise HTTPException(status_code=404, detail=result.message)
    
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/name/{account_name}")
def api_get_account_by_name(account_name: str) -> dict[str, Any]:
    """
    按名称获取账户详情
    """
    logger.info("GET /account/name/%s", account_name)
    result = get_account_by_name(account_name)
    
    if result.ok:
        return {"code": 200, "message": "success", "data": result.value}
    
    if result.error_code == E_ACCOUNT_NOT_FOUND:
        raise HTTPException(status_code=404, detail=result.message)
    
    raise HTTPException(status_code=500, detail=result.message)


@router.put("/{account_id}/holdings")
def api_update_holdings(account_id: int, body: UpdateHoldingsRequest) -> dict[str, Any]:
    """
    更新账户持仓（整体替换）
    """
    logger.info("PUT /account/%s/holdings | count=%s", account_id, len(body.holdings))
    result = update_holdings(account_id, body.holdings)
    
    if result.ok:
        return {"code": 200, "message": "更新成功", "data": result.value}
    
    if result.error_code == E_ACCOUNT_NOT_FOUND:
        raise HTTPException(status_code=404, detail=result.message)
    if result.error_code == E_INVALID_HOLDINGS:
        raise HTTPException(status_code=400, detail=result.message)
    
    raise HTTPException(status_code=500, detail=result.message)


@router.put("/{account_id}/ranges")
def api_update_ranges(account_id: int, body: UpdateRangesRequest) -> dict[str, Any]:
    """
    更新账户时间区间
    """
    logger.info("PUT /account/%s/ranges", account_id)
    result = update_ranges(
        account_id=account_id,
        backtest_start=_parse_date(body.backtest_start),
        backtest_end=_parse_date(body.backtest_end),
        prediction_start=_parse_date(body.prediction_start),
        prediction_end=_parse_date(body.prediction_end),
    )
    
    if result.ok:
        return {"code": 200, "message": "更新成功", "data": result.value}
    
    if result.error_code == E_ACCOUNT_NOT_FOUND:
        raise HTTPException(status_code=404, detail=result.message)
    
    raise HTTPException(status_code=500, detail=result.message)


@router.delete("/{account_id}")
def api_delete_account(account_id: int) -> dict[str, Any]:
    """
    删除账户（级联删除关联的AI建议）
    """
    logger.info("DELETE /account/%s", account_id)
    result = delete_account(account_id)
    
    if result.ok:
        return {"code": 200, "message": "删除成功", "data": None}
    
    if result.error_code == E_ACCOUNT_NOT_FOUND:
        raise HTTPException(status_code=404, detail=result.message)
    
    raise HTTPException(status_code=500, detail=result.message)
