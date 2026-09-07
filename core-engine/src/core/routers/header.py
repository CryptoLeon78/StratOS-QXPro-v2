"""PARTE 9.2: `GET /api/v1/header/summary` + `/summary/equity-curve` --
cabecera del dashboard (AppHeader, 6 StatCard). Query directa (sin
services/ propio, mismo criterio que el resto de endpoints "trivial" del
plan de G5); reutiliza `risk.py::real_portfolio_equity_curve` y
`killswitch_sweep.py::compute_portfolio_dd_pct` (ya existen).

Sin conversion de divisa (mismo hueco documentado en risk.py/config_drift.py):
`equity_eur` suma el `equity` crudo de las cuentas REALES tal cual lo
reporta MT5, no convertido via `FxRate` (tabla migrada en G1, sin ningun
consumidor todavia)."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import AccountDataOrigin, DecisionStatus, PipelinePhase, SemaphoreState
from core.db.models.accounts import Account, Bot
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


def _thresholds_seed_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "config" / "thresholds.seed.json"
        if candidate.is_file():
            return candidate
    raise RuntimeError("thresholds.seed.json is required by the header router")


def _load_header_thresholds() -> tuple[int, dict[str, int], dict[str, int]]:
    thresholds = json.loads(_thresholds_seed_path().read_text(encoding="utf-8"))
    return (
        int(thresholds["header_heartbeat_stale_after_s"]),
        {name: int(days) for name, days in thresholds["equity_curve_lookback_days"].items()},
        {name: int(days) for name, days in thresholds["header_pnl_window_days"].items()},
    )


_HEARTBEAT_STALE_AFTER_S, _EQUITY_CURVE_LOOKBACK_DAYS, _PNL_WINDOW_DAYS = _load_header_thresholds()


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
    heartbeat_age_seconds = (now - last_heartbeat).total_seconds() if last_heartbeat else None
    mt_connected = (
        heartbeat_age_seconds is not None and heartbeat_age_seconds <= _HEARTBEAT_STALE_AFTER_S
    )
    # El contrato de `data_stale_seconds` es una señal de incidencia para la
    # UI, no la edad de cualquier dato: si el heartbeat sigue dentro del
    # umbral, debe ser None para que el badge no etiquete telemetría fresca
    # como "DATOS STALE".
    data_stale_seconds = (
        int(heartbeat_age_seconds)
        if heartbeat_age_seconds is not None and not mt_connected
        else None
    )

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
        pnl_day=_pnl_since(_PNL_WINDOW_DAYS["day"]),
        pnl_week=_pnl_since(_PNL_WINDOW_DAYS["week"]),
        pnl_month=_pnl_since(_PNL_WINDOW_DAYS["month"]),
        portfolio_dd_pct=dd_pct,
        ks_level=ks_level,
        global_semaphore=global_semaphore,
        mt_connected=mt_connected,
        open_positions=open_positions,
        alerts=alerts,
        pending_decisions=pending_decisions,
        data_stale_seconds=data_stale_seconds,
    )


class ProvenanceRow(BaseModel):
    data_origin: AccountDataOrigin
    accounts: int
    bots: int


class TradeAttributionCoverage(BaseModel):
    """Que parte de las cifras agregadas pertenece a un bot vivo.

    Las metricas POR BOT ya cubren solo EAs vivos: un EA retirado no tiene fila en `bot`, asi
    que no aparece en ningun sitio. El hueco esta en los agregados de Portfolio, Riesgo y
    Auditoria, que suman todos los trades de la cuenta -- incluidos los de EAs retirados hace
    meses y los del historico HTML, que no publica magic.

    Decision del operador (2026-09-02): los EAs retirados no se inventarian ni se presentan.
    Pero una cifra agregada tiene que poder decir cuanta de ella no es de ningun bot vivo, en
    vez de presentarse como si todo el total fuera del portfolio actual.
    """

    total: int
    attributed_to_live_bot: int
    retired_ea: int
    without_ea: int
    coverage_pct: float | None


class DataProvenanceResponse(BaseModel):
    """De qué universos se compone lo que muestran las vistas agregadas.

    En Portfolio, Salud, Riesgo, Auditoría y Dominical la procedencia no es un campo de una
    fila: es una propiedad del agregado. El recorrido G12 encontró que esas superficies
    sumaban fixture y telemetría real en la misma cifra sin que nada lo dijera, y por eso el
    operador no podía fiarse de los números. Aquí se declara la composición real para que la
    UI la muestre en vez de callarla.

    `is_mixed` es el dato accionable: con un solo origen, las cifras significan una cosa; con
    varios, cualquier total agrega universos distintos.
    """

    accounts: list[ProvenanceRow]
    is_mixed: bool
    trade_attribution: TradeAttributionCoverage


@router.get("/data-provenance", response_model=DataProvenanceResponse)
async def data_provenance(
    session: AsyncSession = Depends(get_session),
) -> DataProvenanceResponse:
    rows = (
        await session.execute(
            select(
                Account.data_origin,
                func.count(func.distinct(Account.id)),
                func.count(Bot.id),
            )
            .select_from(Account)
            .outerjoin(Bot, Bot.account_id == Account.id)
            .group_by(Account.data_origin)
            .order_by(Account.data_origin)
        )
    ).all()
    composicion = [
        ProvenanceRow(data_origin=origin, accounts=n_accounts, bots=n_bots)
        for origin, n_accounts, n_bots in rows
    ]
    total, atribuidos, sin_ea = (
        await session.execute(
            select(
                func.count(Trade.ticket_mt5),
                func.count(Trade.bot_id),
                func.count(Trade.ticket_mt5).filter(Trade.magic_number == 0),
            )
        )
    ).one()
    # `magic=0` es ausencia declarada de EA (operacion manual o del broker, o un historico
    # que no publica magic); el resto de huerfanos son EAs retirados que ya no tienen bot.
    retirados = total - atribuidos - sin_ea
    atribucion = TradeAttributionCoverage(
        total=total,
        attributed_to_live_bot=atribuidos,
        retired_ea=retirados,
        without_ea=sin_ea,
        # Sin trades no hay cobertura del 0 %: no hay nada que cubrir. Se declara ausencia.
        coverage_pct=round(100 * atribuidos / total, 2) if total else None,
    )

    # Una base vacía es ausencia, no mezcla: no se infiere procedencia de lo que no hay.
    return DataProvenanceResponse(
        accounts=composicion, is_mixed=len(composicion) > 1, trade_attribution=atribucion
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
