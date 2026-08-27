"""PARTE 9.2: `GET /api/v1/bots` + `/{id}` + `/{id}/semaphore-history` --
pestaña Bots (7.4, layout maestro-detalle). Query directa.

`/{id}/open-positions` (G10, docs/backlog.md): reutiliza
`services/bot_equity.py::bot_open_positions()` (G10 tambien).

`/{id}/pnl-curve` + `/{id}/r-multiples` + `/{id}/metrics` (G10, docs/
backlog.md): panel "P&L acumulado"/"Histograma de retornos (R)"/
"Rolling vs Baseline"/"Metricas completas"/"Contribucion al portfolio" de
7.4 -- reutilizan `services/bot_equity.py` + `services/semaphore_sweep.py`
(G10), sin formula nueva en este router."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import BotProfile, BotRole, PipelinePhase, SemaphoreState, TradeType
from core.db.models.accounts import Baseline, Bot
from core.db.models.decisions import SemaphoreTransition
from core.formulas.pipeline import trades_per_week as trades_per_week_formula
from core.services.bot_equity import (
    bot_open_positions,
    bot_pnl_curve_with_dates,
    bot_r_multiples,
    compute_curve_metrics,
    compute_portfolio_contribution,
)
from core.services.semaphore_sweep import (
    SemaphoreSweepConfig,
    assemble_health_chips,
    assemble_semaphore_metrics,
)

_SWEEP_CONFIG = SemaphoreSweepConfig()
_WEEKS_PER_MONTH = 4.345  # 52/12 -- misma convencion que trades_per_week_formula (semanas)

router = APIRouter(prefix="/api/v1/bots", tags=["bots"], dependencies=[Depends(get_current_user)])


class BotResponse(BaseModel):
    id: int
    account_id: int
    magic_number: int
    name: str
    market: str
    timeframe: str
    profile: BotProfile
    role: BotRole
    slot: str | None
    pipeline_phase: PipelinePhase
    semaphore_state: SemaphoreState
    entered_state_at: datetime
    capital_allocated_pct: Decimal
    risk_per_trade_pct: Decimal
    sizing_multiplier: Decimal
    sizing_current_pct: Decimal
    kelly_fraction: Decimal | None
    created_at: datetime
    baseline_id: int | None

    model_config = {"from_attributes": True}


class OpenPositionRow(BaseModel):
    id: int
    ticket_mt5: int
    symbol: str
    type: TradeType
    open_time: datetime
    volume: Decimal
    open_price: Decimal
    sl: Decimal | None
    tp: Decimal | None
    profit: Decimal

    model_config = {"from_attributes": True}


class PnlCurvePoint(BaseModel):
    ts: datetime | None
    cumulative_pnl: Decimal


class BotMetricsResponse(BaseModel):
    has_baseline: bool
    # rolling
    sharpe_rolling: float | None
    pf_rolling: float | None
    exp_rolling: float | None
    win_rate_rolling: float | None
    payoff_rolling: float | None
    avg_trade_duration_rolling_min: float | None
    loss_streak: int | None
    dd_rolling_pct: Decimal | None
    # baseline
    sharpe_baseline: float | None
    pf_baseline: float | None
    exp_baseline: float | None
    win_rate_baseline: float | None
    payoff_baseline: float | None
    avg_trade_duration_baseline_min: float | None
    dd_contract_pct: Decimal | None
    # curva (no exige baseline)
    sortino: float | None
    calmar: float | None
    max_dd_pct: float
    ulcer_index: float
    recovery_factor: float | None
    net_pnl: Decimal
    trades_per_month: float
    # contribucion al portfolio
    pct_of_total_pnl: float | None
    correlation_vs_rest: float | None
    pnl_bot: Decimal
    pnl_account: Decimal


class SemaphoreHistoryRow(BaseModel):
    id: int
    ts: datetime
    from_state: SemaphoreState
    to_state: SemaphoreState
    trigger_metrics: dict[str, Any]
    instruction_text: str
    confirmed_at: datetime | None
    confirmed_by: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[BotResponse])
async def list_bots(session: AsyncSession = Depends(get_session)) -> list[Bot]:
    return list((await session.execute(select(Bot))).scalars().all())


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: int, session: AsyncSession = Depends(get_session)) -> Bot:
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    return bot


@router.get("/{bot_id}/open-positions", response_model=list[OpenPositionRow])
async def open_positions(
    bot_id: int, session: AsyncSession = Depends(get_session)
) -> list[OpenPositionRow]:
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    trades = await bot_open_positions(session, bot_id)
    return [OpenPositionRow.model_validate(t) for t in trades]


@router.get("/{bot_id}/pnl-curve", response_model=list[PnlCurvePoint])
async def pnl_curve(
    bot_id: int, session: AsyncSession = Depends(get_session)
) -> list[PnlCurvePoint]:
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    points = await bot_pnl_curve_with_dates(session, bot_id)
    return [PnlCurvePoint(ts=ts, cumulative_pnl=value) for ts, value in points]


@router.get("/{bot_id}/r-multiples", response_model=list[Decimal])
async def r_multiples(bot_id: int, session: AsyncSession = Depends(get_session)) -> list[Decimal]:
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    return await bot_r_multiples(session, bot_id)


@router.get("/{bot_id}/metrics", response_model=BotMetricsResponse)
async def bot_metrics(
    bot_id: int, session: AsyncSession = Depends(get_session)
) -> BotMetricsResponse:
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")

    curve = await bot_pnl_curve_with_dates(session, bot_id)
    curve_values = [value for _, value in curve]
    curve_metrics = compute_curve_metrics(curve_values)
    contribution = await compute_portfolio_contribution(session, bot)

    now = datetime.now(UTC)
    window_days = 30
    recent_close_times = [
        ts for ts, _ in curve if ts is not None and ts >= now - timedelta(days=window_days)
    ]
    trades_per_month = (
        trades_per_week_formula(recent_close_times, window_days=window_days) * _WEEKS_PER_MONTH
    )

    baseline = await session.get(Baseline, bot.baseline_id) if bot.baseline_id else None
    if baseline is None:
        return BotMetricsResponse(
            has_baseline=False,
            sharpe_rolling=None,
            pf_rolling=None,
            exp_rolling=None,
            win_rate_rolling=None,
            payoff_rolling=None,
            avg_trade_duration_rolling_min=None,
            loss_streak=None,
            dd_rolling_pct=None,
            sharpe_baseline=None,
            pf_baseline=None,
            exp_baseline=None,
            win_rate_baseline=None,
            payoff_baseline=None,
            avg_trade_duration_baseline_min=None,
            dd_contract_pct=None,
            sortino=curve_metrics.sortino,
            calmar=curve_metrics.calmar,
            max_dd_pct=curve_metrics.max_dd_pct,
            ulcer_index=curve_metrics.ulcer_index,
            recovery_factor=curve_metrics.recovery_factor,
            net_pnl=curve_metrics.net_pnl,
            trades_per_month=trades_per_month,
            pct_of_total_pnl=contribution.pct_of_total_pnl,
            correlation_vs_rest=contribution.correlation_vs_rest,
            pnl_bot=contribution.pnl_bot,
            pnl_account=contribution.pnl_account,
        )

    semaphore_metrics = await assemble_semaphore_metrics(session, bot, baseline, _SWEEP_CONFIG)
    chips = await assemble_health_chips(session, bot, baseline, _SWEEP_CONFIG)

    return BotMetricsResponse(
        has_baseline=True,
        sharpe_rolling=chips.sharpe_rolling,
        pf_rolling=semaphore_metrics.pf_rolling,
        exp_rolling=semaphore_metrics.exp_rolling,
        win_rate_rolling=chips.win_rate_rolling,
        payoff_rolling=chips.payoff,
        avg_trade_duration_rolling_min=chips.avg_trade_duration_min,
        loss_streak=semaphore_metrics.loss_streak,
        dd_rolling_pct=semaphore_metrics.dd_bot_pct,
        sharpe_baseline=baseline.sharpe,
        pf_baseline=semaphore_metrics.pf_baseline,
        exp_baseline=semaphore_metrics.exp_baseline,
        win_rate_baseline=baseline.win_rate,
        payoff_baseline=baseline.payoff,
        avg_trade_duration_baseline_min=baseline.avg_trade_duration_min,
        dd_contract_pct=semaphore_metrics.dd_contract_pct,
        sortino=curve_metrics.sortino,
        calmar=curve_metrics.calmar,
        max_dd_pct=curve_metrics.max_dd_pct,
        ulcer_index=curve_metrics.ulcer_index,
        recovery_factor=curve_metrics.recovery_factor,
        net_pnl=curve_metrics.net_pnl,
        trades_per_month=trades_per_month,
        pct_of_total_pnl=contribution.pct_of_total_pnl,
        correlation_vs_rest=contribution.correlation_vs_rest,
        pnl_bot=contribution.pnl_bot,
        pnl_account=contribution.pnl_account,
    )


@router.get("/{bot_id}/semaphore-history", response_model=list[SemaphoreHistoryRow])
async def semaphore_history(
    bot_id: int, session: AsyncSession = Depends(get_session)
) -> list[SemaphoreTransition]:
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    return list(
        (
            await session.execute(
                select(SemaphoreTransition)
                .where(SemaphoreTransition.bot_id == bot_id)
                .order_by(SemaphoreTransition.ts.desc())
            )
        )
        .scalars()
        .all()
    )
