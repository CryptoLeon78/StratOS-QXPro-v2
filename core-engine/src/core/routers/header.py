"""PARTE 9.2: `GET /api/v1/header/summary` + `/summary/equity-curve` --
cabecera del dashboard (AppHeader, 6 StatCard). Query directa (sin
services/ propio, mismo criterio que el resto de endpoints "trivial" del
plan de G5); reutiliza `risk.py::real_portfolio_equity_curve` y
`killswitch_sweep.py::compute_portfolio_dd_pct` (ya existen).

Sin conversion de divisa (mismo hueco documentado en risk.py/config_drift.py):
`equity_eur` suma el `equity` crudo de las cuentas REALES tal cual lo
reporta MT5, no convertido via `FxRate` (tabla migrada en G1, sin ningun
consumidor todavia)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import DecisionStatus, PipelinePhase, SemaphoreState
from core.db.models.accounts import Bot
from core.db.models.decisions import Alert, Decision, KillSwitchEvent
from core.db.models.market import HeartbeatLog, Trade
from core.services.killswitch_sweep import KillSwitchSweepConfig, compute_portfolio_dd_pct
from core.services.risk import real_portfolio_equity_curve

router = APIRouter(prefix="/api/v1", tags=["header"], dependencies=[Depends(get_current_user)])

_SEMAPHORE_SEVERITY = {
    SemaphoreState.VERDE: 0,
    SemaphoreState.AMARILLO: 1,
    SemaphoreState.NARANJA: 2,
}
_HEARTBEAT_STALE_AFTER_S = 120  # header_heartbeat_stale_after_s, thresholds.seed.json
_EQUITY_CURVE_LOOKBACK_DAYS = {"30d": 30, "90d": 90, "180d": 180, "1y": 365, "all": 3650}


class HeaderSummaryResponse(BaseModel):
    equity_eur: Decimal
    pnl_day: Decimal
    pnl_week: Decimal
    pnl_month: Decimal
    portfolio_dd_pct: Decimal
    ks_level: int
    global_semaphore: str
    mt_connected: bool
    open_positions: int
    alerts: int
    pending_decisions: int
    data_stale_seconds: int | None


class EquityCurvePoint(BaseModel):
    date: str
    equity: Decimal


async def compute_header_summary(
    session: AsyncSession, *, now: datetime | None = None
) -> HeaderSummaryResponse:
    """Calcula la cabecera con un reloj explícito para fixtures verificables.

    Los handlers HTTP no exponen ``now``: en producción siempre se usa UTC
    actual. El seed full congelado lo aporta solo para su auto-verificación.
    """
    now = now or datetime.now(UTC)
    curve = await real_portfolio_equity_curve(session, now - timedelta(days=35))
    equity_eur = Decimal(str(curve.iloc[-1])) if not curve.empty else Decimal("0")

    def _pnl_since(days: int) -> Decimal:
        if curve.empty:
            return Decimal("0")
        past = curve.asof(pd.Timestamp((now - timedelta(days=days)).date()))
        if pd.isna(past):
            return Decimal("0")
        return equity_eur - Decimal(str(past))

    dd_pct = await compute_portfolio_dd_pct(session, KillSwitchSweepConfig(), now) or Decimal("0")
    ks_level = (
        await session.execute(
            select(KillSwitchEvent.level).order_by(KillSwitchEvent.ts.desc()).limit(1)
        )
    ).scalar_one_or_none() or 0

    bot_states = (
        (
            await session.execute(
                select(Bot.semaphore_state).where(
                    Bot.pipeline_phase.in_((PipelinePhase.F7, PipelinePhase.PRODUCCION))
                )
            )
        )
        .scalars()
        .all()
    )
    global_semaphore = (
        max(bot_states, key=lambda s: _SEMAPHORE_SEVERITY[s]).value if bot_states else "VERDE"
    )

    last_heartbeat = (await session.execute(select(func.max(HeartbeatLog.ts)))).scalar_one_or_none()
    data_stale_seconds = int((now - last_heartbeat).total_seconds()) if last_heartbeat else None
    mt_connected = data_stale_seconds is not None and data_stale_seconds <= _HEARTBEAT_STALE_AFTER_S

    open_positions = (
        await session.execute(select(func.count(Trade.id)).where(Trade.close_time.is_(None)))
    ).scalar() or 0
    alerts = (
        await session.execute(select(func.count(Alert.id)).where(Alert.resolved.is_(False)))
    ).scalar_one()
    pending_decisions = (
        await session.execute(
            select(func.count(Decision.id)).where(Decision.status == DecisionStatus.PENDING)
        )
    ).scalar_one()

    return HeaderSummaryResponse(
        equity_eur=equity_eur,
        pnl_day=_pnl_since(1),
        pnl_week=_pnl_since(7),
        pnl_month=_pnl_since(30),
        portfolio_dd_pct=dd_pct,
        ks_level=ks_level,
        global_semaphore=global_semaphore,
        mt_connected=mt_connected,
        open_positions=open_positions,
        alerts=alerts,
        pending_decisions=pending_decisions,
        data_stale_seconds=data_stale_seconds,
    )


@router.get("/header/summary", response_model=HeaderSummaryResponse)
async def header_summary(session: AsyncSession = Depends(get_session)) -> HeaderSummaryResponse:
    return await compute_header_summary(session)


@router.get("/summary/equity-curve", response_model=list[EquityCurvePoint])
async def equity_curve(
    range_: Literal["30d", "90d", "180d", "1y", "all"] = Query(default="90d", alias="range"),
    session: AsyncSession = Depends(get_session),
) -> list[EquityCurvePoint]:
    now = datetime.now(UTC)
    lookback_days = _EQUITY_CURVE_LOOKBACK_DAYS[range_]
    curve = await real_portfolio_equity_curve(session, now - timedelta(days=lookback_days))
    # pandas-stubs tipa `.items()` como `Iterable[tuple[Hashable, Any]]` --
    # demasiado generico para que mypy --strict reconozca el indice como
    # fecha (mismo problema documentado en services/correlations.py).
    return [
        EquityCurvePoint(date=str(pd.Timestamp(idx).date()), equity=Decimal(str(value)))  # type: ignore[arg-type]
        for idx, value in curve.items()
    ]
