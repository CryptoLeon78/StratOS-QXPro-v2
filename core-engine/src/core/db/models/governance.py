"""PARTE 5.2: CorrelationMatrix, MonteCarloRun, UmsPhaseLog, NewsEvent, User,
SystemConfig (mutables) + WithdrawalLog, ChecklistRun (2 de las 6 tablas
inmutables de P6/P15.3)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import sa_enums
from core.db.base import Base
from core.db.column_types import DrawdownPct, Money
from core.db.enums import ChecklistType, NewsImpact


class CorrelationMatrix(Base):
    __tablename__ = "correlation_matrix"
    __table_args__ = (UniqueConstraint("ts", "bot_a_id", "bot_b_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bot_a_id: Mapped[int] = mapped_column(ForeignKey("bot.id"))
    bot_b_id: Mapped[int] = mapped_column(ForeignKey("bot.id"))
    correlation: Mapped[float] = mapped_column()
    is_redundant_pair: Mapped[bool] = mapped_column(Boolean)
    window_days: Mapped[int] = mapped_column(Integer)


class MonteCarloRun(Base):
    """dd_p50/p75/p95/dd_contract_pct: misma familia Decimal que
    Baseline.max_dd_pct (max_drawdown_pct() -> Decimal, PARTE 8)."""

    __tablename__ = "montecarlo_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    n_simulations: Mapped[int] = mapped_column(Integer)
    dd_p50: Mapped[Decimal] = mapped_column(DrawdownPct)
    dd_p75: Mapped[Decimal] = mapped_column(DrawdownPct)
    dd_p95: Mapped[Decimal] = mapped_column(DrawdownPct)
    dd_contract_pct: Mapped[Decimal] = mapped_column(DrawdownPct)
    seed: Mapped[int] = mapped_column(BigInteger)


class UmsPhaseLog(Base):
    __tablename__ = "ums_phase_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    phase: Mapped[int] = mapped_column(Integer)
    equity_at: Mapped[Decimal] = mapped_column(Money)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ready_to_advance: Mapped[bool] = mapped_column(Boolean)


class WithdrawalLog(Base):
    """Inmutable (P6/P15.3): retiro mensual-nomina sin excepcion (PARTE 14),
    sustainable_withdrawal() -> Decimal (PARTE 8)."""

    __tablename__ = "withdrawal_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    amount: Mapped[Decimal] = mapped_column(Money)
    equity_before: Mapped[Decimal] = mapped_column(Money)
    checklist_completed: Mapped[dict[str, Any]] = mapped_column(JSONB)


class NewsEvent(Base):
    __tablename__ = "news_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    currency: Mapped[str] = mapped_column(String(3))
    impact: Mapped[NewsImpact] = mapped_column(sa_enums.news_impact)
    title: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    blackout_before_min: Mapped[int] = mapped_column(Integer, default=30, server_default="30")
    blackout_after_min: Mapped[int] = mapped_column(Integer, default=30, server_default="30")


class ChecklistRun(Base):
    """Inmutable (P6/P15.3)."""

    __tablename__ = "checklist_run"
    __table_args__ = (UniqueConstraint("checklist_type", "period_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checklist_type: Mapped[ChecklistType] = mapped_column(sa_enums.checklist_type)
    period_key: Mapped[str] = mapped_column(String)
    items: Mapped[dict[str, Any]] = mapped_column(JSONB)
    completed: Mapped[bool] = mapped_column(Boolean)
    signed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_hash: Mapped[str | None] = mapped_column(String, nullable=True)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="operator", server_default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SystemConfig(Base):
    """Unica fuente de umbrales contractuales (P11, PARTE 10.3). Sembrada por
    `config/thresholds.seed.json` via `scripts/seed.py` (PARTE 13, G8)."""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
