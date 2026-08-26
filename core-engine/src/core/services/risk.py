"""PARTE 7.7: Tail Risk (VaR/CVaR) y exposicion en vivo. Envuelve
`historical_var`/`historical_cvar` (formulas/portfolio.py, G2) con la curva
de equity real de las cuentas REALES (nunca DEMO, P6.2). Escalado mensual/
anual por raiz del tiempo (convencion estandar de VaR bajo retornos i.i.d.,
no es una formula de PARTE 8 -- ASSUMPTIONS G5)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import TradeType
from core.db.models.accounts import Account
from core.db.models.market import EquitySnapshot, Trade
from core.formulas.portfolio import daily_returns, historical_cvar, historical_var

_TRADING_DAYS_PER_MONTH = 21.0
_TRADING_DAYS_PER_YEAR = 252.0


@dataclass(frozen=True)
class RiskServiceConfig:
    window_days: int = 60
    var95_level: float = 0.95
    var99_level: float = 0.99
    cvar95_level: float = 0.95
    cvar99_level: float = 0.99
    cvar99_daily_gate_pct: float = 3.0
    cvar99_monthly_gate_pct: float = 15.0
    verdict_ok: str = "Colas dentro de los gates (CVaR99 diario < 3 % y mensual < 15 %). Mantener."
    verdict_breach: str = (
        "Incumplimiento de contrato de cola — revisar exposición y reducir sizing."
    )


@dataclass(frozen=True)
class TailRiskResult:
    var95_daily: float
    var99_daily: float
    cvar95_daily: float
    cvar99_daily: float
    var99_monthly: float
    cvar99_monthly: float
    cvar99_annual: float
    breached: bool
    verdict: str


@dataclass(frozen=True)
class ExposureRow:
    symbol: str
    net_volume: Decimal
    gross_volume: Decimal
    pnl: Decimal


async def real_portfolio_equity_curve(session: AsyncSession, window_start: datetime) -> pd.Series:
    rows = (
        await session.execute(
            select(EquitySnapshot.account_id, EquitySnapshot.ts, EquitySnapshot.equity)
            .join(Account, Account.id == EquitySnapshot.account_id)
            .where(Account.is_demo.is_(False), EquitySnapshot.ts >= window_start)
            .order_by(EquitySnapshot.account_id, EquitySnapshot.ts)
        )
    ).all()
    if not rows:
        return pd.Series(dtype=float)

    frame = pd.DataFrame(rows, columns=["account_id", "ts", "equity"])
    frame["date"] = frame["ts"].apply(lambda ts: pd.Timestamp(ts.date()))
    frame["equity"] = frame["equity"].astype(float)
    # ultimo snapshot de cada dia por cuenta, luego forward-fill por si una
    # cuenta no reporto ese dia (mismo criterio que correlation_matrix, G2).
    daily_by_account = frame.groupby(["account_id", "date"])["equity"].last().unstack("account_id")
    return daily_by_account.ffill().sum(axis=1)


async def compute_tail_risk(
    session: AsyncSession, config: RiskServiceConfig, now: datetime
) -> TailRiskResult | None:
    window_start = now - timedelta(days=config.window_days)
    equity_curve = await real_portfolio_equity_curve(session, window_start)
    if len(equity_curve) < 2:
        return None

    returns = daily_returns(equity_curve)
    if returns.empty:
        return None

    var95 = historical_var(returns, level=config.var95_level) * 100
    var99 = historical_var(returns, level=config.var99_level) * 100
    cvar95 = historical_cvar(returns, level=config.cvar95_level) * 100
    cvar99 = historical_cvar(returns, level=config.cvar99_level) * 100

    var99_monthly = var99 * (_TRADING_DAYS_PER_MONTH**0.5)
    cvar99_monthly = cvar99 * (_TRADING_DAYS_PER_MONTH**0.5)
    cvar99_annual = cvar99 * (_TRADING_DAYS_PER_YEAR**0.5)

    breached = (
        cvar99 >= config.cvar99_daily_gate_pct or cvar99_monthly >= config.cvar99_monthly_gate_pct
    )
    verdict = config.verdict_breach if breached else config.verdict_ok

    return TailRiskResult(
        var95_daily=var95,
        var99_daily=var99,
        cvar95_daily=cvar95,
        cvar99_daily=cvar99,
        var99_monthly=var99_monthly,
        cvar99_monthly=cvar99_monthly,
        cvar99_annual=cvar99_annual,
        breached=breached,
        verdict=verdict,
    )


async def compute_exposure(session: AsyncSession) -> list[ExposureRow]:
    """7.7: tabla Simbolo/Net/Gross/P&L de posiciones abiertas. Solo por
    simbolo en su unidad nativa -- sin conversion de divisa (ASSUMPTIONS
    G5-Q5: `Trade` no guarda la divisa del simbolo, no hay tabla de mapeo)."""
    rows = (
        await session.execute(
            select(Trade.symbol, Trade.type, Trade.volume, Trade.profit).where(
                Trade.close_time.is_(None)
            )
        )
    ).all()

    aggregated: dict[str, list[Decimal]] = {}
    for symbol, trade_type, volume, profit in rows:
        net, gross, pnl = aggregated.setdefault(symbol, [Decimal("0"), Decimal("0"), Decimal("0")])
        signed = volume if trade_type == TradeType.BUY else -volume
        aggregated[symbol] = [net + signed, gross + volume, pnl + profit]

    return [
        ExposureRow(symbol=symbol, net_volume=net, gross_volume=gross, pnl=pnl)
        for symbol, (net, gross, pnl) in aggregated.items()
    ]
