from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI, OpenAI

from src.config import get_settings

MARKDOWN_RESPONSE_TEMPLATE = """## 操作建议
（文字描述）

### 买入建议
- 股票代码 股票名称：建议买入区间 XX-YY 元
...

### 卖出建议
- 股票代码 股票名称：建议卖出区间 XX-YY 元
...

## 风险提示
（文字描述）
"""


class DeepSeekClientError(RuntimeError):
    """DeepSeek client raised a non-recoverable error."""


class DeepSeekClient:
    def __init__(self, max_retries: int = 3) -> None:
        settings = get_settings()
        self.base_url = settings.deepseek_base_url
        self.api_key = settings.deepseek_api_key
        self.model = settings.deepseek_model
        self.max_retries = max_retries

        if not self.api_key:
            raise DeepSeekClientError("DEEPSEEK_API_KEY is empty. Please set it in .env.")

        self._sync_client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self._async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion tokens as an async generator.
        Designed for FastAPI StreamingResponse / SSE usage.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                stream = await self._async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    **kwargs,
                )
                async for chunk in stream:
                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    delta = getattr(choices[0], "delta", None)
                    content = getattr(delta, "content", None)
                    if content:
                        yield content
                return
            except Exception as exc:  # noqa: BLE001
                if attempt >= self.max_retries:
                    raise DeepSeekClientError(
                        f"DeepSeek stream request failed after {self.max_retries} retries: {exc}"
                    ) from exc
                await asyncio.sleep(0.8 * attempt)

    def chat_complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """
        Non-streaming completion for simple synchronous scenarios.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._sync_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=False,
                    **kwargs,
                )
                choices = getattr(response, "choices", None) or []
                if not choices or getattr(choices[0], "message", None) is None:
                    return ""
                content = choices[0].message.content
                return content or ""
            except Exception as exc:  # noqa: BLE001
                if attempt >= self.max_retries:
                    raise DeepSeekClientError(
                        f"DeepSeek completion request failed after {self.max_retries} retries: {exc}"
                    ) from exc
                time.sleep(0.5 * attempt)


def build_markdown_format_instruction() -> str:
    return (
        "请严格按以下 Markdown 结构输出投资建议，不要添加无关标题或免责声明：\n\n"
        f"{MARKDOWN_RESPONSE_TEMPLATE}"
    )
