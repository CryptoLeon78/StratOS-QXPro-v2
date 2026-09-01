"""PARTE 7.7: drawdown esperado (Monte Carlo) y contrato de drawdown por
bot. Envuelve `monte_carlo_maxdd()` (formulas/portfolio.py, G2) con el
historial real de trades cerrados. Recalculo mensual + cada 50 trades
(contractual, 7.7) -- sin hook sincrono en ingest/ (cerrado desde G4), se
aproxima con un barrido diario que compara contra el ultimo run."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Bot
from core.db.models.governance import MonteCarloRun
from core.db.models.market import Trade
from core.formulas.portfolio import monte_carlo_maxdd

_RECALC_MONTH_DAYS = 30


@dataclass(frozen=True)
class MonteCarloServiceConfig:
    n_sims: int = 300
    seed: int = 42
    initial_equity: Decimal = Decimal("100")
    recalc_every_trades: int = 50


async def bots_due_for_recalc(
    session: AsyncSession, config: MonteCarloServiceConfig, now: datetime
) -> list[Bot]:
    bots = (await session.execute(select(Bot))).scalars().all()
    due: list[Bot] = []
    for bot in bots:
        last_run = (
            await session.execute(
                select(MonteCarloRun)
                .where(MonteCarloRun.bot_id == bot.id)
                .order_by(MonteCarloRun.ts.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if last_run is None:
            due.append(bot)
            continue
        if now - last_run.ts >= timedelta(days=_RECALC_MONTH_DAYS):
            due.append(bot)
            continue
        trades_since = (
            await session.execute(
                select(func.count(Trade.id)).where(
                    Trade.bot_id == bot.id,
                    Trade.close_time.is_not(None),
                    Trade.close_time > last_run.ts,
                )
            )
        ).scalar() or 0
        if trades_since >= config.recalc_every_trades:
            due.append(bot)
    return due


async def _closed_trade_pnls(session: AsyncSession, bot_id: int) -> list[Decimal]:
    rows = (
        await session.execute(
            select(Trade.profit, Trade.commission, Trade.swap).where(
                Trade.bot_id == bot_id, Trade.close_time.is_not(None)
            )
        )
    ).all()
    return [profit + commission + swap for profit, commission, swap in rows]


async def run_montecarlo_for_bot(
    session: AsyncSession, bot: Bot, config: MonteCarloServiceConfig, now: datetime
) -> MonteCarloRun | None:
    trade_pnls = await _closed_trade_pnls(session, bot.id)
    if not trade_pnls:
        return None

    result = monte_carlo_maxdd(
        trade_pnls,
        n_sims=config.n_sims,
        seed=config.seed,
        initial_equity=config.initial_equity,
    )
    # 7.7: el contrato firmado es el DD P95 en el momento del calculo
    # (ejemplo literal Atlas Trend: P95 3,9% == "acepta hasta -3,9%").
    run = MonteCarloRun(
        bot_id=bot.id,
        ts=now,
        n_simulations=result.n_simulations,
        dd_p50=result.p50,
        dd_p75=result.p75,
        dd_p95=result.p95,
        dd_contract_pct=result.p95,
        seed=result.seed,
    )
    session.add(run)
    await session.flush()
    return run
