"""PARTE 6.3: SIZING_CAP -- el gate del pipeline necesita saber si escalar
el siguiente `staging_step` de un candidato haria que la suma de sizing de
todos los bots en produccion supere `sizing_total_cap` (89%, portfolio-wide,
independiente de la calidad del propio candidato). `evaluate_pipeline_gate`/
`apply_pipeline_gate` (state_machines/pipeline.py, G3) ya aceptan
`sizing_cap_breach`; este modulo es el caller que lo calcula con datos
reales y, si el veredicto es GO, escala `Bot.sizing_current_pct` de verdad
(apply_pipeline_gate no toca ese campo, solo el estado del candidato)."""

from datetime import datetime
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import PipelinePhase, Verdict
from core.db.models.accounts import Bot
from core.db.models.pipeline import PipelineCandidate
from core.state_machines.pipeline import apply_pipeline_gate, evaluate_pipeline_gate
from core.state_machines.types import GateResult, PipelineGateConfig, PipelineGateMetrics

# "Bots activos" a efectos de SIZING_CAP: en produccion real. F7 es la fase
# terminal de campeon (PARTE 7.3: "F7 PRODUCCIÓN (CHAMPION)"); PRODUCCION
# se incluye por si algun flujo futuro la usa como alias -- ni PARTE 5.2 ni
# 6.3 definen explicitamente el universo de "bots activos" (ASSUMPTIONS G5).
_ACTIVE_PHASES = (PipelinePhase.F7, PipelinePhase.PRODUCCION)


async def active_sizing_sum(session: AsyncSession, exclude_bot_id: int | None = None) -> Decimal:
    query = select(func.coalesce(func.sum(Bot.sizing_current_pct), 0)).where(
        Bot.pipeline_phase.in_(_ACTIVE_PHASES)
    )
    if exclude_bot_id is not None:
        query = query.where(Bot.id != exclude_bot_id)
    total = (await session.execute(query)).scalar_one()
    return Decimal(total)


async def compute_sizing_cap_breach(
    session: AsyncSession,
    candidate_bot_id: int,
    candidate_step_pct: Decimal,
    config: PipelineGateConfig,
) -> bool:
    others_total = await active_sizing_sum(session, exclude_bot_id=candidate_bot_id)
    return (others_total + candidate_step_pct) > config.sizing_total_cap


def _next_staging_step(current_pct: Decimal, steps: tuple[int, ...]) -> Decimal | None:
    for step in sorted(steps):
        if Decimal(step) > current_pct:
            return Decimal(step)
    return None


async def escalate_staging_step(
    session: AsyncSession,
    redis: Redis,
    candidate: PipelineCandidate,
    metrics: PipelineGateMetrics,
    config: PipelineGateConfig,
    now: datetime,
) -> GateResult:
    bot = await session.get(Bot, candidate.bot_id)
    if bot is None:
        raise ValueError(f"escalate_staging_step: bot {candidate.bot_id} no existe")

    next_step = _next_staging_step(bot.sizing_current_pct, config.staging_steps)
    if next_step is None:
        raise ValueError("escalate_staging_step: el candidato ya esta en el ultimo escalon")

    breach = await compute_sizing_cap_breach(session, bot.id, next_step, config)
    result = evaluate_pipeline_gate(metrics, config, sizing_cap_breach=breach)
    await apply_pipeline_gate(session, redis, candidate, result)

    if not breach and result.verdict == Verdict.GO.value:
        bot.sizing_current_pct = next_step
        await session.flush()

    return result
