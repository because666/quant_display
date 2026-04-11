"""回测结果API：查询回测历史、获取最新回测指标与净值曲线"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BACKTEST_RESULTS_DIR = DATA_DIR / "backtest_results"


@router.get("/results")
def get_backtest_results(
    model_type: str | None = Query(default=None, description="模型类型筛选: lightgbm 或 xgboost"),
    limit: int = Query(default=10, ge=1, le=100, description="返回条数"),
) -> dict[str, Any]:
    """获取回测结果列表（从SQLite读取）"""
    try:
        from src.db import init_db, session_scope
        from src.db.models import BacktestResult

        init_db()
        results = []
        with session_scope() as session:
            query = session.query(BacktestResult).order_by(BacktestResult.id.desc())
            if model_type:
                query = query.filter(BacktestResult.model_type == model_type)
            rows = query.limit(limit).all()
            for row in rows:
                metrics = json.loads(row.metrics_json) if row.metrics_json else {}
                results.append({
                    "id": row.id,
                    "model_type": row.model_type,
                    "created_at": str(row.created_at) if row.created_at else None,
                    "metrics": metrics,
                })

        return {"code": 200, "data": {"results": results, "count": len(results)}}
    except Exception as e:
        logger.exception("查询回测结果失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/results/{result_id}")
def get_backtest_detail(result_id: int) -> dict[str, Any]:
    """获取单条回测结果详情（含净值曲线和持仓）"""
    try:
        from src.db import init_db, session_scope
        from src.db.models import BacktestResult

        init_db()
        with session_scope() as session:
            row = session.query(BacktestResult).filter(BacktestResult.id == result_id).first()
            if not row:
                raise HTTPException(status_code=404, detail=f"回测结果 {result_id} 不存在")

            nav_data = json.loads(row.nav_json) if row.nav_json else {}
            metrics = json.loads(row.metrics_json) if row.metrics_json else {}
            params = json.loads(row.params_json) if row.params_json else {}

            return {
                "code": 200,
                "data": {
                    "id": row.id,
                    "model_type": row.model_type,
                    "created_at": str(row.created_at) if row.created_at else None,
                    "metrics": metrics,
                    "params": params,
                    "nav": nav_data,
                },
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("查询回测详情失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/latest")
def get_latest_backtest() -> dict[str, Any]:
    """获取最新回测结果（含净值曲线和指标）"""
    try:
        from src.db import init_db, session_scope
        from src.db.models import BacktestResult

        init_db()
        results = {}
        with session_scope() as session:
            for model_type in ("lightgbm", "xgboost"):
                row = (
                    session.query(BacktestResult)
                    .filter(BacktestResult.model_type == model_type)
                    .order_by(BacktestResult.id.desc())
                    .first()
                )
                if row:
                    nav_data = json.loads(row.nav_json) if row.nav_json else {}
                    metrics = json.loads(row.metrics_json) if row.metrics_json else {}
                    results[model_type] = {
                        "id": row.id,
                        "metrics": metrics,
                        "nav_points": nav_data.get("nav_points", []),
                        "created_at": str(row.created_at) if row.created_at else None,
                    }

        return {"code": 200, "data": results}
    except Exception as e:
        logger.exception("查询最新回测结果失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/comparison")
def get_backtest_comparison() -> dict[str, Any]:
    """获取双模型对比数据"""
    try:
        comparison_path = BACKTEST_RESULTS_DIR / "comparison.json"
        nav_path = BACKTEST_RESULTS_DIR / "comparison_nav.json"

        comparison = {}
        if comparison_path.exists():
            with open(comparison_path, "r", encoding="utf-8") as f:
                comparison = json.load(f)

        nav_comparison = {}
        if nav_path.exists():
            with open(nav_path, "r", encoding="utf-8") as f:
                nav_comparison = json.load(f)

        return {
            "code": 200,
            "data": {
                "comparison": comparison,
                "nav_comparison": nav_comparison,
            },
        }
    except Exception as e:
        logger.exception("查询对比数据失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/model-info")
def get_model_analysis() -> dict[str, Any]:
    """获取模型分析数据（特征重要性、NDCG曲线等）"""
    try:
        models_dir = PROJECT_ROOT / "models"
        result: dict[str, Any] = {}

        from src.data_loader import load_factor_columns
        factor_cols = load_factor_columns(data_dir=DATA_DIR)
        fkey_map = {f"f{i}": name for i, name in enumerate(factor_cols)}

        for model_type in ("lightgbm", "xgboost"):
            fi_path = models_dir / f"{model_type}_feature_importance.json"
            metrics_path = models_dir / f"{model_type}_metrics.json"

            model_data: dict[str, Any] = {}
            if fi_path.exists():
                with open(fi_path, "r", encoding="utf-8") as f:
                    fi = json.load(f)
                mapped = {}
                for k, v in fi.items():
                    mapped[fkey_map.get(k, k)] = v
                ranked = sorted(mapped.items(), key=lambda x: -x[1])
                model_data["feature_importance"] = [
                    {"feature": k, "importance": v} for k, v in ranked
                ]
            if metrics_path.exists():
                with open(metrics_path, "r", encoding="utf-8") as f:
                    model_data["metrics"] = json.load(f)

            result[model_type] = model_data

        eval_path = models_dir / "evaluation_metrics.json"
        if eval_path.exists():
            with open(eval_path, "r", encoding="utf-8") as f:
                result["evaluation"] = json.load(f)

        return {"code": 200, "data": result}
    except Exception as e:
        logger.exception("查询模型分析数据失败")
        raise HTTPException(status_code=500, detail=str(e)) from e
