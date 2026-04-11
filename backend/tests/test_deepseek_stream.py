"""deepseek_stream：SSE 封装与配置异常。"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import AuthenticationError

from src import deepseek_stream as ds


class _FakeAsyncStream:
    def __init__(self, parts: list[str]) -> None:
        self._parts = parts
        self._i = 0

    def __aiter__(self) -> "_FakeAsyncStream":
        self._i = 0
        return self

    async def __anext__(self) -> SimpleNamespace:
        if self._i >= len(self._parts):
            raise StopAsyncIteration
        t = self._parts[self._i]
        self._i += 1
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=t))])


def test_stream_advice_sse_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.com/v1")

    fake_client = AsyncMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_FakeAsyncStream(["## ", "操作建议", "\n"])
    )

    async def _run() -> list[str]:
        out: list[str] = []
        async for line in ds.stream_advice(
            [{"role": "user", "content": "hi"}],
            client=fake_client,
        ):
            out.append(line)
        return out

    out = asyncio.run(_run())
    assert all(x.startswith("data: ") and x.endswith("\n\n") for x in out)
    joined = "".join(ds.iter_sse_payloads("".join(out)))
    assert "## 操作建议" in joined


def test_collect_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.com/v1")
    fake_client = AsyncMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_FakeAsyncStream(["# ", "MD"]))
    text = asyncio.run(ds.collect_markdown([{"role": "user", "content": "x"}], client=fake_client))
    assert text == "# MD"


def test_parse_sse_chunk() -> None:
    assert ds.parse_sse_chunk('data: {"content": "ab"}') == "ab"
    assert ds.parse_sse_chunk("data: [DONE]") is None


def test_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ds, "_api_key", lambda: "")
    monkeypatch.setattr(ds, "_base_url", lambda: "https://example.com")
    with pytest.raises(ds.DeepSeekAuthError, match="DEEPSEEK_API_KEY"):
        ds._require_config()


def test_missing_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ds, "_api_key", lambda: "sk-x")
    monkeypatch.setattr(ds, "_base_url", lambda: "")
    with pytest.raises(ds.DeepSeekStreamError, match="DEEPSEEK_BASE_URL"):
        ds._require_config()


def test_auth_error_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-bad")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.com/v1")
    fake = AsyncMock()

    async def boom(**_kw: object) -> _FakeAsyncStream:
        req = httpx.Request("POST", "https://example.com/v1/chat/completions")
        resp = httpx.Response(401, request=req)
        raise AuthenticationError("Invalid API key", response=resp, body=None)

    fake.chat.completions.create = boom

    async def _call() -> None:
        await ds.collect_markdown([{"role": "user", "content": "x"}], client=fake)

    with pytest.raises(ds.DeepSeekAuthError, match="DEEPSEEK_API_KEY|密钥"):
        asyncio.run(_call())
