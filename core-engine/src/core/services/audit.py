"""PARTE 7.11: reconciliacion contable, continuidad de envio y resumen de
sellos de integridad. Envuelve `audit_discrepancy()` (formulas/audit.py, G2)
con `EquitySnapshot`/`Trade`/`HeartbeatLog`/`IngestBatch` reales.

Hueco real de esquema (documentar, no corregir aqui): PARTE 5.2 no tiene
tabla de depositos/aportes de capital -- el panel 7.11 describe "flujo
posterior (P&L + swaps + comisiones + depositos)" pero solo P&L/swap/
comision son reconstruibles desde `Trade`. `flows` aqui es solo el P&L
comercial cerrado; un deposito/retiro de capital fuera de `WithdrawalLog`
(portfolio-wide, no por cuenta) apareceria como descuadre falso-positivo."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AlertLevel
from core.db.models.accounts import Account
from core.db.models.decisions import Alert
from core.db.models.market import EquitySnapshot, HeartbeatLog, IngestBatch, Trade
from core.formulas.audit import audit_discrepancy


@dataclass(frozen=True)
class AuditConfig:
    discrepancy_tolerance: Decimal = Decimal("0.0001")
    continuity_window_days: int = 7
    # 5x el intervalo contractual de heartbeat (60s, PARTE 10.3) antes de
    # considerar "tramo sin envio" (ASSUMPTIONS G5, no fijado en PARTE 7.11).
    heartbeat_gap_threshold_s: int = 300


@dataclass(frozen=True)
class ReconciliationResult:
    account_id: int
    initial_balance: Decimal
    flows: Decimal
    final_balance: Decimal
    expected: Decimal
    discrepancy_pct: Decimal | None
    breached: bool


@dataclass(frozen=True)
class ContinuityGap:
    start: datetime
    end: datetime
    duration_minutes: float


@dataclass(frozen=True)
class ContinuityResult:
    account_id: int
    coverage_pct: float
    gaps: list[ContinuityGap]


@dataclass(frozen=True)
class SealsSummary:
    total_batches: int
    total_trades: int
    ticket_min: int | None
    ticket_max: int | None
    history_start: datetime | None
    history_end: datetime | None


async def compute_reconciliation(
    session: AsyncSession, account_id: int, config: AuditConfig
) -> ReconciliationResult | None:
    first_snapshot = (
        await session.execute(
            select(EquitySnapshot.balance)
            .where(EquitySnapshot.account_id == account_id)
            .order_by(EquitySnapshot.ts.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    last_snapshot = (
        await session.execute(
            select(EquitySnapshot.balance)
            .where(EquitySnapshot.account_id == account_id)
            .order_by(EquitySnapshot.ts.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if first_snapshot is None or last_snapshot is None or first_snapshot == last_snapshot:
        return None

    flows = (
        await session.execute(
            select(func.coalesce(func.sum(Trade.profit + Trade.commission + Trade.swap), 0)).where(
                Trade.account_id == account_id, Trade.close_time.is_not(None)
            )
        )
    ).scalar_one()
    flows = Decimal(flows)
    expected = first_snapshot + flows

    try:
        discrepancy = audit_discrepancy(first_snapshot, flows, last_snapshot) * 100
        breached = discrepancy > config.discrepancy_tolerance * 100
    except ZeroDivisionError:
        discrepancy = None
        breached = True

    return ReconciliationResult(
        account_id=account_id,
        initial_balance=first_snapshot,
        flows=flows,
        final_balance=last_snapshot,
        expected=expected,
        discrepancy_pct=discrepancy,
        breached=breached,
    )


async def compute_send_continuity(
    session: AsyncSession, account_id: int, config: AuditConfig, days: int, now: datetime
) -> ContinuityResult:
    window_start = now - timedelta(days=days)
    timestamps = (
        (
            await session.execute(
                select(HeartbeatLog.ts)
                .where(HeartbeatLog.account_id == account_id, HeartbeatLog.ts >= window_start)
                .order_by(HeartbeatLog.ts.asc())
            )
        )
        .scalars()
        .all()
    )

    total_hours = days * 24.0
    if not timestamps:
        return ContinuityResult(account_id=account_id, coverage_pct=0.0, gaps=[])

    hours_covered = {(ts.date(), ts.hour) for ts in timestamps}
    coverage_pct = min(100.0, len(hours_covered) / total_hours * 100.0)

    gaps: list[ContinuityGap] = []
    for previous, current in zip(timestamps, timestamps[1:], strict=False):
        delta_s = (current - previous).total_seconds()
        if delta_s > config.heartbeat_gap_threshold_s:
            gaps.append(ContinuityGap(start=previous, end=current, duration_minutes=delta_s / 60.0))

    return ContinuityResult(account_id=account_id, coverage_pct=coverage_pct, gaps=gaps)


async def compute_seals_summary(session: AsyncSession) -> SealsSummary:
    total_batches = (await session.execute(select(func.count(IngestBatch.id)))).scalar_one()
    total_trades = (await session.execute(select(func.count(Trade.id)))).scalar_one()
    ticket_min = (await session.execute(select(func.min(Trade.ticket_mt5)))).scalar_one()
    ticket_max = (await session.execute(select(func.max(Trade.ticket_mt5)))).scalar_one()
    history_start = (await session.execute(select(func.min(Trade.open_time)))).scalar_one()
    history_end = (
        await session.execute(select(func.max(func.coalesce(Trade.close_time, Trade.open_time))))
    ).scalar_one()
    return SealsSummary(
        total_batches=total_batches,
        total_trades=total_trades,
        ticket_min=ticket_min,
        ticket_max=ticket_max,
        history_start=history_start,
        history_end=history_end,
    )


async def run_audit_daily(
    session: AsyncSession, redis: Redis, config: AuditConfig, now: datetime
) -> None:
    account_ids = (
        (await session.execute(select(Account.id).where(Account.is_active.is_(True))))
        .scalars()
        .all()
    )
    for account_id in account_ids:
        result = await compute_reconciliation(session, account_id, config)
        if result is None:
            continue

        dedup_key = f"audit:{account_id}"
        existing = (
            await session.execute(
                select(Alert).where(Alert.dedup_key == dedup_key, Alert.resolved.is_(False))
            )
        ).scalar_one_or_none()

        if result.breached:
            if existing is None:
                discrepancy_label = (
                    f"{result.discrepancy_pct}%"
                    if result.discrepancy_pct is not None
                    else "estructural"
                )
                alert = Alert(
                    ts=now,
                    level=AlertLevel.CRITICA,
                    module="audit",
                    message=f"Cuenta {account_id}: descuadre contable ({discrepancy_label}).",
                    action_required="Revisar reconciliacion en la pestana Auditoria.",
                    dedup_key=dedup_key,
                )
                session.add(alert)
                await session.flush()
                await redis.publish(
                    "events:alert",
                    json.dumps(
                        {
                            "type": "alert.created",
                            "ts": now.isoformat(),
                            "alert_id": alert.id,
                            "level": alert.level.value,
                            "module": alert.module,
                            "message": alert.message,
                            "dedup_key": alert.dedup_key,
                        }
                    ),
                )
        elif existing is not None:
            existing.resolved = True
            existing.resolved_at = now
            existing.resolved_by = "system:audit"
            await session.flush()
