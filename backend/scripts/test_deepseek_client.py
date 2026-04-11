import asyncio

from src.deepseek_client import DeepSeekClient, build_markdown_format_instruction


async def main() -> None:
    client = DeepSeekClient()
    messages = [
        {"role": "system", "content": build_markdown_format_instruction()},
        {"role": "user", "content": "请给我一个示例建议，包含买入和卖出区间。"},
    ]

    print("=== STREAM START ===")
    async for chunk in client.chat_stream(messages, temperature=0.3):
        print(chunk, end="", flush=True)
    print("\n=== STREAM END ===")

    print("\n=== COMPLETE START ===")
    full = client.chat_complete(messages, temperature=0.3)
    print(full)
    print("=== COMPLETE END ===")


if __name__ == "__main__":
    asyncio.run(main())
