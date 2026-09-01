"""PARTE 9.2: `GET /api/v1/execution/watchdog` + `/heartbeat` -- pestaña
Ejecucion (7.8). Reutiliza `watchdog.py::evaluate_all_bots` y
`audit.py::compute_send_continuity` (ya existen, G5) para uptime 7 dias."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.models.accounts import Account
from core.db.models.market import HeartbeatLog
from core.formulas.types import WatchdogState
from core.services.audit import AuditConfig, compute_send_continuity
from core.services.tca import tca_summary
from core.services.watchdog import WatchdogServiceConfig, evaluate_all_bots

router = APIRouter(
    prefix="/api/v1/execution", tags=["execution"], dependencies=[Depends(get_current_user)]
)

_WATCHDOG_CONFIG = WatchdogServiceConfig()
_AUDIT_CONFIG = AuditConfig()


class WatchdogRowResponse(BaseModel):
    bot_id: int
    magic_number: int
    state: WatchdogState
    observed_30d: int
    expected_month: int | None
    last_trade_at: datetime | None


class HeartbeatResponse(BaseModel):
    account_id: int
    last_ts: datetime | None
    latency_ms: int | None
    uptime_pct_7d: float
    connected: bool


class TcaResponse(BaseModel):
    fills: int
    slippage_p50: Decimal | None
    slippage_p95: Decimal | None
    slippage_p99: Decimal | None
    asymmetry_index: float | None
    implementation_shortfall_p50: Decimal | None
    rejected_orders: int
    broker_profiles: list["BrokerProfileResponse"]


class BrokerProfileResponse(BaseModel):
    broker: str
    symbol: str
    fills: int
    spread_p50: Decimal | None


@router.get("/watchdog", response_model=list[WatchdogRowResponse])
async def execution_watchdog(
    session: AsyncSession = Depends(get_session),
) -> list[WatchdogRowResponse]:
    rows = await evaluate_all_bots(session, _WATCHDOG_CONFIG, datetime.now(UTC))
    return [WatchdogRowResponse.model_validate(row, from_attributes=True) for row in rows]


@router.get("/heartbeat", response_model=list[HeartbeatResponse])
async def execution_heartbeat(
    session: AsyncSession = Depends(get_session),
) -> list[HeartbeatResponse]:
    now = datetime.now(UTC)
    account_ids = (await session.execute(select(Account.id))).scalars().all()
    rows = []
    for account_id in account_ids:
        last = (
            await session.execute(
                select(HeartbeatLog)
                .where(HeartbeatLog.account_id == account_id)
                .order_by(HeartbeatLog.ts.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        continuity = await compute_send_continuity(session, account_id, _AUDIT_CONFIG, 7, now)
        stale_after = _AUDIT_CONFIG.heartbeat_gap_threshold_s
        connected = last is not None and (now - last.ts).total_seconds() <= stale_after
        rows.append(
            HeartbeatResponse(
                account_id=account_id,
                last_ts=last.ts if last else None,
                latency_ms=last.latency_ms if last else None,
                uptime_pct_7d=continuity.coverage_pct,
                connected=connected,
            )
        )
    return rows


@router.get("/tca", response_model=TcaResponse | None)
async def execution_tca(session: AsyncSession = Depends(get_session)) -> TcaResponse | None:
    summary = await tca_summary(session)
    return TcaResponse.model_validate(summary, from_attributes=True) if summary else None
