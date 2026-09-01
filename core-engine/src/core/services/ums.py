"""PARTE 7.9: escalado UMS en 6 fases. `UmsPhaseLog` (governance.py) es un
log append-only de TRANSICIONES reales (no de evaluaciones cualquiera):
"fase actual" = fase de la ultima fila. Regla asimetrica: subir de fase
exige metricas sostenidas + firma humana (`signed_by` NOT NULL);
bajar de fase es automatico si el equity cae bajo el rango de la fase
vigente (proteccion, sin firma -- `signed_by` NULL, migracion G5-0004)."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.db.models.governance import UmsPhaseLog
from core.db.models.market import Trade
from core.formulas.trading import max_drawdown_pct
from core.services.risk import real_portfolio_equity_curve

_AVG_DAYS_PER_MONTH = 30.44


@dataclass(frozen=True)
class UmsPhaseDef:
    phase: int
    name: str
    equity_min: Decimal
    equity_max: Decimal | None
    kelly_fraction: Decimal
    risk_per_trade_pct_min: Decimal | None = None
    risk_per_trade_pct_max: Decimal | None = None
    risk_note: str | None = None


# Refleja 1:1 `ums_phases` de config/thresholds.seed.json (tabla 7.9) -- el
# JSON es la fuente unica (P11), esto es solo para invocabilidad sin cargar
# el fichero completo (mismo patron que state_machines/types.py, G3).
DEFAULT_UMS_PHASES: tuple[UmsPhaseDef, ...] = (
    UmsPhaseDef(
        1,
        "Validacion Personal",
        Decimal("0"),
        Decimal("5000"),
        Decimal("0.5"),
        risk_note="micro-lotes",
    ),
    UmsPhaseDef(
        2,
        "Track Record",
        Decimal("5000"),
        Decimal("25000"),
        Decimal("0.5"),
        risk_per_trade_pct_min=Decimal("1.0"),
        risk_per_trade_pct_max=Decimal("1.5"),
    ),
    UmsPhaseDef(
        3,
        "Portfolio Maduro",
        Decimal("25000"),
        Decimal("100000"),
        Decimal("0.33"),
        risk_per_trade_pct_min=Decimal("0.5"),
        risk_per_trade_pct_max=Decimal("1.0"),
    ),
    UmsPhaseDef(
        4,
        "Semi-Profesional",
        Decimal("100000"),
        Decimal("500000"),
        Decimal("0.25"),
        risk_per_trade_pct_min=Decimal("0.3"),
        risk_per_trade_pct_max=Decimal("0.7"),
    ),
    UmsPhaseDef(5, "Semi-Institucional", Decimal("500000"), Decimal("1000000"), Decimal("0.2")),
    UmsPhaseDef(6, "Institucional", Decimal("1000000"), None, Decimal("0.2")),
)


@dataclass(frozen=True)
class UmsConfig:
    phases: tuple[UmsPhaseDef, ...] = DEFAULT_UMS_PHASES
    min_months: int = 3
    min_sharpe: float = 1.0
    max_dd_gate_pct: Decimal = Decimal("8")


@dataclass(frozen=True)
class UmsMetrics:
    sharpe: float
    dd_pct: Decimal


@dataclass(frozen=True)
class UmsCurrentState:
    phase: int
    entered_at: datetime


@dataclass(frozen=True)
class UmsReadiness:
    current_phase: int
    months_in_phase: float
    ready_to_advance: bool
    reason: str | None


def _phase_for_equity(equity: Decimal, phases: tuple[UmsPhaseDef, ...]) -> UmsPhaseDef:
    for phase_def in phases:
        if equity >= phase_def.equity_min and (
            phase_def.equity_max is None or equity < phase_def.equity_max
        ):
            return phase_def
    return phases[0] if equity < phases[0].equity_min else phases[-1]


def evaluate_advance_readiness(
    current: UmsCurrentState | None, metrics: UmsMetrics, config: UmsConfig, now: datetime
) -> UmsReadiness:
    if current is None:
        return UmsReadiness(
            current_phase=1,
            months_in_phase=0.0,
            ready_to_advance=False,
            reason="sin fase UMS registrada",
        )

    months_in_phase = (now - current.entered_at).days / _AVG_DAYS_PER_MONTH
    if months_in_phase < config.min_months:
        return UmsReadiness(current.phase, months_in_phase, False, "meses insuficientes en fase")
    if metrics.sharpe < config.min_sharpe:
        return UmsReadiness(current.phase, months_in_phase, False, "sharpe por debajo del gate")
    if metrics.dd_pct >= config.max_dd_gate_pct:
        return UmsReadiness(current.phase, months_in_phase, False, "drawdown fuera del gate")
    return UmsReadiness(current.phase, months_in_phase, True, None)


async def monthly_evolution_metrics(session: AsyncSession, now: datetime) -> dict[str, Any]:
    """G10 (docs/backlog.md): `trades`/`retorno_pct`/`max_dd_pct` del
    ultimo mes (`_AVG_DAYS_PER_MONTH` dias, misma constante ya usada en
    este modulo), para la columna "Evolucion mensual" de Escalado --
    trades CERRADOS reales + curva de equity real de portfolio
    (`real_portfolio_equity_curve`, `services/risk.py`, ya existe G5).
    Sin equity suficiente en la ventana, `retorno_pct`/`max_dd_pct` quedan
    en `None` -- no se inventan."""
    window_start = now - timedelta(days=_AVG_DAYS_PER_MONTH)
    trades_count = (
        await session.execute(
            select(func.count(Trade.id)).where(
                Trade.close_time.isnot(None),
                Trade.close_time >= window_start,
                Trade.close_time <= now,
            )
        )
    ).scalar() or 0

    equity_curve = await real_portfolio_equity_curve(session, window_start)
    if len(equity_curve) < 2:
        return {"trades": trades_count, "retorno_pct": None, "max_dd_pct": None}

    start_equity = float(equity_curve.iloc[0])
    end_equity = float(equity_curve.iloc[-1])
    retorno_pct = (end_equity - start_equity) / start_equity * 100 if start_equity > 0 else None
    dd_curve = [Decimal(str(v)) for v in equity_curve]

    return {
        "trades": trades_count,
        "retorno_pct": retorno_pct,
        "max_dd_pct": str(max_drawdown_pct(dd_curve)),
    }


async def current_phase(session: AsyncSession) -> UmsPhaseLog | None:
    return (
        await session.execute(select(UmsPhaseLog).order_by(UmsPhaseLog.ts.desc()).limit(1))
    ).scalar_one_or_none()


async def confirm_advance(
    session: AsyncSession,
    metrics: UmsMetrics,
    config: UmsConfig,
    signed_by: str,
    current_equity: Decimal,
    now: datetime,
) -> UmsPhaseLog:
    """Re-evalua siempre (nunca confia en un `ready_to_advance` de hace
    rato) y rechaza si no cumple, antes de tocar la BBDD."""
    last = await current_phase(session)
    current_state = (
        UmsCurrentState(phase=last.phase, entered_at=last.ts) if last is not None else None
    )
    readiness = evaluate_advance_readiness(current_state, metrics, config, now)
    if not readiness.ready_to_advance:
        raise ValueError(f"UMS: no cumple los requisitos de ascenso ({readiness.reason})")

    next_phase = readiness.current_phase + 1
    if next_phase > len(config.phases):
        raise ValueError("UMS: ya en la fase institucional maxima, no hay ascenso posible")

    row = UmsPhaseLog(
        ts=now,
        phase=next_phase,
        equity_at=current_equity,
        metrics={
            "sharpe": metrics.sharpe,
            "dd_pct": str(metrics.dd_pct),
            **await monthly_evolution_metrics(session, now),
        },
        ready_to_advance=True,
        signed_by=signed_by,
    )
    session.add(row)
    await session.flush()
    return row


async def check_automatic_downgrade(
    session: AsyncSession,
    redis: Redis,
    config: UmsConfig,
    current_equity: Decimal,
    now: datetime,
) -> None:
    last = await current_phase(session)
    if last is None:
        return

    target_phase = _phase_for_equity(current_equity, config.phases)
    if target_phase.phase >= last.phase:
        return

    row = UmsPhaseLog(
        ts=now,
        phase=target_phase.phase,
        equity_at=current_equity,
        metrics=await monthly_evolution_metrics(session, now),
        ready_to_advance=False,
        signed_by=None,
    )
    session.add(row)

    dedup_key = f"ums:downgrade:{now.date().isoformat()}"
    alert = Alert(
        ts=now,
        level=AlertLevel.CRITICA,
        module="ums",
        message=(
            f"Bajada automatica de fase UMS: {last.phase} -> {target_phase.phase} "
            f"(equity {current_equity})."
        ),
        action_required="Revisar la causa de la caida de equity.",
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
