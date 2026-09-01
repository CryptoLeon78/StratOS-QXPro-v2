"""Inventario operativo append-only: admision sin inventar una fase de pipeline."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
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
