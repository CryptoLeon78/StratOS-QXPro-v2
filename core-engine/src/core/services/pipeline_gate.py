"""PARTE 6.3: ensambla `PipelineGateMetrics` con los trades reales del bot
del candidato y llama a `evaluate_pipeline_gate`/`apply_pipeline_gate`
(state_machines/pipeline.py, G3, ya existen).

Huecos reales de esquema, documentados (no corregidos aqui):
- `Trade.r_multiple` nunca se calcula en ingest (G4) -- necesitaria
  tick_value/tick_size por simbolo, que el esquema no guarda. Sin
  r_multiples reales, `expectancy_r` cae a 0.0 (falla el gate >0.15 de
  forma segura, fail-closed) en vez de inventar un numero.
- No hay curva de equity POR BOT (`EquitySnapshot` es por cuenta) -- se
  reconstruye una curva acumulada desde un capital base 100 + P&L de cada
  trade en orden (mismo criterio que `monte_carlo_maxdd`, G2, para la
  curva bootstrap). El "Sharpe de trades" (media/desviacion de P&L por
  trade, sin curva de equity real) reutiliza `formulas/trading.py::
  rolling_sharpe` (G10) con `window=len(...)` (todo el historial OOS del
  candidato, no una ventana rodante corta como en Salud/Bots)."""

from datetime import datetime, timedelta
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.market import Trade
from core.db.models.pipeline import PipelineCandidate
from core.formulas.pipeline import trades_per_week as trades_per_week_formula
from core.formulas.trading import expectancy_r as expectancy_r_formula
from core.formulas.trading import max_drawdown_pct, rolling_sharpe
from core.formulas.trading import rolling_profit_factor as rolling_profit_factor_formula
from core.state_machines.pipeline import apply_pipeline_gate, evaluate_pipeline_gate
from core.state_machines.types import GateResult, PipelineGateConfig, PipelineGateMetrics

_BASE_EQUITY = Decimal("100")


async def assemble_metrics(
    session: AsyncSession, candidate: PipelineCandidate, now: datetime
) -> PipelineGateMetrics:
    rows = (
        await session.execute(
            select(Trade.profit, Trade.commission, Trade.swap, Trade.close_time, Trade.r_multiple)
            .where(Trade.bot_id == candidate.bot_id, Trade.close_time.is_not(None))
            .order_by(Trade.close_time.asc())
        )
    ).all()

    net_profits = [profit + commission + swap for profit, commission, swap, _, _ in rows]
    close_times = [close_time for _, _, _, close_time, _ in rows]
    r_multiples = [r for _, _, _, _, r in rows if r is not None]

    profit_factor = rolling_profit_factor_formula(net_profits, window=len(net_profits)) or 0.0
    expectancy = expectancy_r_formula(r_multiples) if r_multiples else 0.0
    sharpe = rolling_sharpe(net_profits, window=len(net_profits))

    equity_curve = [_BASE_EQUITY]
    for pnl in net_profits:
        equity_curve.append(equity_curve[-1] + pnl)
    max_dd = float(max_drawdown_pct(equity_curve)) if len(equity_curve) > 1 else 0.0

    window_days = 30
    recent_close_times = [ct for ct in close_times if ct >= now - timedelta(days=window_days)]
    freq = trades_per_week_formula(recent_close_times, window_days=window_days)
    observed_close_times = [
        close_time for close_time in close_times if close_time >= candidate.entered_phase_at
    ]
    incubation_days = (now - observed_close_times[0]).days if observed_close_times else 0

    return PipelineGateMetrics(
        profit_factor=profit_factor,
        expectancy_r=expectancy,
        sharpe=sharpe,
        max_dd_pct=max_dd,
        oos_trades=len(rows),
        incubation_days=incubation_days,
        trades_per_week=freq,
    )


async def evaluate_and_persist(
    session: AsyncSession,
    redis: Redis,
    candidate: PipelineCandidate,
    config: PipelineGateConfig,
    now: datetime,
    sizing_cap_breach: bool = False,
) -> GateResult:
    metrics = await assemble_metrics(session, candidate, now)
    # apply_pipeline_gate (G3) solo escribe gates_passed/verdict/provisional/
    # evaluated_at -- los campos de metrica "en crudo" (para los paneles de
    # UI de 7.3/7.4) se rellenan aqui, antes de persistir el veredicto.
    candidate.profit_factor = metrics.profit_factor
    candidate.expectancy_r = metrics.expectancy_r
    candidate.sharpe = metrics.sharpe
    candidate.max_dd_pct = Decimal(str(round(metrics.max_dd_pct, 4)))
    candidate.oos_trades = metrics.oos_trades
    candidate.trades_per_week = metrics.trades_per_week
    candidate.incubation_days = metrics.incubation_days

    result = evaluate_pipeline_gate(metrics, config, sizing_cap_breach=sizing_cap_breach)
    await apply_pipeline_gate(session, redis, candidate, result)
    return result
