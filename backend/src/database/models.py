from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(64), nullable=False)
    listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_delisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delisted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True)


class FactorData(Base, TimestampMixin):
    __tablename__ = "factor_data"
    __table_args__ = (UniqueConstraint("trade_date", "stock_code", name="uq_factor_date_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    factor_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    future_1w_return: Mapped[float | None] = mapped_column(Float, nullable=True)


class BacktestResult(Base, TimestampMixin):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    backtest_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    nav_series: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    holdings_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ShadowAccount(Base, TimestampMixin):
    """影子账户：前端随机 ID 或自定义名称存入 account_name，用于区分最多 10 个并发会话。"""

    __tablename__ = "shadow_account"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    holdings: Mapped[list | dict] = mapped_column(JSON, nullable=False, default=list)
    backtest_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    backtest_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    prediction_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    prediction_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    ai_advices: Mapped[list["AIAdvice"]] = relationship(
        back_populates="shadow_account",
        cascade="all, delete-orphan",
    )


class AIAdvice(Base):
    __tablename__ = "ai_advice"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shadow_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    advice_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    top_stocks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    context_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    shadow_account: Mapped["ShadowAccount"] = relationship(back_populates="ai_advices")
