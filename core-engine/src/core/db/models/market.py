"""PARTE 5.2: Trade, EquitySnapshot, HeartbeatLog (hypertables por su columna
de tiempo — la conversion real a hypertable + compresion/retencion vive en la
migracion Alembic 0001, no aqui), IngestBatch, FxRate.

Nota TimescaleDB: la PK/UNIQUE de una hypertable debe incluir la columna de
particion. Trade usa PK compuesta (id, open_time) en vez de id solo (el
BIGSERIAL ya garantiza unicidad global; la columna extra es para satisfacer
esa exigencia de Timescale) + UNIQUE(ticket_mt5, open_time) tal cual PARTE 5.2.

Todas las columnas Numeric se tipan `Mapped[Decimal]`: el tipo SQLAlchemy
`Numeric` devuelve `decimal.Decimal` en Python (PARTE 8: Decimal para dinero).
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import sa_enums
from core.db.base import Base
from core.db.column_types import DrawdownPct, FxRateValue, Money, Price, RMultiple, Volume
from core.db.enums import TradeType


class Trade(Base):
    """`bot_id` NULL = huerfano (lo reporta el watchdog, la ingesta no se
    rechaza). Compresion a 90 dias, sin borrado (PARTE 5.2)."""

    __tablename__ = "trade"
    __table_args__ = (
        PrimaryKeyConstraint("id", "open_time"),
        UniqueConstraint("ticket_mt5", "open_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, autoincrement=True)
    bot_id: Mapped[int | None] = mapped_column(ForeignKey("bot.id"), nullable=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    magic_number: Mapped[int] = mapped_column(Integer)
    ticket_mt5: Mapped[int] = mapped_column(BigInteger)
    symbol: Mapped[str] = mapped_column(String)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    type: Mapped[TradeType] = mapped_column(sa_enums.trade_type)
    volume: Mapped[Decimal] = mapped_column(Volume)
    open_price: Mapped[Decimal] = mapped_column(Price)
    close_price: Mapped[Decimal | None] = mapped_column(Price, nullable=True)
    sl: Mapped[Decimal | None] = mapped_column(Price, nullable=True)
    tp: Mapped[Decimal | None] = mapped_column(Price, nullable=True)
    profit: Mapped[Decimal] = mapped_column(Money)
    commission: Mapped[Decimal] = mapped_column(Money)
    swap: Mapped[Decimal] = mapped_column(Money)
    r_multiple: Mapped[Decimal | None] = mapped_column(RMultiple, nullable=True)
    ingest_batch_id: Mapped[int] = mapped_column(ForeignKey("ingest_batch.id"))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshot"
    __table_args__ = (PrimaryKeyConstraint("ts", "account_id"),)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    equity: Mapped[Decimal] = mapped_column(Money)
    balance: Mapped[Decimal] = mapped_column(Money)
    drawdown_pct: Mapped[Decimal] = mapped_column(DrawdownPct)
    margin_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_margin: Mapped[Decimal | None] = mapped_column(Money, nullable=True)


class HeartbeatLog(Base):
    """Retencion 30 dias (PARTE 5.2)."""

    __tablename__ = "heartbeat_log"
    __table_args__ = (PrimaryKeyConstraint("ts", "connector_instance_id", "account_id"),)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    connector_instance_id: Mapped[str] = mapped_column(String)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    latency_ms: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)


class IngestBatch(Base):
    """Sello por lote (pestana Auditoria: "lotes sellados (hash+ts)"). El hash
    cubre el payload canonico del lote (lo calcula el conector/ingest, G4/G5)."""

    __tablename__ = "ingest_batch"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    connector_instance_id: Mapped[str] = mapped_column(String)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    batch_type: Mapped[str] = mapped_column(String)
    records: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    server_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FxRate(Base):
    __tablename__ = "fx_rate"
    __table_args__ = (PrimaryKeyConstraint("ts", "base", "quote"),)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    base: Mapped[str] = mapped_column(String(3))
    quote: Mapped[str] = mapped_column(String(3))
    rate: Mapped[Decimal] = mapped_column(FxRateValue)


class VirtualTrade(Base):
    """G4/ASSUMPTIONS: `POST /ingest/signals` (PARTE 9.1) no tiene tabla en
    PARTE 5.2 -- son trades virtuales (semaforo NARANJA, PARTE 6.1), no
    trades reales, por eso viven aparte de `Trade` (mezclarlos corrompería
    cualquier formula que escanee P&L real). Mutable: no es una de las 6
    tablas inmutables de P6/P15.3."""

    __tablename__ = "virtual_trade"
    __table_args__ = (UniqueConstraint("account_id", "magic_number", "signal_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    bot_id: Mapped[int | None] = mapped_column(ForeignKey("bot.id"), nullable=True)
    magic_number: Mapped[int] = mapped_column(Integer)
    signal_id: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String)
    type: Mapped[TradeType] = mapped_column(sa_enums.trade_type)
    volume: Mapped[Decimal] = mapped_column(Volume)
    entry_price: Mapped[Decimal] = mapped_column(Price)
    sl: Mapped[Decimal | None] = mapped_column(Price, nullable=True)
    tp: Mapped[Decimal | None] = mapped_column(Price, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingest_batch_id: Mapped[int] = mapped_column(ForeignKey("ingest_batch.id"))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EaState(Base):
    """G4/ASSUMPTIONS: `POST /ingest/ea_state` (PARTE 9.1) alimenta la
    pestaña Cuentas/EA (7.2, diseño derivado) -- espejo del ULTIMO estado
    reportado por EA, no una serie temporal (por eso PK compuesta simple,
    UPSERT en cada ingesta, no INSERT append-only)."""

    __tablename__ = "ea_state"
    __table_args__ = (PrimaryKeyConstraint("account_id", "magic_number"),)

    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    magic_number: Mapped[int] = mapped_column(Integer)
    ea_version: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)
    autotrading: Mapped[bool] = mapped_column(Boolean)
    schedule_filter: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    news_windows: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    ingest_batch_id: Mapped[int] = mapped_column(ForeignKey("ingest_batch.id"))
    last_ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
