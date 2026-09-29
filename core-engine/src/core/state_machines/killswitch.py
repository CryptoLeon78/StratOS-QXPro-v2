"""PARTE 6.2: kill-switch de portfolio, 4 niveles ("cuadro de diferenciales")."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ActorType, AlertLevel, DecisionStatus
from core.db.models.decisions import Alert, Decision, DecisionLog, KillSwitchEvent
from core.state_machines.hash_chain import GENESIS_HASH, compute_decision_hash
from core.state_machines.types import KillSwitchConfig, TransitionResult

_INSTRUCTION_BY_LEVEL = {
    0: None,
    1: "instruction_l1",
    2: "instruction_l2",
    3: "instruction_l3",
    4: "instruction_l4",
}


def _instruction_for(level: int, config: KillSwitchConfig) -> str | None:
    attr = _INSTRUCTION_BY_LEVEL[level]
    return None if attr is None else str(getattr(config, attr))


def _level_for_dd(portfolio_dd_pct: Decimal, config: KillSwitchConfig) -> int:
    if portfolio_dd_pct >= config.l4:
        return 4
    if portfolio_dd_pct >= config.l3:
        return 3
    if portfolio_dd_pct >= config.l2:
        return 2
    if portfolio_dd_pct >= config.l1:
        return 1
    return 0


def _unchanged(level: int, config: KillSwitchConfig) -> TransitionResult:
    return TransitionResult(
        changed=False,
        from_state=str(level),
        to_state=str(level),
        decision_type=None,
        instruction_text=_instruction_for(level, config),
        severity=None,
        requires_confirmation=False,
        trigger_metrics={},
    )


def evaluate_killswitch_escalation(
    portfolio_dd_pct: Decimal,
    current_level: int,
    config: KillSwitchConfig,
) -> TransitionResult:
    """PARTE 6.2: escalado automatico, solo hacia arriba (una recuperacion de
    DD nunca desescala aqui -- eso exige firma, ver
    `evaluate_killswitch_deescalation`). Puede saltar niveles directamente si
    el DD sube de golpe (p.ej. de L0 a L4 sin pasar por L1-L3)."""
    target = _level_for_dd(portfolio_dd_pct, config)
    if target <= current_level:
        return _unchanged(current_level, config)
    return TransitionResult(
        changed=True,
        from_state=str(current_level),
        to_state=str(target),
        decision_type="KILLSWITCH_ESCALATION",
        instruction_text=_instruction_for(target, config),
        severity=AlertLevel.INFO if target == 1 else AlertLevel.CRITICA,
        requires_confirmation=target >= 2,
        trigger_metrics={"portfolio_dd_pct": str(portfolio_dd_pct), "level": target},
    )


def evaluate_killswitch_deescalation(
    portfolio_dd_pct: Decimal,
    current_level: int,
    config: KillSwitchConfig,
    signed_by: str | None,
) -> TransitionResult:
    """PARTE 6.2: "desescalado solo manual con DD < umbral - 2pp de
    histeresis Y firma". El umbral de referencia es el del nivel actual; al
    desescalar se recalcula el nivel objetivo con el DD real (puede bajar
    varios niveles de golpe, igual que la escalada puede subirlos)."""
    if current_level == 0 or signed_by is None:
        return _unchanged(current_level, config)
    current_threshold = [None, config.l1, config.l2, config.l3, config.l4][current_level]
    assert current_threshold is not None
    if portfolio_dd_pct >= current_threshold - config.hysteresis_pp:
        return _unchanged(current_level, config)
    target = _level_for_dd(portfolio_dd_pct, config)
    return TransitionResult(
        changed=True,
        from_state=str(current_level),
        to_state=str(target),
        decision_type="KILLSWITCH_DEESCALATION",
        instruction_text=_instruction_for(target, config),
        severity=AlertLevel.INFO,
        requires_confirmation=False,
        trigger_metrics={
            "portfolio_dd_pct": str(portfolio_dd_pct),
            "level": target,
            "signed_by": signed_by,
        },
    )


async def apply_killswitch_transition(
    session: AsyncSession,
    redis: Redis,
    result: TransitionResult,
    account_id: int | None = None,
) -> None:
    """Persiste KillSwitchEvent + DecisionLog (hash-chain) + Decision (si
    requiere confirmacion) + Alert, publica en events:killswitch con el
    esquema de PARTE 9.3. No-op si `result.changed` es False. `account_id`
    (ADR 0013) etiqueta el evento, la decision y la alerta con la cuenta a
    la que pertenece el DD; `None` = escalera de portfolio heredada."""
    if not result.changed:
        return

    now = datetime.now(UTC)
    level = int(result.to_state)
    dd_pct = Decimal(str(result.trigger_metrics["portfolio_dd_pct"]))

    session.add(
        KillSwitchEvent(
            ts=now,
            level=level,
            portfolio_dd_pct=dd_pct,
            actions=result.trigger_metrics,
            instruction_text=result.instruction_text or "",
            account_id=account_id,
        )
    )

    last_hash = (
        await session.execute(select(DecisionLog.hash).order_by(DecisionLog.id.desc()).limit(1))
    ).scalar_one_or_none()
    prev_hash = last_hash or GENESIS_HASH
    payload: dict[str, Any] = {
        "from": result.from_state,
        "to": result.to_state,
        **result.trigger_metrics,
    }
    if account_id is not None:
        payload["account_id"] = account_id
    new_hash = compute_decision_hash(
        prev_hash=prev_hash,
        ts=now,
        actor=ActorType.SYSTEM,
        module="killswitch",
        decision_type=result.decision_type or "KILLSWITCH_TRANSITION",
        payload=payload,
    )
    session.add(
        DecisionLog(
            ts=now,
            actor=ActorType.SYSTEM,
            module="killswitch",
            decision_type=result.decision_type or "KILLSWITCH_TRANSITION",
            payload=payload,
            prev_hash=prev_hash,
            hash=new_hash,
        )
    )

    if result.requires_confirmation:
        session.add(
            Decision(
                ts=now,
                module="killswitch",
                title=f"Kill-switch: nivel {result.from_state} -> {result.to_state}",
                description=(f"Drawdown de portfolio {dd_pct}% activa el nivel {result.to_state}."),
                instruction_text=result.instruction_text or "",
                evidence=result.trigger_metrics,
                status=DecisionStatus.PENDING,
                account_id=account_id,
            )
        )

    if result.severity is not None:
        session.add(
            Alert(
                ts=now,
                level=result.severity,
                module="killswitch",
                message=f"Kill-switch nivel {result.from_state} -> {result.to_state}",
                action_required=result.instruction_text if result.requires_confirmation else None,
                account_id=account_id,
            )
        )

    event = {
        "type": "killswitch.transition",
        "ts": now.isoformat(),
        "from": result.from_state,
        "to": result.to_state,
        "instruction": result.instruction_text,
        "requires_confirmation": result.requires_confirmation,
        "account_id": account_id,
    }
    await redis.publish("events:killswitch", json.dumps(event))
