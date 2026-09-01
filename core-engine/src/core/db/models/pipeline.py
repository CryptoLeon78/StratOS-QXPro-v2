"""PARTE 5.2: PipelineCandidate, ChallengerEvaluation, CemeteryEntry."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import sa_enums
from core.db.base import Base
from core.db.column_types import DrawdownPct
from core.db.enums import ActorType, CemeteryCause, PipelinePhase, Verdict


class PipelineCandidate(Base):
    """`decision_eta_days` alimenta "Decision habilitada en ~N dias" / "Faltan
    N trades y N dias" (proyeccion desde frecuencia observada, PARTE 8:
    decision_eta_days())."""

    __tablename__ = "pipeline_candidate"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id"), unique=True)
    current_phase: Mapped[PipelinePhase] = mapped_column(sa_enums.pipeline_phase)
    entered_phase_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    incubation_days: Mapped[int] = mapped_column(Integer)
    oos_trades: Mapped[int] = mapped_column(Integer)
    profit_factor: Mapped[float | None] = mapped_column(nullable=True)
    expectancy_r: Mapped[float | None] = mapped_column(nullable=True)
    sharpe: Mapped[float | None] = mapped_column(nullable=True)
    max_dd_pct: Mapped[Decimal | None] = mapped_column(DrawdownPct, nullable=True)
    wfe: Mapped[float | None] = mapped_column(nullable=True)  # walk_forward_efficiency() -> float
    # trades_per_week() -> float (PARTE 8)
    trades_per_week: Mapped[float | None] = mapped_column(nullable=True)
    gates_passed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    gates_total: Mapped[int] = mapped_column(Integer, default=7, server_default="7")
    provisional: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    verdict: Mapped[Verdict | None] = mapped_column(sa_enums.verdict, nullable=True)
    verdict_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_eta_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PipelinePhaseTransition(Base):
    """Rastro append-only de fases creado desde G11; no inventa pasado."""

    __tablename__ = "pipeline_phase_transition"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("pipeline_candidate.id"))
    from_phase: Mapped[PipelinePhase | None] = mapped_column(sa_enums.pipeline_phase, nullable=True)
    to_phase: Mapped[PipelinePhase] = mapped_column(sa_enums.pipeline_phase)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[ActorType] = mapped_column(sa_enums.actor_type)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChallengerEvaluation(Base):
    """Rotacion darwiniana: challenger evaluado contra el champion del mismo
    slot (PARTE 6.3, 5 criterios en `criteria`)."""

    __tablename__ = "challenger_evaluation"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    challenger_bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id"))
    champion_bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id"))
    slot: Mapped[str] = mapped_column(String)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB)
    passed: Mapped[bool] = mapped_column(Boolean)
    p_value: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str] = mapped_column(Text)


class CemeteryEntry(Base):
    """ "Un bot retirado nunca se reactiva sin re-validacion completa (pipeline
    desde Fase 3)" (banner de la pestana Graveyard). Reincorporacion exige
    repetir desde F3 con identidad NUEVA (nuevo Bot.id), nunca resucitar el
    registro (PARTE 5.2/6.3)."""

    __tablename__ = "cemetery_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id"), unique=True)
    retired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cause: Mapped[CemeteryCause] = mapped_column(sa_enums.cemetery_cause)
    autopsy_text: Mapped[str] = mapped_column(Text)
    lesson: Mapped[str] = mapped_column(Text)
    revalidation_from_phase: Mapped[PipelinePhase] = mapped_column(
        sa_enums.pipeline_phase,
        default=PipelinePhase.F3,
        server_default=PipelinePhase.F3.value,
    )
    reactivation_blocked: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
