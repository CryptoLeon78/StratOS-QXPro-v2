"""TCA sobre fills v1.1; sin fills el resultado es ``None``, nunca cero."""

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import TradeType
from core.db.models.accounts import Account
from core.db.models.market import ExecutionFill

# ASSUMPTION G11-05: percentiles estándar de ejecución; son constantes
# descriptivas, no umbrales de trading ni política de riesgo.
_PERCENTILE_MEDIAN = 50
_PERCENTILE_TAIL = 95
_PERCENTILE_EXTREME = 99
_FILLED_STATUS = "FILLED"
_REJECTED_STATUS = "REJECTED"


@dataclass(frozen=True)
class TcaSummary:
    fills: int
    slippage_p50: Decimal | None
    slippage_p95: Decimal | None
    slippage_p99: Decimal | None
    asymmetry_index: float | None
    implementation_shortfall_p50: Decimal | None
    rejected_orders: int
    broker_profiles: tuple["BrokerProfile", ...]


@dataclass(frozen=True)
class BrokerProfile:
    broker: str
    symbol: str
    fills: int
    spread_p50: Decimal | None


def signed_slippage(fill: ExecutionFill) -> Decimal:
    """Positivo = ejecución adversa; BUY paga más, SELL vende más barato."""
    if fill.executed_price is None:
        raise ValueError("un fill TCA requiere precio ejecutado")
    return (
        fill.executed_price - fill.requested_price
        if fill.type == TradeType.BUY
        else fill.requested_price - fill.executed_price
    )


async def tca_summary(session: AsyncSession, account_id: int | None = None) -> TcaSummary | None:
    fills_query = select(ExecutionFill)
    if account_id is not None:
        fills_query = fills_query.where(ExecutionFill.account_id == account_id)
    reports = list((await session.execute(fills_query)).scalars().all())
    if not reports:
        return None
    fills = [report for report in reports if report.status == _FILLED_STATUS]
    rejected_orders = sum(report.status == _REJECTED_STATUS for report in reports)
    account_brokers: dict[int, str] = {
        account_id: broker
        for account_id, broker in (await session.execute(select(Account.id, Account.broker))).all()
    }
    profiles: list[BrokerProfile] = []
    reports_by_broker_symbol: dict[tuple[str, str], list[ExecutionFill]] = {}
    for report in reports:
        key = (account_brokers[report.account_id], report.symbol)
        reports_by_broker_symbol.setdefault(key, []).append(report)
    for (broker, symbol), group in sorted(reports_by_broker_symbol.items()):
        spreads = [float(report.spread) for report in group if report.spread is not None]
        profiles.append(
            BrokerProfile(
                broker=broker,
                symbol=symbol,
                fills=sum(report.status == _FILLED_STATUS for report in group),
                spread_p50=(
                    Decimal(str(np.percentile(spreads, _PERCENTILE_MEDIAN))) if spreads else None
                ),
            )
        )
    if not fills:
        return TcaSummary(0, None, None, None, None, None, rejected_orders, tuple(profiles))
    slippages = [signed_slippage(fill) for fill in fills]
    values = np.array([float(value) for value in slippages])
    shortfalls = [
        slip + (fill.spread / Decimal("2"))
        for fill, slip in zip(fills, slippages, strict=True)
        if fill.spread is not None
    ]
    adverse = int((values > 0).sum())
    favourable = int((values < 0).sum())
    denominator = adverse + favourable
    return TcaSummary(
        fills=len(fills),
        slippage_p50=Decimal(str(np.percentile(values, _PERCENTILE_MEDIAN))),
        slippage_p95=Decimal(str(np.percentile(values, _PERCENTILE_TAIL))),
        slippage_p99=Decimal(str(np.percentile(values, _PERCENTILE_EXTREME))),
        asymmetry_index=(adverse - favourable) / denominator if denominator else 0.0,
        implementation_shortfall_p50=(
            Decimal(str(np.percentile([float(value) for value in shortfalls], _PERCENTILE_MEDIAN)))
            if shortfalls
            else None
        ),
        rejected_orders=rejected_orders,
        broker_profiles=tuple(profiles),
    )
