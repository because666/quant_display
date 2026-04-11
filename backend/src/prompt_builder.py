"""
DeepSeek 对话提示词构造：系统角色 + 用户侧多源信息（预测 Top、持仓、ATR 区间、特征重要性）。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Sequence, TypedDict

logger = logging.getLogger(__name__)

ChatMessage = TypedDict("ChatMessage", {"role": str, "content": str})


def build_system_prompt() -> str:
    """
    系统角色与输出格式约束（Markdown），便于下游解析 ``##`` / ``###`` 结构。
    """
    return "\n".join(
        [
            "你是一位专业的量化投资顾问。请仅根据用户提供的模型预测得分、持仓与参考价格区间等信息进行分析，"
            "不得编造不存在的行情或新闻。若信息不足，请明确说明并建议观望。",
            "",
            "请严格按照以下 Markdown 结构输出（标题层级与顺序保持一致）：",
            "",
            "## 操作建议",
            "",
            "### 买入建议",
            "（可写：建议关注标的、分批思路、与模型得分一致性说明；若无买入机会则说明原因。）",
            "",
            "### 卖出建议",
            "（可写：减仓/止盈/止损思路；对「不在模型 Top10 推荐内」的持仓请单独点评是否考虑卖出或继续持有。）",
            "",
            "### 调仓与持仓调整",
            "（可写：加减仓比例、换仓逻辑、观望条件等。）",
            "",
            "## 风险提示",
            "（模型局限、过拟合、流动性、政策与黑天鹅等。）",
            "",
            "全文使用规范 Markdown；数值保留合理小数位；勿使用 HTML。",
        ]
    )


def _stock_code(row: Mapping[str, Any]) -> str:
    for k in ("stock_code", "code", "symbol"):
        if k in row and row[k] is not None:
            return str(row[k]).strip()
    raise KeyError("股票代码字段缺失，需要 stock_code / code / symbol 之一")


def _normalize_top_stocks(top_stocks: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if not top_stocks:
        return []
    out: list[dict[str, Any]] = []
    for i, row in enumerate(top_stocks):
        try:
            code = _stock_code(row)
        except KeyError:
            logger.warning("跳过 Top 列表第 %s 条：无代码字段", i)
            continue
        name = row.get("name") or row.get("stock_name") or ""
        score = row.get("score")
        try:
            sc = float(score) if score is not None else float("nan")
        except (TypeError, ValueError):
            sc = float("nan")
        out.append({"code": code, "name": str(name), "score": sc})
    return out


def _normalize_holdings(holdings: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if not holdings:
        return []
    out: list[dict[str, Any]] = []
    for i, row in enumerate(holdings):
        try:
            code = _stock_code(row)
        except KeyError:
            logger.warning("跳过持仓第 %s 条：无代码字段", i)
            continue
        name = row.get("name") or row.get("stock_name") or ""
        qty = row.get("quantity", row.get("qty"))
        cost = row.get("cost", row.get("cost_price"))
        cur = row.get("current_price", row.get("price", row.get("close")))
        try:
            qv = float(qty) if qty is not None else float("nan")
            cv = float(cost) if cost is not None else float("nan")
            pv = float(cur) if cur is not None else float("nan")
        except (TypeError, ValueError):
            qv, cv, pv = float("nan"), float("nan"), float("nan")
        out.append(
            {
                "code": code,
                "name": str(name),
                "quantity": qv,
                "cost": cv,
                "current_price": pv,
            }
        )
    return out


def _top_n_importance(feature_importance: Mapping[str, float] | None, n: int = 5) -> list[tuple[str, float]]:
    if not feature_importance:
        return []
    items = sorted(feature_importance.items(), key=lambda x: float(x[1]), reverse=True)
    return [(str(k), float(v)) for k, v in items[:n]]


def _format_price_block(code: str, pr: Mapping[str, Any] | None) -> str:
    if not pr:
        return f"- {code}：暂无区间数据"
    def _f(k: str) -> str:
        v = pr.get(k)
        if v is None:
            return "—"
        try:
            return f"{float(v):.4f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            return str(v)

    return (
        f"- {code}：买入参考 [{_f('buy_low')}, {_f('buy_high')}]；"
        f"卖出参考 [{_f('sell_low')}, {_f('sell_high')}]（单位：元；"
        f"ATR={_f('atr')}，支撑={_f('support')}，阻力={_f('resistance')}）"
    )


def compose_user_prompt_text(
    top_stocks: Sequence[Mapping[str, Any]] | None,
    holdings: Sequence[Mapping[str, Any]] | None,
    price_ranges: Mapping[str, Mapping[str, Any]] | None,
    feature_importance: Mapping[str, float] | None,
) -> str:
    """
    仅生成 user 角色的正文（不含 system）。需要完整 messages 时请用 ``build_user_prompt``。
    """
    tops = _normalize_top_stocks(top_stocks)
    holds = _normalize_holdings(holdings)
    pr_map: dict[str, Mapping[str, Any]] = dict(price_ranges or {})
    top5_factors = _top_n_importance(feature_importance, 5)

    top_codes = {t["code"] for t in tops}
    hold_codes = {h["code"] for h in holds}
    codes_for_ranges = sorted(top_codes | hold_codes)

    lines: list[str] = []

    lines.append("请基于下列结构化信息，给出可执行的调仓与风控建议（输出格式须遵守系统提示中的 Markdown 模板）。")
    lines.append("")

    lines.append("## 当前市场特征（模型视角）")
    if top5_factors:
        parts = [f"{name}（重要性 {val:.6g}）" for name, val in top5_factors]
        lines.append("当前截面下，模型最依赖的前 5 个因子为：" + "；".join(parts) + "。")
        lines.append("说明：因子重要性为训练模型时的 gain 类指标，仅反映历史统计规律，不代表未来收益。")
    else:
        lines.append("未提供特征重要性；请主要依据得分排序与价格区间推理。")
    lines.append("")

    lines.append("## 模型推荐买入关注列表（按得分排序，含前 10）")
    if tops:
        for i, t in enumerate(tops[:10], start=1):
            nm = f" {t['name']}" if t.get("name") else ""
            sc = t["score"]
            sc_s = f"{sc:.6f}" if sc == sc else "N/A"
            lines.append(f"{i}. {t['code']}{nm}，模型得分 {sc_s}")
        lines.append("")
        lines.append("**请重点展开分析前 5 名标的**（上表第 1–5 行），并简要点评第 6–10 名是否与持仓重复或存在冲突。")
    else:
        lines.append("（无 Top 股票列表）")
    lines.append("")

    lines.append("## 您当前的持仓")
    if holds:
        for h in holds:
            nm = f" {h['name']}" if h.get("name") else ""
            lines.append(
                f"- {h['code']}{nm}：数量 {h['quantity'] if h['quantity'] == h['quantity'] else 'N/A'}，"
                f"成本价 {h['cost'] if h['cost'] == h['cost'] else 'N/A'}，"
                f"当前价 {h['current_price'] if h['current_price'] == h['current_price'] else 'N/A'}"
            )
        not_in_top = sorted(hold_codes - top_codes)
        if not_in_top:
            lines.append("")
            lines.append(
                "**下列持仓代码不在上述模型 Top10 推荐内**："
                + "、".join(not_in_top)
                + "。请结合其价格区间与盈亏情况，**单独评估是否减仓、止盈或止损**，避免仅因惯性持有。"
            )
    else:
        lines.append("（当前无持仓）")
    lines.append("")

    lines.append("## 每只相关股票的参考买卖区间（已预计算）")
    lines.append("区间含义：买入参考带大致位于现价下方（ATR 倍数），卖出参考带大致位于现价上方；并已用近期支撑/阻力做边界微调。")
    if codes_for_ranges:
        for c in codes_for_ranges:
            lines.append(_format_price_block(c, pr_map.get(c)))
    else:
        lines.append("（无标的代码可展示区间）")
    lines.append("")

    lines.append("## 请您输出的分析要求")
    lines.append("- 结合 **Top5 推荐** 与 **现有持仓**，说明是否调仓、加仓、减仓或观望。")
    lines.append("- 对持仓中与推荐重叠的标的，说明是否加仓/持有；对未进 Top10 的持仓，必须给出是否卖出的明确倾向（可附条件）。")
    lines.append("- 引用价格区间时请注明「仅供参考」，不构成投资建议。")

    return "\n".join(lines)


def build_user_prompt(
    top_stocks: Sequence[Mapping[str, Any]] | None,
    holdings: Sequence[Mapping[str, Any]] | None,
    price_ranges: Mapping[str, Mapping[str, Any]] | None,
    feature_importance: Mapping[str, float] | None,
) -> list[ChatMessage]:
    """
    返回 DeepSeek / OpenAI Chat 兼容消息列表：
    ``[{"role":"system","content":...},{"role":"user","content":...}]``。
    """
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": compose_user_prompt_text(top_stocks, holdings, price_ranges, feature_importance)},
    ]


def _main() -> None:
    demo_top = [
        {"stock_code": "000001.SZ", "name": "平安银行", "score": 0.9123},
        {"code": "600000.SH", "name": "浦发银行", "score": 0.88},
    ]
    demo_hold = [{"code": "000001.SZ", "name": "平安银行", "quantity": 100, "cost": 10.5, "current_price": 11.0}]
    demo_pr = {
        "000001.SZ": {
            "buy_low": 10.7,
            "buy_high": 10.9,
            "sell_low": 11.1,
            "sell_high": 11.4,
            "atr": 0.5,
            "support": 10.5,
            "resistance": 11.5,
        }
    }
    demo_fi = {"momentum_20d": 120.0, "volatility_60d": 80.0, "roe": 50.0, "pe_ttm": 30.0, "turnover": 10.0}
    msgs = build_user_prompt(demo_top, demo_hold, demo_pr, demo_fi)
    print(json.dumps(msgs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
