"""模型预测 API：供前端与 AI 推荐服务调用。"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.v1.deps import get_predictor
from src.predictor import ModelPredictor, load_prediction_data

logger = logging.getLogger(__name__)

router = APIRouter(tags=["predict"])


class PredictRequest(BaseModel):
    """可选：限定股票池、截面日期、返回 Top N。"""

    stock_codes: list[str] | None = Field(default=None, description="仅对这些代码打分；为空则全截面")
    date: str | None = Field(default=None, description="截面日期 YYYY-MM-DD，传给实时因子加载")
    top_n: int = Field(default=20, ge=1, le=500)


@router.post("/predict")
def post_predict(
    request: Request,
    body: PredictRequest,
    predictor: Annotated[ModelPredictor, Depends(get_predictor)],
) -> dict[str, Any]:
    logger.info(
        "POST /predict | client=%s | stock_codes=%s | date=%s | top_n=%s",
        request.client.host if request.client else "?",
        body.stock_codes,
        body.date,
        body.top_n,
    )
    try:
        df, timestamp = load_prediction_data(data_dir=predictor._data_dir, latest_date=body.date)
    except Exception as e:
        logger.exception("加载预测数据失败")
        raise HTTPException(status_code=503, detail=f"无法加载预测数据: {e}") from e

    if body.stock_codes:
        want = {str(x).strip() for x in body.stock_codes}
        df = df[df["stock_code"].astype(str).isin(want)].copy()
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="给定股票列表在当前因子截面中无匹配数据",
            )

    try:
        top = predictor.get_top_stocks(df, top_n=body.top_n, with_contributions=False)
    except Exception as e:
        logger.exception("模型预测失败")
        raise HTTPException(status_code=500, detail=str(e)) from e

    top_stocks = [{"code": str(r["stock_code"]), "score": float(r["score"])} for _, r in top.iterrows()]
    feature_importance = predictor.get_feature_importance()
    return {
        "code": 200,
        "data": {
            "top_stocks": top_stocks,
            "feature_importance": feature_importance,
            "timestamp": timestamp,
        },
    }


@router.get("/model/info")
def get_model_info(
    request: Request,
    predictor: Annotated[ModelPredictor, Depends(get_predictor)],
) -> dict[str, Any]:
    logger.info("GET /model/info | client=%s", request.client.host if request.client else "?")
    fi = predictor.get_feature_importance()
    ranked = sorted(fi.items(), key=lambda x: -x[1])
    feature_importance_list = [{"feature": k, "importance": v} for k, v in ranked]
    return {
        "code": 200,
        "data": {
            "model_type": predictor.model_type,
            "trained_at": predictor.get_model_trained_at(),
            "feature_importance": fi,
            "feature_importance_list": feature_importance_list,
        },
    }
