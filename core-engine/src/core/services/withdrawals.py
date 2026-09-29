"""PARTE 7.9/14: calculadora de retiro sostenible + registro del retiro
mensual-nomina "SIN EXCEPCION" (14: se ejecuta aunque el mes sea negativo
-- el gate es el checklist firmado, no el resultado del mes). Envuelve
`sustainable_withdrawal()` (formulas/audit.py, G2) con la curva de equity
real (reutiliza `risk.py::real_portfolio_equity_curve`)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.governance import ChecklistRun, WithdrawalLog
from core.formulas.audit import sustainable_withdrawal
from core.formulas.portfolio import daily_returns
from core.formulas.trading import max_drawdown_pct
from core.formulas.types import WithdrawalConfig
from core.services.risk import real_portfolio_equity_curve

_TRADING_DAYS_PER_MONTH = 21


@dataclass(frozen=True)
class WithdrawalServiceConfig:
    safety_margin: Decimal = Decimal("1.0")
    max_dd_gate_pct: Decimal = Decimal("8")
    window_days: int = 365


async def calculate(
    session: AsyncSession,
    config: WithdrawalServiceConfig,
    now: datetime,
    account_id: int | None = None,
) -> Decimal:
    window_start = now - timedelta(days=config.window_days)
    equity_curve = await real_portfolio_equity_curve(session, window_start, account_id)
    if len(equity_curve) < 2:
        return Decimal("0")

    returns = daily_returns(equity_curve)
    if returns.empty:
        return Decimal("0")

    avg_monthly_return = float((1 + returns.mean()) ** _TRADING_DAYS_PER_MONTH - 1)
    max_dd = max_drawdown_pct([Decimal(str(v)) for v in equity_curve])
    equity = Decimal(str(equity_curve.iloc[-1]))

    return sustainable_withdrawal(
        avg_monthly_return,
        max_dd,
        equity,
        WithdrawalConfig(
            safety_margin=config.safety_margin, max_dd_gate_pct=config.max_dd_gate_pct
        ),
    )


async def register_withdrawal(
    session: AsyncSession,
    amount: Decimal,
    checklist_run: ChecklistRun,
    equity_before: Decimal,
    now: datetime,
    account_id: int | None = None,
) -> WithdrawalLog:
    if not checklist_run.completed:
        raise ValueError("register_withdrawal: el checklist mensual no esta completado")

    log = WithdrawalLog(
        ts=now,
        amount=amount,
        equity_before=equity_before,
        checklist_completed=checklist_run.items,
        account_id=account_id,
    )
    session.add(log)
    await session.flush()
    return log
