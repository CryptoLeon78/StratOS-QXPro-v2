"""PARTE 9.2: `GET /api/v1/health/bots` -- pestaña Salud (7.6, grid de
tarjetas por bot). Reutiliza `semaphore_sweep.py::assemble_semaphore_metrics`
(ya existe, G5) para las chips de metricas rodantes vs baseline +
`assemble_health_chips` (G10, docs/backlog.md) para Win Rate drift/
Payoff/Duracion media/Sharpe rolling."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import BotProfile, PipelinePhase, SemaphoreState
from core.db.models.accounts import Baseline, Bot
from core.services.semaphore_sweep import (
    SemaphoreSweepConfig,
    assemble_health_chips,
    assemble_semaphore_metrics,
)

router = APIRouter(
    prefix="/api/v1/health", tags=["health"], dependencies=[Depends(get_current_user)]
)

_SWEEP_CONFIG = SemaphoreSweepConfig()


class HealthRow(BaseModel):
    bot_id: int
    magic_number: int
    name: str
    profile: BotProfile
    pipeline_phase: PipelinePhase
    semaphore_state: SemaphoreState
    days_in_state: int
    pf_rolling: float
    pf_baseline: float
    exp_rolling: float
    exp_baseline: float
    loss_streak: int
    dd_bot_pct: Decimal
    dd_contract_pct: Decimal
    page_hinkley_triggered: bool
    win_rate_drift: float
    payoff: float | None
    avg_trade_duration_min: float | None
    sharpe_rolling: float


@router.get("/bots", response_model=list[HealthRow])
async def health_bots(session: AsyncSession = Depends(get_session)) -> list[HealthRow]:
    now = datetime.now(UTC)
    bots = (await session.execute(select(Bot).where(Bot.baseline_id.is_not(None)))).scalars().all()
    rows: list[HealthRow] = []
    for bot in bots:
        baseline = await session.get(Baseline, bot.baseline_id)
        if baseline is None:
            continue
        metrics = await assemble_semaphore_metrics(session, bot, baseline, _SWEEP_CONFIG)
        chips = await assemble_health_chips(session, bot, baseline, _SWEEP_CONFIG)
        rows.append(
            HealthRow(
                bot_id=bot.id,
                magic_number=bot.magic_number,
                name=bot.name,
                profile=bot.profile,
                pipeline_phase=bot.pipeline_phase,
                semaphore_state=bot.semaphore_state,
                days_in_state=(now - bot.entered_state_at).days,
                pf_rolling=metrics.pf_rolling,
                pf_baseline=metrics.pf_baseline,
                exp_rolling=metrics.exp_rolling,
                exp_baseline=metrics.exp_baseline,
                loss_streak=metrics.loss_streak,
                dd_bot_pct=metrics.dd_bot_pct,
                dd_contract_pct=metrics.dd_contract_pct,
                page_hinkley_triggered=metrics.page_hinkley_triggered,
                win_rate_drift=chips.win_rate_drift,
                payoff=chips.payoff,
                avg_trade_duration_min=chips.avg_trade_duration_min,
                sharpe_rolling=chips.sharpe_rolling,
            )
        )
    return rows
