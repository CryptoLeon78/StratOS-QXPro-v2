"""PARTE 6.1: barrido periodico que ensambla `SemaphoreMetrics` con datos
reales (Trade/Baseline) y llama a `evaluate_semaphore_transition`/
`apply_semaphore_transition` (state_machines/semaphore.py, G3, ya
existen). Orquesta con datos reales el mismo caso demo de PARTE 1/12
(Poseidon Trend GER40, PF rodante 1,18 vs baseline 1,94 -> AMARILLO).

Huecos reales de esquema heredados de pipeline_gate.py (mismo problema,
misma solucion documentada ahi): `Trade.r_multiple` casi nunca esta
poblado (ingest no lo calcula, G4) -- `exp_rolling`/`loss_streak`/
`page_hinkley_triggered` caen a valores conservadores (0/0/False) cuando
faltan R-multiples, en vez de inventar datos. `loss_streak_p99_baseline`
se lee directo de `Baseline.max_consec_losses` (ya persistido en G1, no se
recalcula el bootstrap de `streak_p99_threshold` sin la serie cruda de
R-multiples del baseline, que tampoco se guarda)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import PipelinePhase
from core.db.models.accounts import Baseline, Bot
from core.db.models.market import Trade
from core.formulas.monitoring import page_hinkley
from core.formulas.trading import (
    avg_trade_duration,
    expectancy_r,
    loss_streak,
    payoff_ratio,
    rolling_profit_factor,
    rolling_sharpe,
    win_rate_drift,
)
from core.state_machines.semaphore import apply_semaphore_transition, evaluate_semaphore_transition
from core.state_machines.types import SemaphoreConfig, SemaphoreMetrics

_BASE_EQUITY = Decimal("100")


@dataclass(frozen=True)
class SemaphoreSweepConfig:
    rolling_window_trades: int = 20
    ph_delta: float = 0.005
    ph_lambda: float = 50.0


async def assemble_semaphore_metrics(
    session: AsyncSession, bot: Bot, baseline: Baseline, sweep_config: SemaphoreSweepConfig
) -> SemaphoreMetrics:
    rows = (
        await session.execute(
            select(Trade.profit, Trade.commission, Trade.swap, Trade.r_multiple)
            .where(Trade.bot_id == bot.id, Trade.close_time.is_not(None))
            .order_by(Trade.close_time.asc())
        )
    ).all()
    profits = [profit + commission + swap for profit, commission, swap, _ in rows]
    r_multiples = [r for *_, r in rows if r is not None]

    pf_rolling = rolling_profit_factor(profits, window=sweep_config.rolling_window_trades) or 0.0
    recent_r = r_multiples[-sweep_config.rolling_window_trades :]
    exp_rolling = expectancy_r(recent_r) if recent_r else 0.0
    streak = loss_streak(r_multiples) if r_multiples else 0
    ph_triggered = False
    if len(r_multiples) >= 2:
        ph_result = page_hinkley(
            [float(r) for r in r_multiples], sweep_config.ph_delta, sweep_config.ph_lambda
        )
        ph_triggered = ph_result.change_detected

    equity_curve = [_BASE_EQUITY]
    for pnl in profits:
        equity_curve.append(equity_curve[-1] + pnl)
    peak = max(equity_curve)
    current = equity_curve[-1]
    dd_bot_pct = (peak - current) / peak * 100 if peak > 0 else Decimal("0")

    return SemaphoreMetrics(
        pf_rolling=pf_rolling,
        pf_baseline=baseline.profit_factor,
        exp_rolling=exp_rolling,
        exp_baseline=baseline.expectancy_r,
        loss_streak=streak,
        loss_streak_p99_baseline=baseline.max_consec_losses,
        page_hinkley_triggered=ph_triggered,
        dd_bot_pct=dd_bot_pct,
        dd_contract_pct=baseline.dd_contract_pct,
    )


@dataclass(frozen=True)
class HealthChips:
    """G10 (docs/backlog.md): chips rodantes de la pestaña Salud que no
    forman parte de `SemaphoreMetrics` (no las consume la maquina de
    estado, solo la vista) -- Win Rate drift, Payoff, Duracion media,
    Sharpe rolling. `win_rate_rolling` = `baseline.win_rate + win_rate_drift`
    (identico algebraicamente a recalcularlo desde cero, reutiliza el
    mismo dato ya calculado) -- para la fila "Win Rate" de la tabla
    Rolling vs Baseline de Bots (7.4), que necesita el valor bruto, no
    solo el delta."""

    win_rate_drift: float
    win_rate_rolling: float
    payoff: float | None
    avg_trade_duration_min: float | None
    sharpe_rolling: float


async def assemble_health_chips(
    session: AsyncSession, bot: Bot, baseline: Baseline, sweep_config: SemaphoreSweepConfig
) -> HealthChips:
    rows = (
        await session.execute(
            select(Trade.profit, Trade.commission, Trade.swap, Trade.open_time, Trade.close_time)
            .where(Trade.bot_id == bot.id, Trade.close_time.is_not(None))
            .order_by(Trade.close_time.asc())
        )
    ).all()
    profits = [profit + commission + swap for profit, commission, swap, _, _ in rows]
    durations = [
        close_time - open_time for _, _, _, open_time, close_time in rows if close_time is not None
    ]

    window = sweep_config.rolling_window_trades
    recent_profits = profits[-window:]
    recent_durations = durations[-window:]

    drift = (
        win_rate_drift(profits, baseline_win_rate=baseline.win_rate, window=window)
        if profits
        else 0.0
    )
    payoff = payoff_ratio(recent_profits) if recent_profits else None
    avg_duration = (
        avg_trade_duration(recent_durations).total_seconds() / 60 if recent_durations else None
    )
    sharpe = rolling_sharpe(profits, window=window)

    return HealthChips(
        win_rate_drift=drift,
        win_rate_rolling=baseline.win_rate + drift,
        payoff=payoff,
        avg_trade_duration_min=avg_duration,
        sharpe_rolling=sharpe,
    )


async def sweep_all_bots(
    session: AsyncSession,
    redis: Redis,
    config: SemaphoreConfig,
    sweep_config: SemaphoreSweepConfig,
    now: datetime,
) -> None:
    bots = (
        (
            await session.execute(
                select(Bot).where(
                    Bot.baseline_id.is_not(None), Bot.pipeline_phase != PipelinePhase.CEMENTERIO
                )
            )
        )
        .scalars()
        .all()
    )
    for bot in bots:
        baseline = await session.get(Baseline, bot.baseline_id)
        if baseline is None:
            continue

        metrics = await assemble_semaphore_metrics(session, bot, baseline, sweep_config)
        days_in_state = (now - bot.entered_state_at).days

        # Aproximacion (ASSUMPTIONS G5): no hay historico de evaluaciones
        # diarias para contar dias CONSECUTIVOS cumpliendo la condicion de
        # recuperacion -- se usa days_in_state si la condicion se cumple
        # HOY, en vez de rastrear la racha real dia a dia.
        recovers_today = (
            metrics.pf_rolling >= config.pf_recover * metrics.pf_baseline
            and metrics.exp_rolling >= config.exp_recover * metrics.exp_baseline
        )
        days_meeting_recovery = days_in_state if recovers_today else 0

        result = evaluate_semaphore_transition(
            bot.semaphore_state,
            metrics,
            config,
            magic_number=bot.magic_number,
            days_in_amarillo=days_in_state,
            days_meeting_recovery_condition=days_meeting_recovery,
        )
        await apply_semaphore_transition(session, redis, bot, result)
