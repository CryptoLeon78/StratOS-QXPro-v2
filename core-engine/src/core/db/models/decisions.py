"""PARTE 5.2: Alert, Decision, ImpulseLog (mutables) + DecisionLog,
SemaphoreTransition, KillSwitchEvent (3 de las 6 tablas inmutables de P6/
P15.3 — el rol `stratos_app` solo tendra SELECT/INSERT en ellas, migracion
0001)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import sa_enums
from core.db.base import Base
from core.db.column_types import DrawdownPct, Money
from core.db.enums import (
    ActorType,
    AlertLevel,
    DecisionStatus,
    ImpulseAction,
    ImpulseStatus,
    SemaphoreState,
)


class Alert(Base):
    __tablename__ = "alert"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    level: Mapped[AlertLevel] = mapped_column(sa_enums.alert_level)
    module: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    action_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedup_key: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    # ADR 0013: NULL = evento heredado de portfolio (anterior al alcance por cuenta).
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("account.id"), nullable=True, index=True
    )


class Decision(Base):
    """Alimenta "Requiere accion (N)" del Resumen y el badge de cabecera. Los
    tres botones de la captura (Confirmar/Posponer/Descartar) escriben aqui
    y en DecisionLog (PARTE 7.1)."""

    __tablename__ = "decision"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    module: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    instruction_text: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[DecisionStatus] = mapped_column(
        sa_enums.decision_status,
        default=DecisionStatus.PENDING,
        server_default=DecisionStatus.PENDING.value,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String, nullable=True)
    postpone_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # ADR 0013: NULL = evento heredado de portfolio (anterior al alcance por cuenta).
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("account.id"), nullable=True, index=True
    )


class ImpulseLog(Base):
    __tablename__ = "impulse_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id"))
    description: Mapped[str] = mapped_column(Text)
    desired_action: Mapped[ImpulseAction] = mapped_column(sa_enums.impulse_action)
    executed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    status: Mapped[ImpulseStatus] = mapped_column(
        sa_enums.impulse_status,
        default=ImpulseStatus.PENDING,
        server_default=ImpulseStatus.PENDING.value,
    )
    # counterfactual_impulse() -> Decimal (PARTE 8): avoided_cost = real - simulado
    counterfactual_result_7d_eur: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    avoided_cost_eur: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DecisionLog(Base):
    """APPEND-ONLY con hash-chain (P6). Prohibido UPDATE/DELETE (permisos de
    rol, migracion 0001)."""

    __tablename__ = "decision_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[ActorType] = mapped_column(sa_enums.actor_type)
    module: Mapped[str] = mapped_column(String)
    decision_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class SemaphoreTransition(Base):
    """Inmutable (P6/P15.3): historial de transiciones de semaforo, nunca se
    edita ni se borra una fila existente."""

    __tablename__ = "semaphore_transition"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    from_state: Mapped[SemaphoreState] = mapped_column(sa_enums.semaphore_state)
    to_state: Mapped[SemaphoreState] = mapped_column(sa_enums.semaphore_state)
    trigger_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    instruction_text: Mapped[str] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String, nullable=True)


class KillSwitchEvent(Base):
    """Inmutable (P6/P15.3)."""

    __tablename__ = "killswitch_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    level: Mapped[int] = mapped_column(Integer)
    portfolio_dd_pct: Mapped[Decimal] = mapped_column(DrawdownPct)
    actions: Mapped[dict[str, Any]] = mapped_column(JSONB)
    instruction_text: Mapped[str] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    # ADR 0013: NULL = evento heredado de portfolio (anterior al alcance por cuenta).
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("account.id"), nullable=True, index=True
    )
