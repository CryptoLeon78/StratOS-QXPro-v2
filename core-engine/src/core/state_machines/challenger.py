"""PARTE 6.3: rotacion darwiniana champion/challenger (5 criterios) +
cementerio (autopsia obligatoria, sin retorno)."""

import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ActorType, AlertLevel, CemeteryCause, PipelinePhase
from core.db.models.accounts import Bot
from core.db.models.decisions import Alert, DecisionLog
from core.db.models.pipeline import CemeteryEntry, ChallengerEvaluation
from core.state_machines.hash_chain import GENESIS_HASH, compute_decision_hash
from core.state_machines.types import (
    ChallengerConfig,
    ChallengerMetrics,
    ChallengerResult,
    ReactivationResult,
)


def evaluate_challenger(
    challenger: ChallengerMetrics,
    champion: ChallengerMetrics,
    config: ChallengerConfig,
) -> ChallengerResult:
    """PARTE 6.3: 5 criterios de rotacion darwiniana. El challenger debe
    superar al champion en TODOS a la vez (ejemplo real: Helios, Sharpe
    x1,22, p=0,03, misma correlacion 0,31 -- rotacion limpia)."""
    criteria = {
        "sharpe": challenger.sharpe >= config.sharpe_ratio * champion.sharpe,
        "p_value": challenger.p_value < config.p_max,
        "correlation_not_higher": challenger.correlation_with_block
        <= champion.correlation_with_block,
        "maxdd_not_higher": challenger.max_dd_pct <= champion.max_dd_pct,
        "expectancy_not_lower": challenger.expectancy_r >= champion.expectancy_r,
    }
    return ChallengerResult(passed=all(criteria.values()), criteria=criteria)


def evaluate_overstay(months_in_f6: int, config: ChallengerConfig) -> bool:
    """PARTE 6.3: "OVERSTAY: challenger >6 meses en F6 sin superar al
    champion -> alerta" (regla de los 6 meses)."""
    return months_in_f6 > config.overstay_months


def evaluate_cemetery_reactivation(
    bot_id: int,
    config: ChallengerConfig,
    signed_by: str | None = None,
    justification: str | None = None,
) -> ReactivationResult:
    """PARTE 6.3: "Reactivacion: API 409 siempre; sin control en UI;
    reincorporacion solo como candidato NUEVO desde F3". Ningun parametro
    (firma, justificacion) puede cambiar el resultado -- no hay excepcion."""
    return ReactivationResult(allowed=False, reason=config.cemetery_banner)


async def _write_decision_log(
    session: AsyncSession, now: datetime, module: str, decision_type: str, payload: dict[str, Any]
) -> None:
    last_hash = (
        await session.execute(select(DecisionLog.hash).order_by(DecisionLog.id.desc()).limit(1))
    ).scalar_one_or_none()
    prev_hash = last_hash or GENESIS_HASH
    new_hash = compute_decision_hash(
        prev_hash=prev_hash,
        ts=now,
        actor=ActorType.SYSTEM,
        module=module,
        decision_type=decision_type,
        payload=payload,
    )
    session.add(
        DecisionLog(
            ts=now,
            actor=ActorType.SYSTEM,
            module=module,
            decision_type=decision_type,
            payload=payload,
            prev_hash=prev_hash,
            hash=new_hash,
        )
    )


async def apply_cemetery_archival(
    session: AsyncSession,
    redis: Redis,
    bot: Bot,
    cause: CemeteryCause,
    autopsy_text: str,
    lesson: str,
) -> None:
    """Archiva un bot en el Cementerio. PARTE 6.3: "autopsia escrita
    OBLIGATORIA (causa + leccion, NOT NULL) antes de archivar" -- se valida
    y se rechaza ANTES de tocar la sesion si falta cualquiera de las dos."""
    if not autopsy_text.strip():
        raise ValueError("autopsy_text es obligatorio para archivar en el Cementerio (PARTE 6.3).")
    if not lesson.strip():
        raise ValueError("lesson es obligatoria para archivar en el Cementerio (PARTE 6.3).")

    now = datetime.now(UTC)
    session.add(
        CemeteryEntry(
            bot_id=bot.id,
            retired_at=now,
            cause=cause,
            autopsy_text=autopsy_text,
            lesson=lesson,
        )
    )
    bot.pipeline_phase = PipelinePhase.CEMENTERIO
    bot.slot = None

    payload = {"bot_id": bot.id, "cause": cause.value}
    await _write_decision_log(session, now, "pipeline", "CEMETERY_ARCHIVAL", payload)

    session.add(
        Alert(
            ts=now,
            level=AlertLevel.SUAVE,
            module="pipeline",
            message=f"Bot {bot.name} archivado en el Cementerio ({cause.value}).",
            action_required=None,
            account_id=bot.account_id,
        )
    )

    event = {
        "type": "cemetery.archived",
        "ts": now.isoformat(),
        "bot_id": bot.id,
        "cause": cause.value,
    }
    await redis.publish("events:pipeline", json.dumps(event))


async def apply_challenger_rotation(
    session: AsyncSession,
    redis: Redis,
    challenger_bot: Bot,
    champion_bot: Bot,
    slot: str,
    evaluation: ChallengerResult,
    p_value: float,
) -> None:
    """Persiste la evaluacion de rotacion (ChallengerEvaluation) siempre; si
    `evaluation.passed`, ademas archiva al champion (`OUTPERFORMED_BY_CHALLENGER`)
    y el challenger ocupa el slot liberado (PARTE 6.3)."""
    now = datetime.now(UTC)
    notes = (
        f"Challenger supero los 5 criterios en el slot {slot}."
        if evaluation.passed
        else f"Challenger no supero al champion en el slot {slot}."
    )
    session.add(
        ChallengerEvaluation(
            ts=now,
            challenger_bot_id=challenger_bot.id,
            champion_bot_id=champion_bot.id,
            slot=slot,
            criteria=evaluation.criteria,
            passed=evaluation.passed,
            p_value=p_value,
            notes=notes,
        )
    )

    if not evaluation.passed:
        event = {
            "type": "challenger.rotation_evaluated",
            "ts": now.isoformat(),
            "challenger_bot_id": challenger_bot.id,
            "champion_bot_id": champion_bot.id,
            "slot": slot,
            "passed": False,
        }
        await redis.publish("events:pipeline", json.dumps(event))
        return

    autopsy_text = (
        f"Superado por el challenger {challenger_bot.name} en el slot {slot}: "
        "Sharpe, significacion estadistica, correlacion con el bloque, maxDD y "
        "expectancy favorecen al challenger en los 5 criterios de rotacion (PARTE 6.3)."
    )
    lesson = (
        "Revisar el slot periodicamente para detectar degradacion relativa "
        "frente a challengers en cartera."
    )
    await apply_cemetery_archival(
        session,
        redis,
        champion_bot,
        CemeteryCause.OUTPERFORMED_BY_CHALLENGER,
        autopsy_text,
        lesson,
    )
    challenger_bot.slot = slot
    challenger_bot.pipeline_phase = PipelinePhase.PRODUCCION

    event = {
        "type": "challenger.rotation_evaluated",
        "ts": now.isoformat(),
        "challenger_bot_id": challenger_bot.id,
        "champion_bot_id": champion_bot.id,
        "slot": slot,
        "passed": True,
    }
    await redis.publish("events:pipeline", json.dumps(event))


async def apply_overstay_alert(
    session: AsyncSession,
    redis: Redis,
    bot: Bot,
    config: ChallengerConfig,
) -> None:
    """PARTE 6.3: alerta "Competitivo pero no superior" para un challenger
    que lleva >6 meses en F6 sin ganar la rotacion (regla de los 6 meses)."""
    now = datetime.now(UTC)
    session.add(
        Alert(
            ts=now,
            level=AlertLevel.SUAVE,
            module="challenger",
            message=f"{bot.name}: {config.instruction_overstay}",
            action_required=config.instruction_overstay,
            account_id=bot.account_id,
        )
    )
    event = {
        "type": "challenger.overstay",
        "ts": now.isoformat(),
        "bot_id": bot.id,
        "instruction": config.instruction_overstay,
    }
    await redis.publish("events:pipeline", json.dumps(event))
