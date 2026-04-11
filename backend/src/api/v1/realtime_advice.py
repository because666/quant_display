"""实时 AI 投资建议：SSE 流式输出（DeepSeek 兼容），并写入 ``ai_advice`` 表。"""
from __future__ import annotations

import asyncio
import json
import logging
import math
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.account import (
    E_DUPLICATE_ACCOUNT_NAME,
    E_MAX_ACCOUNTS_EXCEEDED,
    create_account,
    get_account_by_name,
)
from src.data_fetcher import _normalize_stock_code, load_cached_data
from src.database.database import SessionLocal
from src.database.models import AIAdvice, ShadowAccount
from src import deepseek_stream as ds
from src import price_range as pr_mod
from src import realtime_updater as rt
from src.api.v1.deps import get_predictor
from src.predictor import ModelPredictor, load_prediction_data
from src.prompt_builder import build_user_prompt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["advice"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class RealtimeAdviceRequest(BaseModel):
    account_name: str = Field(..., min_length=1, max_length=128, description="影子账户名（不存在则自动创建）")
    refresh: bool = Field(
        True,
        description="True：拉取最新日线并计算当前截面因子（较慢）；False：使用本地缓存截面（较快）",
    )


def _sse_error_payload(message: str, *, code: str = "error") -> str:
    return f"data: {json.dumps({'error': True, 'code': code, 'message': message}, ensure_ascii=False)}\n\n"


def _batch_last_closes(codes: list[str]) -> dict[str, float]:
    """按规范化代码缓存最近收盘价。"""
    out: dict[str, float] = {}
    seen: set[str] = set()
    for raw in codes:
        key = _normalize_stock_code(raw)
        if key in seen:
            continue
        seen.add(key)
        try:
            df = load_cached_data(key)
            if df is None or df.empty or "close" not in df.columns:
                continue
            cl = float(pd.to_numeric(df["close"], errors="coerce").iloc[-1])
            if math.isfinite(cl) and cl > 0:
                out[key] = cl
        except Exception as exc:  # noqa: BLE001
            logger.debug("收盘价缺失 %s: %s", key, exc)
    return out


def _build_price_ranges_dict(codes: list[str], close_map: dict[str, float]) -> dict[str, dict[str, Any]]:
    ranges: dict[str, dict[str, Any]] = {}
    for c in codes:
        key = _normalize_stock_code(c)
        px = close_map.get(key)
        if px is None or not math.isfinite(px) or px <= 0:
            ranges[c] = {}
            continue
        try:
            ranges[c] = pr_mod.get_price_range(c, px)
        except Exception as exc:  # noqa: BLE001
            logger.warning("价格区间计算失败 %s: %s", c, exc)
            ranges[c] = {}
    return ranges


def _resolve_or_create_account(account_name: str) -> tuple[int | None, str | None]:
    """返回 (account_id, error_message)。"""
    name = account_name.strip()
    if not name:
        return None, "account_name 不能为空"

    gr = get_account_by_name(name)
    if gr.ok and gr.value:
        return int(gr.value["id"]), None

    cr = create_account(name, holdings=[])
    if cr.ok and cr.value:
        return int(cr.value["id"]), None

    if cr.error_code == E_DUPLICATE_ACCOUNT_NAME:
        gr2 = get_account_by_name(name)
        if gr2.ok and gr2.value:
            return int(gr2.value["id"]), None
        return None, "账户创建竞态后仍无法读取"

    if cr.error_code == E_MAX_ACCOUNTS_EXCEEDED:
        return None, cr.message or "影子账户数量已达上限（10）"

    return None, cr.message or "无法创建影子账户"


def _load_holdings_list(account_id: int) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        acc = session.get(ShadowAccount, account_id)
        if acc is None:
            return []
        h = acc.holdings
        if isinstance(h, list):
            return list(h)
        return []


def _persist_advice(
    account_id: int,
    advice_markdown: str,
    top_stocks: list[dict[str, Any]],
    context_snapshot: dict[str, Any],
) -> None:
    with SessionLocal() as session:
        session.add(
            AIAdvice(
                account_id=account_id,
                advice_markdown=advice_markdown,
                top_stocks=top_stocks,
                context_snapshot=context_snapshot,
            )
        )
        session.commit()


async def _load_factor_frame(refresh: bool, predictor: ModelPredictor) -> tuple[pd.DataFrame, str]:
    """加载因子截面数据（优先使用本地parquet，避免触发akshare下载）"""
    from src.api.v1.stockpool import _load_section

    df, section = await asyncio.to_thread(
        _load_section, predictor._data_dir, None
    )
    if df.empty:
        raise RuntimeError("截面数据为空")
    return df, str(section)


@router.post("/realtime_advice")
async def post_realtime_advice(
    request: Request,
    body: RealtimeAdviceRequest,
    predictor: Annotated[ModelPredictor, Depends(get_predictor)],
) -> StreamingResponse:
    """
    SSE（``text/event-stream``）：流式输出 DeepSeek 返回的 Markdown 片段（``data: {"content":"..."}\\n\\n``），
    结束时写入 ``ai_advice``。失败时推送 ``data: {"error":true,...}\\n\\n``。
    """

    async def event_stream() -> Any:
        account_id: int | None = None
        collected: list[str] = []
        top_for_db: list[dict[str, Any]] = []
        context_snapshot: dict[str, Any] = {}

        try:
            aid, err = await asyncio.to_thread(_resolve_or_create_account, body.account_name)
            if err or aid is None:
                yield _sse_error_payload(err or "账户解析失败", code="account")
                return
            account_id = aid

            factor_df, section_date = await _load_factor_frame(body.refresh, predictor)

            top_df = await asyncio.to_thread(
                lambda: predictor.get_top_stocks(factor_df, top_n=10, with_contributions=False)
            )
            if top_df.empty:
                err_msg = "当前截面无有效预测结果"
                yield _sse_error_payload(err_msg, code="predict")
                await asyncio.to_thread(
                    _persist_advice,
                    account_id,
                    f"[错误] {err_msg}",
                    [],
                    {
                        "section_date": section_date,
                        "model_type": predictor.model_type,
                        "refresh": body.refresh,
                        "account_name": body.account_name.strip(),
                        "error": "empty_top",
                    },
                )
                return

            top_for_db = [
                {"stock_code": str(r["stock_code"]), "score": float(r["score"])}
                for _, r in top_df.iterrows()
            ]

            raw_holdings = await asyncio.to_thread(_load_holdings_list, account_id)

            codes: set[str] = set()
            for row in top_for_db:
                codes.add(row["stock_code"])
            for h in raw_holdings:
                c = h.get("code") or h.get("stock_code")
                if c:
                    codes.add(str(c))

            close_map = await asyncio.to_thread(_batch_last_closes, list(codes))
            price_ranges = await asyncio.to_thread(_build_price_ranges_dict, list(codes), close_map)

            holdings_prompt: list[dict[str, Any]] = []
            for h in raw_holdings:
                c = str(h.get("code") or h.get("stock_code") or "")
                if not c:
                    continue
                nk = _normalize_stock_code(c)
                px = close_map.get(nk)
                cur = float(px) if px is not None and math.isfinite(px) else float("nan")
                holdings_prompt.append(
                    {
                        "code": c,
                        "name": str(h.get("name", "")),
                        "quantity": float(h.get("quantity", 0) or 0),
                        "cost": float(h.get("cost", 0) or 0),
                        "current_price": cur,
                    }
                )

            fi = await asyncio.to_thread(predictor.get_feature_importance)
            messages = build_user_prompt(top_for_db, holdings_prompt, price_ranges, fi)

            context_snapshot = {
                "section_date": section_date,
                "model_type": predictor.model_type,
                "refresh": body.refresh,
                "account_name": body.account_name.strip(),
                "feature_importance_top5": sorted(fi.items(), key=lambda x: float(x[1]), reverse=True)[:5],
                "price_range_keys": list(price_ranges.keys()),
            }

            logger.info(
                "SSE realtime_advice start | account_id=%s | client=%s | refresh=%s",
                account_id,
                request.client.host if request.client else "?",
                body.refresh,
            )

            async for chunk in ds.stream_advice(messages):
                collected.append(chunk)
                yield chunk

            full_md = "".join(ds.iter_sse_payloads("".join(collected)))
            await asyncio.to_thread(
                _persist_advice,
                account_id,
                full_md if full_md.strip() else "(模型未返回可见正文)",
                top_for_db,
                context_snapshot,
            )
            yield "data: [DONE]\n\n"

        except ds.DeepSeekAuthError as exc:
            logger.warning("DeepSeek 鉴权失败: %s", exc)
            yield _sse_error_payload(str(exc), code="auth")
        except ds.DeepSeekStreamError as exc:
            logger.exception("DeepSeek 调用失败: %s", exc)
            yield _sse_error_payload(str(exc), code="llm")
        except Exception as exc:  # noqa: BLE001
            logger.exception("realtime_advice 失败: %s", exc)
            yield _sse_error_payload(str(exc), code="internal")
            if account_id is not None and collected:
                try:
                    partial_md = "".join(ds.iter_sse_payloads("".join(collected)))
                    ctx = {**context_snapshot, "truncated": True, "error": str(exc)}
                    await asyncio.to_thread(
                        _persist_advice,
                        account_id,
                        partial_md or f"[流中断] {exc}",
                        top_for_db,
                        ctx,
                    )
                except Exception as save_exc:  # noqa: BLE001
                    logger.exception("保存中断结果失败: %s", save_exc)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=dict(SSE_HEADERS),
    )
