"""Inventario operativo append-only: admision sin inventar una fase de pipeline."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import sa_enums
from core.db.base import Base
from core.db.enums import AssetAdmissionStatus, AssetSourceGroup


class OperationalAsset(Base):
    __tablename__ = "operational_asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_group: Mapped[AssetSourceGroup] = mapped_column(sa_enums.asset_source_group)
    source_root: Mapped[str] = mapped_column(String)
    sqx_path: Mapped[str | None] = mapped_column(String, nullable=True)
    mql5_path: Mapped[str | None] = mapped_column(String, nullable=True)
    sqx_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mql5_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    strategy_name: Mapped[str | None] = mapped_column(String, nullable=True)
    magic_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OperationalAssetEvent(Base):
    __tablename__ = "operational_asset_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("operational_asset.id"))
    status: Mapped[AssetAdmissionStatus] = mapped_column(sa_enums.asset_admission_status)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DemoChartAttachment(Base):
    """Declaración inmutable de un adjunto demo por gráfico.

    El manifiesto completo queda preservado en ``ImportArtifact``. Esta tabla
    conserva los campos de identidad que se deben confrontar con el siguiente
    ``EaState`` sellado; crearla no abre MT5 ni implica que el EA esté corriendo.
    """

    __tablename__ = "demo_chart_attachment"
    __table_args__ = (UniqueConstraint("candidate_id", "artifact_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("pipeline_candidate.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("operational_asset.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    artifact_id: Mapped[int] = mapped_column(ForeignKey("import_artifact.id"))
    magic_number: Mapped[int] = mapped_column(Integer)
    symbol: Mapped[str] = mapped_column(String)
    timeframe: Mapped[str] = mapped_column(String)
    ea_version: Mapped[str] = mapped_column(String)
    mql5_sha256: Mapped[str] = mapped_column(String(64))
    compiled_ex5_sha256: Mapped[str] = mapped_column(String(64))
    comment_identity: Mapped[str] = mapped_column(String)
    expert_relative_path: Mapped[str] = mapped_column(String)
    reporter_outbox: Mapped[str] = mapped_column(String)
    required_mode: Mapped[str] = mapped_column(String)
    required_autotrading: Mapped[bool] = mapped_column(Boolean)
    required_sizing_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    declared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PipelineWorkItem(Base):
    """Registro persistente del trabajo externo que alimenta F1--F6.

    No ejecuta procesos: el agente Windows consume únicamente comandos
    aprobados creados a partir de estas filas.
    """

    __tablename__ = "pipeline_work_item"
    __table_args__ = (UniqueConstraint("kind", "source_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    source_key: Mapped[str] = mapped_column(String)
    phase: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PipelineAgentCommand(Base):
    """Comando idempotente para el agente Windows demo; append-only."""

    __tablename__ = "pipeline_agent_command"
    __table_args__ = (UniqueConstraint("idempotency_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_work_item.id"), nullable=True
    )
    command_type: Mapped[str] = mapped_column(String)
    idempotency_key: Mapped[str] = mapped_column(String)
    request_sha256: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PipelineAgentCommandEvent(Base):
    """Resultado append-only emitido por el agente para un comando de Pipeline."""

    __tablename__ = "pipeline_agent_command_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    command_id: Mapped[int] = mapped_column(ForeignKey("pipeline_agent_command.id"))
    status: Mapped[str] = mapped_column(String)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExternalEaInventory(Base):
    """Observaciones inmutables de EAs reales; no equivalen a alta F7."""

    __tablename__ = "external_ea_inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    bot_id: Mapped[int | None] = mapped_column(ForeignKey("bot.id"), nullable=True)
    ea_filename: Mapped[str] = mapped_column(String)
    ea_relative_path: Mapped[str] = mapped_column(String)
    ea_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    comment_identity: Mapped[str] = mapped_column(String)
    magic_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
