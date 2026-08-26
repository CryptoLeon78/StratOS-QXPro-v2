"""PARTE 7.11 (modulo transversal "Diario de impulsos") + PARTE 8:
monitorizacion contrafactual a 7 dias de una intervencion deseada. Envuelve
`counterfactual_impulse()` (formulas/audit.py, G2) con el historial real de
trades del bot tras el impulso.

Hueco real de esquema (documentar, no corregir aqui): `ImpulseLog` no
guarda el `sizing_multiplier` vigente EN EL MOMENTO del impulso (solo lo
necesitan INCREASE_RISK/DECREASE_RISK). Sin ese campo, la simulacion usa el
`Bot.sizing_multiplier` observado en el momento de la EVALUACION (7 dias
despues) como aproximacion -- inexacto si el sizing cambio entre medias.
PAUSE_BOT/CLOSE_POSITION (simulado=0) no se ven afectados por este hueco."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ImpulseAction, ImpulseStatus
from core.db.models.accounts import Bot
from core.db.models.decisions import ImpulseLog
from core.db.models.market import Trade
from core.formulas.audit import counterfactual_impulse
from core.formulas.types import ImpulseSnapshot, TradeLike


@dataclass(frozen=True)
class ImpulseServiceConfig:
    eval_days: int = 7


@dataclass(frozen=True)
class ImpulseReport:
    quarter: str
    count: int
    total_avoided_cost_eur: Decimal


async def create_impulse(
    session: AsyncSession,
    bot_id: int,
    description: str,
    desired_action: ImpulseAction,
    now: datetime,
) -> ImpulseLog:
    impulse = ImpulseLog(
        ts=now,
        bot_id=bot_id,
        description=description,
        desired_action=desired_action,
        executed=False,
        status=ImpulseStatus.PENDING,
    )
    session.add(impulse)
    await session.flush()
    return impulse


async def evaluate_pending_impulses(
    session: AsyncSession, config: ImpulseServiceConfig, now: datetime
) -> None:
    due = (
        (
            await session.execute(
                select(ImpulseLog).where(ImpulseLog.status == ImpulseStatus.PENDING)
            )
        )
        .scalars()
        .all()
    )
    for impulse in due:
        eval_at = impulse.ts + timedelta(days=config.eval_days)
        if eval_at > now:
            continue

        bot = await session.get(Bot, impulse.bot_id)
        trade_rows = (
            await session.execute(
                select(Trade.profit, Trade.commission, Trade.swap).where(
                    Trade.bot_id == impulse.bot_id,
                    Trade.close_time.is_not(None),
                    Trade.close_time > impulse.ts,
                    Trade.close_time <= eval_at,
                )
            )
        ).all()
        trades_after = [
            TradeLike(profit=profit, commission=commission, swap=swap)
            for profit, commission, swap in trade_rows
        ]
        real_result = sum(
            (t.profit + t.commission + t.swap for t in trades_after), start=Decimal("0")
        )
        snapshot = ImpulseSnapshot(
            sizing_multiplier=bot.sizing_multiplier if bot is not None else Decimal("1.0")
        )
        avoided_cost = counterfactual_impulse(trades_after, impulse.desired_action, snapshot)

        impulse.counterfactual_result_7d_eur = real_result
        impulse.avoided_cost_eur = avoided_cost
        impulse.status = ImpulseStatus.CLOSED
        impulse.evaluated_at = now
    await session.flush()


def _quarter_range(quarter: str) -> tuple[datetime, datetime]:
    year_str, q_str = quarter.split("-Q")
    year, q = int(year_str), int(q_str)
    start_month = (q - 1) * 3 + 1
    start = datetime(year, start_month, 1, tzinfo=UTC)
    end_month = start_month + 3
    end = (
        datetime(year + 1, 1, 1, tzinfo=UTC)
        if end_month > 12
        else datetime(year, end_month, 1, tzinfo=UTC)
    )
    return start, end


async def quarterly_report(session: AsyncSession, quarter: str) -> ImpulseReport:
    start, end = _quarter_range(quarter)
    rows = (
        (
            await session.execute(
                select(ImpulseLog.avoided_cost_eur).where(
                    ImpulseLog.status == ImpulseStatus.CLOSED,
                    ImpulseLog.ts >= start,
                    ImpulseLog.ts < end,
                )
            )
        )
        .scalars()
        .all()
    )
    total = sum((cost for cost in rows if cost is not None), start=Decimal("0"))
    return ImpulseReport(quarter=quarter, count=len(rows), total_avoided_cost_eur=total)
