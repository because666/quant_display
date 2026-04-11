"""
DeepSeek 兼容 Chat Completions 流式封装（支持聚合站 / 中转 URL）。

配置优先从环境变量读取（``os.getenv``）；若未设置，则回退到 ``get_settings()`` 中的
``deepseek_*`` 字段（与 ``.env`` + pydantic-settings 一致）。**禁止在代码中硬编码 API 密钥。**
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from src.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_STREAM_TIMEOUT_S = 120.0


class DeepSeekStreamError(RuntimeError):
    """流式调用配置错误或不可恢复失败。"""


class DeepSeekAuthError(DeepSeekStreamError):
    """API Key 无效或未配置。"""


def _env_or_settings(key: str, fallback: str = "") -> str:
    v = os.getenv(key)
    if v is not None and str(v).strip():
        return str(v).strip()
    s = get_settings()
    if key == "DEEPSEEK_API_KEY":
        return (s.deepseek_api_key or "").strip()
    if key == "DEEPSEEK_BASE_URL":
        return (s.deepseek_base_url or "").strip().rstrip("/")
    if key == "DEEPSEEK_MODEL":
        return (s.deepseek_model or "").strip() or fallback
    return fallback


def _api_key() -> str:
    return _env_or_settings("DEEPSEEK_API_KEY")


def _base_url() -> str:
    u = _env_or_settings("DEEPSEEK_BASE_URL")
    if not u:
        return ""
    u = u.rstrip("/")
    if not u.endswith("/v1") and not u.endswith("/v1/"):
        u = u + "/v1"
    return u


def _model_name() -> str:
    m = _env_or_settings("DEEPSEEK_MODEL", DEFAULT_MODEL)
    return m or DEFAULT_MODEL


def _require_config() -> tuple[str, str]:
    key = _api_key()
    base = _base_url()
    if not key:
        raise DeepSeekAuthError(
            "未配置 DEEPSEEK_API_KEY：请在环境变量或 .env（pydantic）中设置，且勿将密钥写入代码仓库。"
        )
    if not base:
        raise DeepSeekStreamError(
            "未配置 DEEPSEEK_BASE_URL：聚合站需设置完整 base URL（例如 https://api.example.com/v1 或服务商文档给定地址）。"
        )
    return key, base


def create_async_client(*, timeout_s: float = DEFAULT_STREAM_TIMEOUT_S) -> AsyncOpenAI:
    key, base = _require_config()
    return AsyncOpenAI(api_key=key, base_url=base, timeout=timeout_s, max_retries=0)


def create_sync_client(*, timeout_s: float = DEFAULT_STREAM_TIMEOUT_S) -> OpenAI:
    key, base = _require_config()
    return OpenAI(api_key=key, base_url=base, timeout=timeout_s, max_retries=0)


async def _stream_with_client(cli: AsyncOpenAI, params: dict[str, Any]) -> AsyncIterator[str]:
    stream = await cli.chat.completions.create(**params)
    async for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        if delta is None:
            continue
        content = getattr(delta, "content", None)
        if content:
            yield content


async def _iter_text_deltas(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    client: AsyncOpenAI | None = None,
    extra_params: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """底层：仅产出模型返回的文本增量（不含 SSE 包装）。"""
    use_model = model or _model_name()
    params: dict[str, Any] = {"model": use_model, "messages": messages, "stream": True}
    if extra_params:
        params.update(extra_params)

    try:
        if client is not None:
            async for piece in _stream_with_client(client, params):
                yield piece
        else:
            key, base = _require_config()
            async with AsyncOpenAI(
                api_key=key,
                base_url=base,
                timeout=DEFAULT_STREAM_TIMEOUT_S,
            ) as cli:
                async for piece in _stream_with_client(cli, params):
                    yield piece
    except AuthenticationError as exc:
        logger.warning("DeepSeek 鉴权失败: %s", exc)
        raise DeepSeekAuthError("API 密钥无效或未授权，请检查 DEEPSEEK_API_KEY。") from exc
    except (APITimeoutError, APIConnectionError) as exc:
        logger.exception("DeepSeek 网络/超时: %s", exc)
        raise DeepSeekStreamError(f"调用聚合站网络异常或超时: {exc}") from exc
    except RateLimitError as exc:
        logger.warning("DeepSeek 限流: %s", exc)
        raise DeepSeekStreamError(f"请求被限流: {exc}") from exc
    except APIStatusError as exc:
        logger.exception("DeepSeek HTTP 错误: %s", exc)
        raise DeepSeekStreamError(f"聚合站返回错误: {exc}") from exc


async def stream_advice(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    client: AsyncOpenAI | None = None,
    extra_params: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """
    异步流式输出，**每条为 SSE 风格数据行**（便于 FastAPI ``StreamingResponse`` 直接 write）::

        data: {"content": "片段文本"}\\n\\n

    解析方按行读取 ``data:`` 后 JSON，拼接所有 ``content`` 即完整 Markdown。
    """
    async for piece in _iter_text_deltas(messages, model=model, client=client, extra_params=extra_params):
        line = json.dumps({"content": piece}, ensure_ascii=False)
        yield f"data: {line}\n\n"


async def collect_markdown(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    client: AsyncOpenAI | None = None,
    extra_params: dict[str, Any] | None = None,
) -> str:
    """将流式文本增量拼接为完整字符串（通常为 Markdown）。"""
    parts: list[str] = []
    async for piece in _iter_text_deltas(messages, model=model, client=client, extra_params=extra_params):
        parts.append(piece)
    return "".join(parts)


def get_advice_sync(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> str:
    """
    同步封装：在事件循环中跑 ``collect_markdown``，供脚本/简单测试使用。
    若当前线程已有运行中的 loop，请改用 ``await collect_markdown(...)``。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(collect_markdown(messages, model=model, extra_params=extra_params))
    raise DeepSeekStreamError("get_advice_sync() 不能在已有事件循环的线程内调用，请 await collect_markdown()。")


def parse_sse_chunk(line: str) -> str | None:
    """
    解析单行 ``data: {...}``，返回 JSON 中的 ``content``；非数据行返回 None。
    """
    s = line.strip()
    if not s.startswith("data:"):
        return None
    payload = s[5:].strip()
    if payload == "[DONE]":
        return None
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return None
    c = obj.get("content")
    return str(c) if c is not None else None


def iter_sse_payloads(sse_text: str) -> Iterator[str]:
    """将含多条 ``data:`` 块的文本解析为 content 片段序列（测试用）。"""
    for line in sse_text.splitlines():
        if line.startswith("data:"):
            c = parse_sse_chunk(line)
            if c is not None:
                yield c


def _sync_stream_text(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> Iterator[str]:
    """使用同步 OpenAI 客户端迭代流（测试/无 asyncio 场景）。"""
    cli = create_sync_client()
    use_model = model or _model_name()
    params: dict[str, Any] = {"model": use_model, "messages": messages, "stream": True}
    if extra_params:
        params.update(extra_params)
    try:
        stream = cli.chat.completions.create(**params)
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if content:
                yield content
    except AuthenticationError as exc:
        raise DeepSeekAuthError("API 密钥无效或未授权，请检查 DEEPSEEK_API_KEY。") from exc
    except (APITimeoutError, APIConnectionError, APIStatusError, RateLimitError) as exc:
        raise DeepSeekStreamError(str(exc)) from exc
    finally:
        cli.close()


def get_advice_sync_blocking(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> str:
    """
    纯同步流式读取并拼接（不创建 asyncio loop），适合在已有事件循环环境（如 Jupyter）下测试。
    """
    return "".join(_sync_stream_text(messages, model=model, extra_params=extra_params))
