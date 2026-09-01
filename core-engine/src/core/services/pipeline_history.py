"""Registro append-only de transiciones F1-F7 y Cementerio."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ActorType, PipelinePhase
from core.db.models.pipeline import PipelineCandidate, PipelinePhaseTransition


def record_phase_transition(
    session: AsyncSession,
    candidate: PipelineCandidate,
    *,
    from_phase: PipelinePhase | None,
    to_phase: PipelinePhase,
    actor: ActorType,
    reason: str | None,
) -> None:
    session.add(
        PipelinePhaseTransition(
            candidate_id=candidate.id,
            from_phase=from_phase,
            to_phase=to_phase,
            actor=actor,
            reason=reason,
            occurred_at=datetime.now(UTC),
        )
    )
