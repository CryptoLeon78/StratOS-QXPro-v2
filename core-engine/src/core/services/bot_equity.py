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

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.market import Trade

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


async def bot_open_positions(session: AsyncSession, bot_id: int) -> list[Trade]:
    """Posiciones abiertas (`close_time IS NULL`) de un bot -- cierra el
    gap "Posiciones abiertas por bot (sin endpoint)" de docs/backlog.md."""
    rows = await session.execute(
        select(Trade).where(Trade.bot_id == bot_id, Trade.close_time.is_(None))
    )
    return list(rows.scalars().all())
