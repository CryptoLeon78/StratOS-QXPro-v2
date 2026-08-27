"""PARTE 13: equity diaria de la cuenta REAL "Prod" (7.9 -- reconciliacion
contable exige EXACTAMENTE que el ultimo `EquitySnapshot.balance` sea
30.000 + suma de `Trade.profit/commission/swap` de la propia cuenta, o el
criterio de aceptacion 6 "Auditoria 0,00% limpio" no puede darse solo con
seed data). Se deriva de los MISMOS `GeneratedTrade` ya generados por
trades_history.py (no una segunda fuente de verdad) -- balance==equity
punto a punto porque todo trade generado ya esta cerrado, no hay P&L
flotante que modelar.

HeartbeatLog (30 dias, retencion real de la tabla per PARTE 5.2 -- fuera
de esa ventana no tendria sentido sembrar filas que un sistema real ya
habria purgado) a cadencia contractual de 60s (mt5-connector,
ASSUMPTIONS G4) para ambas cuentas. Cada heartbeat es su propio
IngestBatch sellado (un POST = un sello, mismo criterio que G4) -- esto
es lo que más acerca el recuento total de lotes sellados al objetivo
literal de PARTE 13 (137.296), aunque sigue sin alcanzarlo del todo (ver
ASSUMPTIONS G8-04): replicar la cadencia contractual completa durante
TODA la historia de 5+ años excedería en varios ordenes de magnitud el
objetivo (harian falta invenar una cadencia sin base contractual), y
respetar solo los ultimos 30 dias de retencion es la unica lectura no
arbitraria disponible."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from core.db.models.accounts import Account
from core.db.models.market import EquitySnapshot, HeartbeatLog, IngestBatch
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from seed_lib.trades_history import GeneratedTrade, trading_days

_MONEY_QUANT = Decimal("0.01")
_DD_QUANT = Decimal("0.001")
_HEARTBEAT_CADENCE = timedelta(seconds=60)  # ASSUMPTIONS G4: heartbeat_interval_s=60.0
_HEARTBEAT_RETENTION_DAYS = 30  # HeartbeatLog.__doc__: "Retencion 30 dias" (PARTE 5.2)


@dataclass(frozen=True)
class GeneratedEquitySnapshot:
    account_id: int
    ts: datetime
    equity: Decimal
    balance: Decimal
    drawdown_pct: Decimal


def generate_equity_snapshots(
    account_id: int,
    trades: list[GeneratedTrade],
    history_start: date,
    history_end: date,
    initial_balance: Decimal,
) -> list[GeneratedEquitySnapshot]:
    daily_pnl: dict[date, Decimal] = defaultdict(Decimal)
    for t in trades:
        daily_pnl[t.open_time.date()] += t.profit

    balance = initial_balance
    peak = initial_balance
    # Snapshot de apertura ANTES de cualquier trade -- 7.9 lee el PRIMER
    # EquitySnapshot como "balance inicial" de la reconciliacion; sin este
    # punto, ese primer snapshot ya incluiria el P&L del primer dia y
    # `flows` (suma de TODOS los trades) lo contaria dos veces, dejando un
    # descuadre falso igual al P&L de ese primer dia (bug real encontrado
    # y corregido en esta misma sesion, ver ASSUMPTIONS G8-04).
    snapshots: list[GeneratedEquitySnapshot] = [
        GeneratedEquitySnapshot(
            account_id=account_id,
            ts=datetime.combine(history_start, time(0, 0), tzinfo=UTC),
            equity=initial_balance,
            balance=initial_balance,
            drawdown_pct=Decimal("0"),
        )
    ]
    for day in trading_days(history_start, history_end):
        balance = (balance + daily_pnl.get(day, Decimal("0"))).quantize(
            _MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        peak = max(peak, balance)
        dd_pct = ((peak - balance) / peak * 100) if peak > 0 else Decimal("0")
        snapshots.append(
            GeneratedEquitySnapshot(
                account_id=account_id,
                ts=datetime.combine(day, time(23, 0), tzinfo=UTC),
                equity=balance,
                balance=balance,
                drawdown_pct=dd_pct.quantize(_DD_QUANT, rounding=ROUND_HALF_UP),
            )
        )
    return snapshots


async def bulk_insert_equity_snapshots(
    session: AsyncSession, account: Account, snapshots: list[GeneratedEquitySnapshot]
) -> tuple[int, int]:
    """Un IngestBatch sellado por dia (batch_type='equity'), mismo patron
    que trades_history.py::bulk_insert_trades."""
    if not snapshots:
        return 0, 0

    batch_rows = []
    for snap in snapshots:
        payload = [
            {
                "ts": snap.ts.isoformat(),
                "equity": str(snap.equity),
                "balance": str(snap.balance),
            }
        ]
        batch_rows.append(
            {
                "ts": snap.ts,
                "connector_instance_id": account.connector_instance_id or "seed-generator",
                "account_id": account.id,
                "batch_type": "equity",
                "records": 1,
                "sha256": compute_batch_sha256(account.login, "equity", payload),
                "server_ts": snap.ts,
            }
        )
    await session.execute(insert(IngestBatch), batch_rows)

    snapshot_rows = [
        {
            "ts": s.ts,
            "account_id": s.account_id,
            "equity": s.equity,
            "balance": s.balance,
            "drawdown_pct": s.drawdown_pct,
            "margin_level": None,
            "free_margin": None,
        }
        for s in snapshots
    ]
    await session.execute(insert(EquitySnapshot), snapshot_rows)

    return len(snapshot_rows), len(batch_rows)


async def bulk_insert_heartbeats(
    session: AsyncSession, account: Account, history_end: datetime
) -> tuple[int, int]:
    """Cadencia real (60s) restringida a los ultimos 30 dias -- ver
    docstring del modulo. Un IngestBatch sellado por heartbeat (sin
    buffering, PARTE 5.1 no describe agregacion de heartbeats)."""
    window_start = history_end - timedelta(days=_HEARTBEAT_RETENTION_DAYS)
    connector_id = account.connector_instance_id or "seed-generator"

    heartbeat_rows = []
    batch_rows = []
    ts = window_start
    while ts <= history_end:
        heartbeat_rows.append(
            {
                "ts": ts,
                "connector_instance_id": connector_id,
                "account_id": account.id,
                "latency_ms": 45,
                "status": "OK",
            }
        )
        payload = [{"ts": ts.isoformat(), "status": "OK"}]
        batch_rows.append(
            {
                "ts": ts,
                "connector_instance_id": connector_id,
                "account_id": account.id,
                "batch_type": "heartbeat",
                "records": 1,
                "sha256": compute_batch_sha256(account.login, "heartbeat", payload),
                "server_ts": ts,
            }
        )
        ts += _HEARTBEAT_CADENCE

    await session.execute(insert(HeartbeatLog), heartbeat_rows)
    await session.execute(insert(IngestBatch), batch_rows)
    return len(heartbeat_rows), len(batch_rows)
