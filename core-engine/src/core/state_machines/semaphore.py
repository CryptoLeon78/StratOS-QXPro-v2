"""PARTE 6.1: semaforo por bot VERDE/AMARILLO/NARANJA."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ActorType, AlertLevel, DecisionStatus, SemaphoreState
from core.db.models.accounts import Bot
from core.db.models.decisions import Alert, Decision, DecisionLog, SemaphoreTransition
from core.state_machines.hash_chain import GENESIS_HASH, compute_decision_hash
from core.state_machines.types import SemaphoreConfig, SemaphoreMetrics, TransitionResult


def _instruction_for(state: SemaphoreState, config: SemaphoreConfig, magic_number: int) -> str:
    if state == SemaphoreState.VERDE:
        return config.instruction_verde
    if state == SemaphoreState.AMARILLO:
        return config.instruction_amarillo
    return config.instruction_naranja_template.format(magic=magic_number)


def _unchanged(
    state: SemaphoreState, config: SemaphoreConfig, magic_number: int
) -> TransitionResult:
    return TransitionResult(
        changed=False,
        from_state=state.value,
        to_state=state.value,
        decision_type=None,
        instruction_text=_instruction_for(state, config, magic_number),
        severity=None,
        requires_confirmation=False,
        trigger_metrics={},
    )


def evaluate_semaphore_transition(
    current_state: SemaphoreState,
    metrics: SemaphoreMetrics,
    config: SemaphoreConfig,
    magic_number: int,
    days_in_amarillo: int = 0,
    days_meeting_recovery_condition: int = 0,
    virtual_trades_clean: int = 0,
    signed_by: str | None = None,
) -> TransitionResult:
    """PARTE 6.1: las 5 filas de la tabla de transicion, en orden de
    prioridad (el incumplimiento de contrato, "cualquiera -> NARANJA", se
    evalua primero porque aplica sin importar el estado de partida)."""
    naranja_instruction = config.instruction_naranja_template.format(magic=magic_number)

    if current_state != SemaphoreState.NARANJA and metrics.dd_bot_pct > metrics.dd_contract_pct:
        return TransitionResult(
            changed=True,
            from_state=current_state.value,
            to_state=SemaphoreState.NARANJA.value,
            decision_type="CONTRACT_BREACH",
            instruction_text=naranja_instruction,
            severity=AlertLevel.CRITICA,
            requires_confirmation=True,
            trigger_metrics={
                "dd_bot_pct": str(metrics.dd_bot_pct),
                "dd_contract_pct": str(metrics.dd_contract_pct),
            },
        )

    if current_state == SemaphoreState.VERDE:
        reasons: list[str] = []
        if metrics.pf_rolling < config.pf_warn * metrics.pf_baseline:
            reasons.append("pf_rolling")
        if metrics.exp_rolling < config.exp_warn * metrics.exp_baseline:
            reasons.append("exp_rolling")
        if metrics.loss_streak > metrics.loss_streak_p99_baseline:
            reasons.append("loss_streak")
        if metrics.page_hinkley_triggered:
            reasons.append("page_hinkley")
        if not reasons:
            return _unchanged(SemaphoreState.VERDE, config, magic_number)
        return TransitionResult(
            changed=True,
            from_state="VERDE",
            to_state="AMARILLO",
            decision_type="SEMAPHORE_TRANSITION",
            instruction_text=config.instruction_amarillo,
            severity=AlertLevel.SUAVE,
            requires_confirmation=True,
            trigger_metrics={
                "reasons": reasons,
                "pf_rolling": metrics.pf_rolling,
                "pf_baseline": metrics.pf_baseline,
                "exp_rolling": metrics.exp_rolling,
                "exp_baseline": metrics.exp_baseline,
                "loss_streak": metrics.loss_streak,
            },
            new_sizing_pct=config.sizing_amarillo_pct,
        )

    if current_state == SemaphoreState.AMARILLO:
        naranja_reasons: list[str] = []
        if metrics.pf_rolling < config.pf_orange * metrics.pf_baseline:
            naranja_reasons.append("pf_rolling")
        if days_in_amarillo >= config.orange_days:
            naranja_reasons.append("days_without_recovery")
        orange_ratio = Decimal(str(config.dd_contract_orange_ratio))
        if metrics.dd_bot_pct > orange_ratio * metrics.dd_contract_pct:
            naranja_reasons.append("dd_bot_pct")
        if naranja_reasons:
            return TransitionResult(
                changed=True,
                from_state="AMARILLO",
                to_state="NARANJA",
                decision_type="SEMAPHORE_TRANSITION",
                instruction_text=naranja_instruction,
                severity=AlertLevel.CRITICA,
                requires_confirmation=True,
                trigger_metrics={
                    "reasons": naranja_reasons,
                    "days_in_amarillo": days_in_amarillo,
                    "pf_rolling": metrics.pf_rolling,
                    "pf_baseline": metrics.pf_baseline,
                },
            )
        recovers = (
            metrics.pf_rolling >= config.pf_recover * metrics.pf_baseline
            and metrics.exp_rolling >= config.exp_recover * metrics.exp_baseline
            and days_meeting_recovery_condition >= config.recovery_days
        )
        if recovers:
            return TransitionResult(
                changed=True,
                from_state="AMARILLO",
                to_state="VERDE",
                decision_type="SEMAPHORE_TRANSITION",
                instruction_text=config.instruction_verde,
                severity=AlertLevel.INFO,
                requires_confirmation=False,
                trigger_metrics={
                    "pf_rolling": metrics.pf_rolling,
                    "pf_baseline": metrics.pf_baseline,
                    "days_meeting_recovery_condition": days_meeting_recovery_condition,
                },
                new_sizing_pct=config.sizing_verde_pct,
            )
        return _unchanged(SemaphoreState.AMARILLO, config, magic_number)

    # NARANJA
    if (
        signed_by is not None
        and virtual_trades_clean >= config.orange_virtual_trades
        and metrics.pf_virtual is not None
        and metrics.pf_virtual >= config.pf_recover * metrics.pf_baseline
        and metrics.exp_virtual is not None
        and metrics.exp_virtual > 0
    ):
        return TransitionResult(
            changed=True,
            from_state="NARANJA",
            to_state="VERDE",
            decision_type="SEMAPHORE_TRANSITION",
            instruction_text=config.instruction_verde,
            severity=AlertLevel.INFO,
            requires_confirmation=False,
            trigger_metrics={
                "virtual_trades_clean": virtual_trades_clean,
                "pf_virtual": metrics.pf_virtual,
                "exp_virtual": metrics.exp_virtual,
                "signed_by": signed_by,
            },
            new_sizing_pct=config.sizing_verde_pct,
        )
    return _unchanged(SemaphoreState.NARANJA, config, magic_number)


async def apply_semaphore_transition(
    session: AsyncSession,
    redis: Redis,
    bot: Bot,
    result: TransitionResult,
) -> None:
    """Persiste SemaphoreTransition + DecisionLog (hash-chain) + Decision
    (si requiere confirmacion) + Alert, actualiza Bot, y publica en
    events:semaphore con el esquema de PARTE 9.3. No-op si `result.changed`
    es False (una evaluacion sin cambio no ensucia el historial)."""
    if not result.changed:
        return

    now = datetime.now(UTC)

    session.add(
        SemaphoreTransition(
            bot_id=bot.id,
            ts=now,
            from_state=SemaphoreState(result.from_state),
            to_state=SemaphoreState(result.to_state),
            trigger_metrics=result.trigger_metrics,
            instruction_text=result.instruction_text or "",
        )
    )

    last_hash = (
        await session.execute(select(DecisionLog.hash).order_by(DecisionLog.id.desc()).limit(1))
    ).scalar_one_or_none()
    prev_hash = last_hash or GENESIS_HASH
    payload: dict[str, Any] = {
        "bot_id": bot.id,
        "magic_number": bot.magic_number,
        "from": result.from_state,
        "to": result.to_state,
        **result.trigger_metrics,
    }
    new_hash = compute_decision_hash(
        prev_hash=prev_hash,
        ts=now,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type=result.decision_type or "SEMAPHORE_TRANSITION",
        payload=payload,
    )
    session.add(
        DecisionLog(
            ts=now,
            actor=ActorType.SYSTEM,
            module="semaphore",
            decision_type=result.decision_type or "SEMAPHORE_TRANSITION",
            payload=payload,
            prev_hash=prev_hash,
            hash=new_hash,
        )
    )

    if result.requires_confirmation:
        session.add(
            Decision(
                ts=now,
                module="semaphore",
                title=f"{bot.name}: {result.from_state} -> {result.to_state}",
                description=(
                    f"Bot magic {bot.magic_number} cambia de "
                    f"{result.from_state} a {result.to_state}."
                ),
                instruction_text=result.instruction_text or "",
                evidence=result.trigger_metrics,
                status=DecisionStatus.PENDING,
                account_id=bot.account_id,
            )
        )

    if result.severity is not None:
        session.add(
            Alert(
                ts=now,
                level=result.severity,
                module="semaphore",
                message=f"Bot magic {bot.magic_number}: {result.from_state} -> {result.to_state}",
                action_required=result.instruction_text if result.requires_confirmation else None,
                account_id=bot.account_id,
            )
        )

    bot.semaphore_state = SemaphoreState(result.to_state)
    bot.entered_state_at = now
    if result.new_sizing_pct is not None:
        bot.sizing_current_pct = result.new_sizing_pct

    event = {
        "type": "semaphore.transition",
        "ts": now.isoformat(),
        "bot_id": bot.id,
        "magic_number": bot.magic_number,
        "from": result.from_state,
        "to": result.to_state,
        "instruction": result.instruction_text,
        "requires_confirmation": result.requires_confirmation,
    }
    await redis.publish("events:semaphore", json.dumps(event))
