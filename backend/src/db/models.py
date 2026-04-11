from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BacktestResult(Base):
    """
    单次回测落库：模型类型、参数快照、净值序列（JSON）、指标（JSON）。
    净值序列为调仓日（周频）点列表，与引擎输出一致；指标在写入前按日频前向填充后计算。
    """

    __tablename__ = "backtest_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_type: Mapped[str] = mapped_column(String(32), index=True)
    params_json: Mapped[str] = mapped_column(Text)
    nav_json: Mapped[str] = mapped_column(Text)
    metrics_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
