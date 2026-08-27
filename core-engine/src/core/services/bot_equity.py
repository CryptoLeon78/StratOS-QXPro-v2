"""G10 (docs/backlog.md): curva de P&L acumulado sintetica por bot y sus
posiciones abiertas -- sin necesidad de nueva ingesta, ambas se derivan de
`Trade` (ya existe desde G1). Base para las formulas ratio-based de (b)
(Sortino/Calmar/Ulcer/RecoveryFactor por bot) y para el panel "Metricas
completas"/"P&L acumulado" de Bots (7.4).

CAVEAT (ya anotado en docs/backlog.md, no repetirlo silenciosamente en
otro lugar): `bot_pnl_curve` es SUM(Trade.profit) acumulado ordenado por
close_time, NO es equity de cuenta real a nivel de bot -- los brokers
reportan equity solo a nivel de CUENTA (`EquitySnapshot.account_id`),
nunca por bot individual. Sirve como proxy razonable para las formulas
ratio-based de `formulas/trading.py`/`formulas/portfolio.py` (todas
insensibles a la base absoluta salvo Calmar/RecoveryFactor, que necesitan
un `initial_equity` no-cero -- mismo motivo por el que `monte_carlo_maxdd`
(G2) ya usa una base nominal de 100, ver ASSUMPTIONS G2)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Bot
from core.db.models.governance import CorrelationMatrix
from core.db.models.market import Trade
from core.formulas.portfolio import sortino_ratio
from core.formulas.trading import calmar_ratio, max_drawdown_pct, recovery_factor, ulcer_index

_NOMINAL_INITIAL_EQUITY = Decimal("100")  # mismo criterio que monte_carlo_maxdd (G2)


async def bot_pnl_curve(
    session: AsyncSession, bot_id: int, initial_equity: Decimal = _NOMINAL_INITIAL_EQUITY
) -> list[Decimal]:
    """Curva de P&L acumulado de un bot: `initial_equity` seguido de un
    punto por cada trade CERRADO (`close_time IS NOT NULL`), en orden
    cronologico de cierre. Sin trades cerrados -> `[initial_equity]`."""
    profits = (
        await session.execute(
            select(Trade.profit)
            .where(Trade.bot_id == bot_id, Trade.close_time.isnot(None))
            .order_by(Trade.close_time)
        )
    ).scalars()

    curve = [initial_equity]
    equity = initial_equity
    for profit in profits:
        equity = equity + profit
        curve.append(equity)
    return curve


async def bot_pnl_curve_with_dates(
    session: AsyncSession, bot_id: int, initial_equity: Decimal = _NOMINAL_INITIAL_EQUITY
) -> list[tuple[datetime | None, Decimal]]:
    """Igual que `bot_pnl_curve()` pero pareado con `close_time` -- para
    el chart "P&L acumulado del bot" (7.4), que necesita eje X real. El
    primer punto (arranque sintetico) lleva `ts=None` -- no hay una fecha
    real que representarlo."""
    rows = (
        await session.execute(
            select(Trade.close_time, Trade.profit)
            .where(Trade.bot_id == bot_id, Trade.close_time.isnot(None))
            .order_by(Trade.close_time)
        )
    ).all()

    points: list[tuple[datetime | None, Decimal]] = [(None, initial_equity)]
    equity = initial_equity
    for close_time, profit in rows:
        equity = equity + profit
        points.append((close_time, equity))
    return points


async def bot_r_multiples(session: AsyncSession, bot_id: int) -> list[Decimal]:
    """R-multiples reales de trades cerrados de un bot (`Trade.r_multiple`,
    poblado desde G10-05) -- para "Histograma de retornos (R)" (7.4).
    Trades sin `r_multiple` (sin `sl`, o simbolo sin `instrument_spec`) se
    excluyen, no se inventan."""
    rows = await session.execute(
        select(Trade.r_multiple).where(
            Trade.bot_id == bot_id, Trade.close_time.isnot(None), Trade.r_multiple.isnot(None)
        )
    )
    return [r for r in rows.scalars().all() if r is not None]


@dataclass(frozen=True)
class BotCurveMetrics:
    """G10: metricas derivadas de `bot_pnl_curve()` (base nominal, ver
    docstring del modulo) -- panel "Metricas completas" de Bots (7.4).
    `net_pnl` SI es P&L real (la base nominal se cancela en una resta);
    `max_dd_pct`/`ulcer_index` son porcentuales sobre la base nominal, no
    comparables a un DD real de cuenta -- mismo caveat que el resto de
    este modulo. `sortino`/`calmar`/`recovery_factor` pueden no ser
    calculables (curva demasiado corta, sin drawdown, sin retornos por
    debajo del target) -- `None`, nunca un numero inventado."""

    net_pnl: Decimal
    max_dd_pct: float
    ulcer_index: float
    calmar: float | None
    recovery_factor: float | None
    sortino: float | None


def compute_curve_metrics(curve: list[Decimal]) -> BotCurveMetrics:
    if len(curve) < 2:
        return BotCurveMetrics(
            net_pnl=Decimal("0"),
            max_dd_pct=0.0,
            ulcer_index=0.0,
            calmar=None,
            recovery_factor=None,
            sortino=None,
        )

    net_pnl = curve[-1] - curve[0]
    max_dd_pct = float(max_drawdown_pct(curve))
    ulcer = ulcer_index(curve)

    try:
        calmar = calmar_ratio(curve)
    except ValueError:
        calmar = None

    try:
        recovery = recovery_factor(curve)
    except ValueError:
        recovery = None

    returns = pd.Series([float(c) for c in curve]).pct_change().dropna()
    try:
        sortino = sortino_ratio(returns) if not returns.empty else None
    except ValueError:
        sortino = None

    return BotCurveMetrics(
        net_pnl=net_pnl,
        max_dd_pct=max_dd_pct,
        ulcer_index=ulcer,
        calmar=calmar,
        recovery_factor=recovery,
        sortino=sortino,
    )


async def bot_open_positions(session: AsyncSession, bot_id: int) -> list[Trade]:
    """Posiciones abiertas (`close_time IS NULL`) de un bot -- cierra el
    gap "Posiciones abiertas por bot (sin endpoint)" de docs/backlog.md."""
    rows = await session.execute(
        select(Trade).where(Trade.bot_id == bot_id, Trade.close_time.is_(None))
    )
    return list(rows.scalars().all())


@dataclass(frozen=True)
class PortfolioContribution:
    """G10: "Contribucion al portfolio" (Bots, 7.4). `pnl_bot`/`pnl_account`
    son P&L real (SUM(Trade.profit), misma convencion que `bot_pnl_curve`).
    `pct_of_total_pnl`/`correlation_vs_rest` quedan en `None` cuando no
    hay base para calcularlos (sin trades cerrados en ningun bot, o sin
    `CorrelationMatrix` sembrada para este bot) -- no se inventan."""

    pct_of_total_pnl: float | None
    correlation_vs_rest: float | None
    pnl_bot: Decimal
    pnl_account: Decimal


async def compute_portfolio_contribution(session: AsyncSession, bot: Bot) -> PortfolioContribution:
    closed_pnl = func.coalesce(func.sum(Trade.profit), 0)
    pnl_bot = Decimal(
        (
            await session.execute(
                select(closed_pnl).where(Trade.bot_id == bot.id, Trade.close_time.is_not(None))
            )
        ).scalar_one()
    )
    pnl_account = Decimal(
        (
            await session.execute(
                select(closed_pnl).where(
                    Trade.account_id == bot.account_id, Trade.close_time.is_not(None)
                )
            )
        ).scalar_one()
    )
    total_pnl_result = await session.execute(
        select(closed_pnl).where(Trade.close_time.is_not(None))
    )
    total_pnl = Decimal(total_pnl_result.scalar_one())
    pct_of_total = float(pnl_bot / total_pnl * 100) if total_pnl != 0 else None

    latest_ts = (
        await session.execute(
            select(func.max(CorrelationMatrix.ts)).where(
                (CorrelationMatrix.bot_a_id == bot.id) | (CorrelationMatrix.bot_b_id == bot.id)
            )
        )
    ).scalar_one_or_none()

    correlation_vs_rest = None
    if latest_ts is not None:
        correlations = (
            (
                await session.execute(
                    select(CorrelationMatrix.correlation).where(
                        CorrelationMatrix.ts == latest_ts,
                        (CorrelationMatrix.bot_a_id == bot.id)
                        | (CorrelationMatrix.bot_b_id == bot.id),
                    )
                )
            )
            .scalars()
            .all()
        )
        if correlations:
            correlation_vs_rest = sum(correlations) / len(correlations)

    return PortfolioContribution(
        pct_of_total_pnl=pct_of_total,
        correlation_vs_rest=correlation_vs_rest,
        pnl_bot=pnl_bot,
        pnl_account=pnl_account,
    )
