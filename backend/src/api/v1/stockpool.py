"""股票池API：获取股票列表、模型排序选股、自定义股票池"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.api.v1.deps import get_predictor
from src.predictor import ModelPredictor
from src.data_loader import load_factor_columns, fill_missing_factors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stockpool", tags=["stockpool"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

_section_cache: dict[str, Any] = {}
_date_list_cache: list[str] | None = None
_stock_list_cache: list[dict[str, str]] | None = None


def _load_stock_list_from_meta(data_dir: Path) -> list[dict[str, str]]:
    """从 data/meta/surviving_stocks_*.parquet 加载股票列表（优先使用最大范围的文件）"""
    global _stock_list_cache
    if _stock_list_cache is not None:
        return _stock_list_cache

    meta_dir = data_dir / "meta"
    if meta_dir.exists():
        parquet_files = sorted(meta_dir.glob("surviving_stocks_*.parquet"), reverse=True)
        if parquet_files:
            try:
                df = pd.read_parquet(parquet_files[0])
                stock_list = []
                for _, row in df.iterrows():
                    stock_list.append({
                        "code": str(row.get("code", "")).strip(),
                        "name": str(row.get("name", "")).strip(),
                    })
                _stock_list_cache = stock_list
                return stock_list
            except Exception as e:
                logger.warning("从meta目录加载股票列表失败: %s", e)

    stock_list_path = data_dir / "stock_list.csv"
    if stock_list_path.exists():
        try:
            df = pd.read_csv(stock_list_path, dtype=str)
            stock_list = []
            for _, row in df.iterrows():
                stock_list.append({
                    "code": str(row.get("stock_code", row.get("代码", ""))).strip(),
                    "name": str(row.get("stock_name", row.get("名称", ""))).strip(),
                })
            _stock_list_cache = stock_list
            return stock_list
        except Exception as e:
            logger.warning("从stock_list.csv加载股票列表失败: %s", e)

    raw_dir = data_dir / "raw"
    if raw_dir.exists():
        parquet_files = sorted(raw_dir.glob("*.parquet"))
        codes = [f.stem for f in parquet_files if f.stem.isdigit() and len(f.stem) == 6]
        stock_list = [{"code": c, "name": ""} for c in codes]
        _stock_list_cache = stock_list
        return stock_list

    _stock_list_cache = []
    return []


def _find_parquet_files(data_dir: Path) -> list[Path]:
    """查找 data_dir 及其一级子目录中的 parquet 截面数据文件"""
    candidates = []
    for fname in ("test.parquet", "val.parquet", "train.parquet"):
        direct = data_dir / fname
        if direct.exists():
            candidates.append(direct)
        else:
            for sub_dir in (d for d in data_dir.iterdir() if d.is_dir()):
                p = sub_dir / fname
                if p.exists():
                    candidates.append(p)
                    break
    return candidates


def _get_available_dates(data_dir: Path) -> list[str]:
    """获取所有可用的截面日期列表（从parquet文件中提取）"""
    global _date_list_cache
    if _date_list_cache is not None:
        return _date_list_cache

    all_dates: list[pd.Timestamp] = []
    for path in _find_parquet_files(data_dir):
        try:
            df = pd.read_parquet(path, columns=["date"])
            if "date" not in df.columns:
                continue
            dates = pd.to_datetime(df["date"]).unique()
            all_dates.extend(dates)
        except Exception:
            continue

    all_dates = sorted(set(all_dates), reverse=True)
    result = [str(d.date()) for d in all_dates]
    _date_list_cache = result
    return result


def _load_section(data_dir: Path, date_str: str | None = None) -> tuple[pd.DataFrame, str]:
    """从本地parquet加载指定截面数据（不触发实时下载）"""
    cache_key = f"section_{date_str}"
    if cache_key in _section_cache:
        return _section_cache[cache_key]

    factor_cols = load_factor_columns(data_dir=data_dir)

    for path in _find_parquet_files(data_dir):
        try:
            df = pd.read_parquet(path)
        except Exception:
            continue
        if "date" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"])

        if date_str:
            target = pd.Timestamp(date_str)
            section = df[df["date"] == target]
        else:
            latest = df["date"].max()
            section = df[df["date"] == latest]

        if section.empty:
            continue

        cols = ["stock_code"] + [c for c in factor_cols if c in section.columns]
        result = section[cols].copy()
        timestamp = str(section["date"].iloc[0].date())

        _section_cache[cache_key] = (result, timestamp)
        return result, timestamp

    raise FileNotFoundError("未找到可用的截面数据文件")


class StockPoolRankRequest(BaseModel):
    """股票池排序请求"""
    model_type: str = Field(default="xgboost", description="模型类型: lightgbm 或 xgboost")
    top_n: int = Field(default=50, ge=1, le=500, description="返回排名前N只股票")
    stock_codes: list[str] | None = Field(default=None, description="自定义股票池，为空则使用全量股票")
    date: str | None = Field(default=None, description="截面日期 YYYY-MM-DD")


@router.get("/dates")
def get_available_dates(request: Request) -> dict[str, Any]:
    """获取所有可用的截面日期列表"""
    try:
        dates = _get_available_dates(DATA_DIR)
        return {
            "code": 200,
            "data": {
                "dates": dates,
                "total": len(dates),
                "latest": dates[0] if dates else None,
            },
        }
    except Exception as e:
        logger.exception("获取截面日期失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/list")
def get_stock_list(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=100, ge=1, le=1000, description="每页数量"),
    keyword: str | None = Query(default=None, description="股票代码或名称关键词筛选"),
) -> dict[str, Any]:
    """获取全部股票列表（分页），支持关键词搜索"""
    try:
        stock_list = _load_stock_list_from_meta(DATA_DIR)

        if keyword:
            keyword = keyword.strip()
            stock_list = [
                s for s in stock_list
                if keyword in s["code"] or keyword in s["name"]
            ]

        total = len(stock_list)
        start = (page - 1) * page_size
        end = start + page_size
        page_data = stock_list[start:end]

        return {
            "code": 200,
            "data": {
                "stocks": page_data,
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }
    except Exception as e:
        logger.exception("获取股票列表失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/count")
def get_stock_count(request: Request) -> dict[str, Any]:
    """获取股票池总数"""
    try:
        stock_list = _load_stock_list_from_meta(DATA_DIR)
        return {"code": 200, "data": {"total": len(stock_list)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/rank")
def rank_stocks(
    request: Request,
    body: StockPoolRankRequest,
    predictor: Annotated[ModelPredictor, Depends(get_predictor)],
) -> dict[str, Any]:
    """使用模型对股票池排序，返回Top N推荐股票。未指定自定义池时使用全量股票"""
    try:
        df, timestamp = _load_section(predictor._data_dir, date_str=body.date)
    except Exception as e:
        logger.exception("加载预测数据失败")
        raise HTTPException(status_code=503, detail=f"无法加载预测数据: {e}") from e

    if body.stock_codes:
        want = {str(x).strip() for x in body.stock_codes}
        df = df[df["stock_code"].astype(str).isin(want)].copy()
        if df.empty:
            raise HTTPException(status_code=400, detail="自定义股票池在当前截面中无匹配数据")
    else:
        all_stocks = _load_stock_list_from_meta(DATA_DIR)
        all_codes = {s["code"] for s in all_stocks} if all_stocks else set()
        section_codes = set(df["stock_code"].astype(str).unique())
        missing_codes = all_codes - section_codes

        if missing_codes:
            factor_cols = [c for c in load_factor_columns(data_dir=predictor._data_dir) if c in df.columns]
            empty_rows = []
            for code in sorted(missing_codes):
                row = {"stock_code": code}
                for col in factor_cols:
                    row[col] = 0.0
                empty_rows.append(row)
            if empty_rows:
                extra_df = pd.DataFrame(empty_rows)
                df = pd.concat([df, extra_df], ignore_index=True)
                logger.info("已补充 %d 只无因子数据的股票到排序池（因子值填充为0）", len(missing_codes))

    try:
        top = predictor.get_top_stocks(df, top_n=body.top_n, with_contributions=False)
    except Exception as e:
        logger.exception("模型排序失败")
        raise HTTPException(status_code=500, detail=str(e)) from e

    ranked_stocks = []
    for _, r in top.iterrows():
        ranked_stocks.append({
            "rank": int(r["rank"]),
            "code": str(r["stock_code"]),
            "score": float(r["score"]),
        })

    feature_importance = predictor.get_feature_importance()
    ranked_fi = sorted(feature_importance.items(), key=lambda x: -x[1])
    fi_list = [{"feature": k, "importance": v} for k, v in ranked_fi[:20]]

    return {
        "code": 200,
        "data": {
            "ranked_stocks": ranked_stocks,
            "feature_importance_top20": fi_list,
            "model_type": predictor.model_type,
            "timestamp": timestamp,
            "total_pool_size": len(df),
        },
    }
