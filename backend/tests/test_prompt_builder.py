"""prompt_builder：系统/用户提示与消息列表。"""
from __future__ import annotations

from src.prompt_builder import (
    build_system_prompt,
    build_user_prompt,
    compose_user_prompt_text,
)


def test_build_system_prompt_markdown_constraints() -> None:
    s = build_system_prompt()
    assert "## 操作建议" in s
    assert "### 买入建议" in s
    assert "### 卖出建议" in s
    assert "## 风险提示" in s
    assert "Markdown" in s


def test_build_user_prompt_message_shape() -> None:
    top = [{"stock_code": "000001.SZ", "name": "A", "score": 0.9}]
    hold = [{"code": "600000.SH", "quantity": 10, "cost": 8.0, "current_price": 8.5}]
    pr = {
        "000001.SZ": {"buy_low": 8.0, "buy_high": 8.2, "sell_low": 8.6, "sell_high": 9.0},
        "600000.SH": {"buy_low": 7.0, "buy_high": 7.5, "sell_low": 8.4, "sell_high": 8.8},
    }
    fi = {"f1": 100.0, "f2": 50.0, "f3": 40.0, "f4": 30.0, "f5": 20.0, "f6": 10.0}
    msgs = build_user_prompt(top, hold, pr, fi)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert len(msgs[0]["content"]) > 50
    assert len(msgs[1]["content"]) > 50


def test_user_content_top5_and_holdings_and_not_in_top10() -> None:
    top = [{"code": f"{i:06d}", "score": float(10 - i)} for i in range(10)]
    hold = [{"code": "999999", "quantity": 1, "cost": 1.0, "current_price": 1.1}]
    pr = {f"{i:06d}": {"buy_low": 1.0, "buy_high": 1.1, "sell_low": 1.2, "sell_high": 1.3} for i in range(10)}
    pr["999999"] = {"buy_low": 1.0, "buy_high": 1.05, "sell_low": 1.15, "sell_high": 1.2}
    fi = {f"feat_{i}": float(i + 1) for i in range(10)}
    text = compose_user_prompt_text(top, hold, pr, fi)
    assert "前 5 个因子" in text or "前 5 个因子为" in text
    assert "000000" in text
    assert "999999" in text
    assert "不在上述模型 Top10" in text
    assert "重点展开分析前 5 名" in text


def test_compose_without_optional_sections() -> None:
    text = compose_user_prompt_text([], [], {}, None)
    assert "无 Top 股票列表" in text
    assert "当前无持仓" in text
