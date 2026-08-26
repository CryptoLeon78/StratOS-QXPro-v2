"""PARTE 8: auditoria, diario de impulsos, retiros."""

from decimal import Decimal

from core.db.enums import ImpulseAction
from core.formulas.types import ImpulseSnapshot, TradeLike, WithdrawalConfig

_STOP_ACTIONS = frozenset({ImpulseAction.CLOSE_POSITION, ImpulseAction.PAUSE_BOT})
_RISK_ACTIONS = frozenset({ImpulseAction.INCREASE_RISK, ImpulseAction.DECREASE_RISK})


def audit_discrepancy(initial: Decimal, flows: Decimal, final: Decimal) -> Decimal:
    """|initial+Σflows-final|/final; final==0 -> CRITICA estructural
    (PARTE 8) -- division indefinida, se propaga como ZeroDivisionError
    para que el caller la trate como alerta CRITICA."""
    if final == 0:
        raise ZeroDivisionError("audit_discrepancy: final=0, descuadre estructural (CRITICA)")
    return abs(initial + flows - final) / final


def counterfactual_impulse(
    bot_trades_after: list[TradeLike],
    desired_action: ImpulseAction,
    snapshot_at_impulse: ImpulseSnapshot,
) -> Decimal:
    """A los 7 dias: resultado real del bot vs resultado simulado de haber
    ejecutado la accion (PARTE 8). CLOSE_POSITION/PAUSE_BOT: simulado=0 (no
    habria nuevos trades). INCREASE_RISK/DECREASE_RISK: simulado = real
    escalado por `sizing_multiplier` vigente en el momento del impulso.
    OTHER: sin cambio de hipotesis, simulado=real. avoided_cost = real -
    simulado (signo documentado en PARTE 8)."""
    real = sum(
        (trade.profit + trade.commission + trade.swap for trade in bot_trades_after),
        start=Decimal("0"),
    )
    if desired_action in _STOP_ACTIONS:
        simulated = Decimal("0")
    elif desired_action in _RISK_ACTIONS:
        simulated = real * snapshot_at_impulse.sizing_multiplier
    else:
        simulated = real
    return real - simulated


def sustainable_withdrawal(
    avg_monthly_return: float, max_dd: Decimal, equity: Decimal, config: WithdrawalConfig
) -> Decimal:
    """Nomina mensual propuesta (PARTE 8/14: "retorno medio 2,69% vs max DD
    4,76%, base de la nomina mensual"). Se anula si el drawdown vigente ya
    supera la puerta de riesgo de `config`, o si el retorno medio es
    negativo (nunca se propone una nomina de una racha perdedora)."""
    if max_dd > config.max_dd_gate_pct:
        return Decimal("0")
    if avg_monthly_return <= 0:
        return Decimal("0")
    return equity * Decimal(str(avg_monthly_return)) * config.safety_margin
