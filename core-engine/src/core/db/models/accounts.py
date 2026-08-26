"""PARTE 5.2: Account, Bot, Baseline."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db import sa_enums
from core.db.base import Base
from core.db.column_types import DrawdownPct
from core.db.enums import BaselineSource, BotProfile, BotRole, PipelinePhase, SemaphoreState


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    broker: Mapped[str] = mapped_column(String)
    login: Mapped[str] = mapped_column(String)
    server: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String(3))
    is_demo: Mapped[bool] = mapped_column(Boolean)
    connector_instance_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Bot(Base):
    """`slot`: plaza de portfolio que ocupa un champion (p.ej. "trend-eurusd-h4");
    la rotacion darwiniana se evalua challenger vs champion del mismo slot.
    `entered_state_at` alimenta el contador "N dias en estado/fase"."""

    __tablename__ = "bot"
    __table_args__ = (UniqueConstraint("account_id", "magic_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    magic_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)
    market: Mapped[str] = mapped_column(String)
    timeframe: Mapped[str] = mapped_column(String)
    profile: Mapped[BotProfile] = mapped_column(sa_enums.bot_profile)
    role: Mapped[BotRole] = mapped_column(sa_enums.bot_role)
    slot: Mapped[str | None] = mapped_column(String, nullable=True)
    pipeline_phase: Mapped[PipelinePhase] = mapped_column(sa_enums.pipeline_phase)
    semaphore_state: Mapped[SemaphoreState] = mapped_column(
        sa_enums.semaphore_state,
        default=SemaphoreState.VERDE,
        server_default=SemaphoreState.VERDE.value,
    )
    entered_state_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capital_allocated_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    risk_per_trade_pct: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    sizing_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("1.0"), server_default="1.0"
    )
    sizing_current_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("100.0"), server_default="100.0"
    )
    kelly_fraction: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    baseline_id: Mapped[int | None] = mapped_column(
        ForeignKey("baseline.id", use_alter=True, name="fk_bot_baseline_id"),
        nullable=True,
    )


class Baseline(Base):
    """Versionada, append-only (una fila nueva por recalculo, nunca se
    actualiza una existente; `is_active` marca la vigente)."""

    __tablename__ = "baseline"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id"))
    source: Mapped[BaselineSource] = mapped_column(sa_enums.baseline_source)
    profit_factor: Mapped[float] = mapped_column()  # rolling_profit_factor() -> float | None
    expectancy_r: Mapped[float] = mapped_column()  # expectancy_r() -> float
    sharpe: Mapped[float] = mapped_column()
    max_dd_pct: Mapped[Decimal] = mapped_column(DrawdownPct)  # max_drawdown_pct() -> Decimal
    win_rate: Mapped[float] = mapped_column()
    payoff: Mapped[float] = mapped_column()
    avg_trade_duration_min: Mapped[float] = mapped_column()
    max_consec_losses: Mapped[int] = mapped_column(Integer)
    expected_trades_30d: Mapped[int] = mapped_column(Integer)
    dd_contract_pct: Mapped[Decimal] = mapped_column(DrawdownPct)  # misma familia que max_dd_pct
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
