"""PARTE 9.2: `GET /api/v1/pipeline/board` + `POST /candidates` +
`/{id}/promote` + `/{id}/demo-readiness` + `/{id}/kill` + `GET /{id}/gate`
-- pestaña Pipeline (7.3, kanban de 7 columnas). Ascensos F1-F2 son
manuales (este router); F3 exige una admision demo persistida y F4+ SOLO por
gate automatico (6.3) -- `promote` los rechaza con 409, el
unico camino real es `pipeline_gate.py::evaluate_and_persist` (barrido,
ya existe G5). `kill` reutiliza `apply_cemetery_archival` (G3, ya existe:
autopsia obligatoria, valida antes de tocar la sesion)."""

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.config import Settings, get_settings
from core.db.base import get_session
from core.db.enums import (
    AccountDataOrigin,
    ActorType,
    BotOriginKind,
    CemeteryCause,
    PipelinePhase,
    Verdict,
)
from core.db.models.accounts import Account, Baseline, Bot
from core.db.models.market import ImportArtifact
from core.db.models.pipeline import CemeteryEntry, PipelineCandidate, PipelinePhaseTransition
from core.redis import get_redis
from core.services.demo_attachment import (
    DemoAttachmentManifest,
    candidate_asset,
    evaluate_demo_attachment,
    has_validated_backtest,
    register_demo_attachment,
)
from core.services.pipeline_history import record_phase_transition
from core.state_machines.challenger import apply_cemetery_archival

router = APIRouter(
    prefix="/api/v1/pipeline", tags=["pipeline"], dependencies=[Depends(get_current_user)]
)

# F3 is a registered admission record.  Moving it to F4 is deliberately not a
# manual UI operation: it requires an externally verified demo attachment.
_MANUAL_PHASES = (PipelinePhase.F1, PipelinePhase.F2)
_PHASE_ORDER = [
    PipelinePhase.F1,
    PipelinePhase.F2,
    PipelinePhase.F3,
    PipelinePhase.F4,
    PipelinePhase.F5,
    PipelinePhase.F6,
    PipelinePhase.F7,
]


class CandidateResponse(BaseModel):
    id: int
    bot_id: int
    account_id: int
    account_origin: AccountDataOrigin
    bot_origin: BotOriginKind
    current_phase: PipelinePhase
    entered_phase_at: datetime
    incubation_days: int
    oos_trades: int
    profit_factor: float | None
    expectancy_r: float | None
    sharpe: float | None
    max_dd_pct: Decimal | None
    wfe: float | None
    trades_per_week: float | None
    gates_passed: int
    gates_total: int
    provisional: bool
    verdict: Verdict | None
    verdict_reason: str | None
    decision_eta_days: int | None
    evaluated_at: datetime | None
    backtest_vs_forward: "BacktestVsForwardResponse | None" = None

    model_config = {"from_attributes": True}


class BacktestMetricsResponse(BaseModel):
    profit_factor: float
    expectancy_r: float
    sharpe: float
    max_dd_pct: Decimal


class ForwardMetricsResponse(BaseModel):
    profit_factor: float | None
    expectancy_r: float | None
    sharpe: float | None
    max_dd_pct: Decimal | None


class BacktestVsForwardResponse(BaseModel):
    """Comparación explícita; no fabrica datos si el bot no tiene baseline."""

    backtest: BacktestMetricsResponse
    forward: ForwardMetricsResponse
    baseline_created_at: datetime
    baseline_provenance: str | None
    delta_profit_factor: float | None
    delta_expectancy_r: float | None
    delta_sharpe: float | None
    delta_max_dd_pct: Decimal | None


class CreateCandidateRequest(BaseModel):
    bot_id: int


class KillRequest(BaseModel):
    cause: CemeteryCause
    autopsy_text: str
    lesson: str


class CemeteryEntryResponse(BaseModel):
    id: int
    bot_id: int
    retired_at: datetime
    cause: CemeteryCause
    autopsy_text: str
    lesson: str
    revalidation_from_phase: PipelinePhase
    reactivation_blocked: bool

    model_config = {"from_attributes": True}


class PipelinePhaseTransitionResponse(BaseModel):
    from_phase: PipelinePhase | None
    to_phase: PipelinePhase
    reason: str | None
    actor: ActorType
    occurred_at: datetime

    model_config = {"from_attributes": True}


class OperationalQueueEntryResponse(BaseModel):
    rank: int
    strategy_name: str
    symbol: str | None
    timeframe: str | None
    state: str


class OperationalQueueResponse(BaseModel):
    status: str
    detail: str | None = None
    generated_at_utc: datetime | None = None
    snapshot_sha256: str | None = None
    entries: list[OperationalQueueEntryResponse] = []


class DemoReadinessRequirement(BaseModel):
    key: str
    satisfied: bool


class DemoReadinessResponse(BaseModel):
    candidate_id: int
    ready: bool
    requirements: list[DemoReadinessRequirement]
    next_action: str


class RegisterDemoAttachmentRequest(BaseModel):
    """Declaración humana de un adjunto ya realizado fuera de StratOS."""

    manifest: DemoAttachmentManifest


def _load_operational_queue_snapshot(settings: Settings) -> OperationalQueueResponse:
    """Expone sólo la vista sellada que Windows publica en modo lectura."""
    path = settings.operational_runtime_dir / "operational-tester-queue.json"
    if not path.is_file():
        return OperationalQueueResponse(status="ABSENT", detail="cola local aún no publicada")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        seal = payload.pop("snapshot_sha256")
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if not isinstance(seal, str) or hashlib.sha256(canonical).hexdigest() != seal:
            return OperationalQueueResponse(
                status="INVALID", detail="sello de cola local no válido"
            )
        entries = [
            OperationalQueueEntryResponse.model_validate(item) for item in payload["entries"]
        ]
        return OperationalQueueResponse(
            status="READY",
            generated_at_utc=payload["generated_at_utc"],
            snapshot_sha256=seal,
            entries=entries,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return OperationalQueueResponse(status="INVALID", detail="formato de cola local no válido")


async def _get_candidate(session: AsyncSession, candidate_id: int) -> PipelineCandidate:
    candidate = await session.get(PipelineCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "candidato no encontrado")
    return candidate


async def _demo_readiness(
    session: AsyncSession, candidate: PipelineCandidate
) -> DemoReadinessResponse:
    """Checks only persisted evidence; it never infers a chart attachment."""
    bot = await session.get(Bot, candidate.bot_id)
    if bot is None:
        raise RuntimeError(f"candidato {candidate.id} sin bot")
    account = await session.get(Account, bot.account_id)
    if account is None:
        raise RuntimeError(f"bot {bot.id} sin cuenta")
    asset = await candidate_asset(session, candidate, bot)
    backtest_validated = await has_validated_backtest(session, asset)
    attachment = await evaluate_demo_attachment(session, candidate, bot, account)
    requirements = [
        DemoReadinessRequirement(key="baseline_signed", satisfied=bot.baseline_id is not None),
        DemoReadinessRequirement(
            key="demo_account", satisfied=account.data_origin == AccountDataOrigin.BROKER_DEMO
        ),
        DemoReadinessRequirement(key="backtest_validated", satisfied=backtest_validated),
        *[
            DemoReadinessRequirement(key=key, satisfied=satisfied)
            for key, satisfied in attachment.requirements.items()
        ],
        DemoReadinessRequirement(key="demo_attachment_verified", satisfied=attachment.verified),
    ]
    ready = all(item.satisfied for item in requirements)
    return DemoReadinessResponse(
        candidate_id=candidate.id,
        ready=ready,
        requirements=requirements,
        next_action="DEMO_ATTACHMENT_REQUIRED" if not ready else "AUTOMATIC_F4_GATE",
    )


async def _candidate_response(
    session: AsyncSession, candidate: PipelineCandidate
) -> CandidateResponse:
    """Añade el baseline firmado y deltas forward sin inferir una baseline."""
    bot = await session.get(Bot, candidate.bot_id)
    if bot is None:
        raise RuntimeError(f"candidato {candidate.id} sin bot")
    account = await session.get(Account, bot.account_id)
    if account is None:
        raise RuntimeError(f"bot {bot.id} sin cuenta")
    response = CandidateResponse.model_validate(
        {
            field: getattr(candidate, field)
            for field in CandidateResponse.model_fields
            if field not in {"account_id", "account_origin", "bot_origin", "backtest_vs_forward"}
        }
        | {
            "account_id": bot.account_id,
            "account_origin": account.data_origin,
            "bot_origin": bot.origin_kind,
        }
    )
    if bot.baseline_id is None:
        return response
    baseline = await session.get(Baseline, bot.baseline_id)
    if baseline is None:
        return response
    provenance: str | None = None
    if baseline.artifact_id is not None:
        artifact = await session.get(ImportArtifact, baseline.artifact_id)
        provenance = artifact.source_path if artifact is not None else None
    forward = ForwardMetricsResponse(
        profit_factor=candidate.profit_factor,
        expectancy_r=candidate.expectancy_r,
        sharpe=candidate.sharpe,
        max_dd_pct=candidate.max_dd_pct,
    )
    response.backtest_vs_forward = BacktestVsForwardResponse(
        backtest=BacktestMetricsResponse(
            profit_factor=baseline.profit_factor,
            expectancy_r=baseline.expectancy_r,
            sharpe=baseline.sharpe,
            max_dd_pct=baseline.max_dd_pct,
        ),
        forward=forward,
        baseline_created_at=baseline.created_at,
        baseline_provenance=provenance,
        delta_profit_factor=(
            forward.profit_factor - baseline.profit_factor
            if forward.profit_factor is not None
            else None
        ),
        delta_expectancy_r=(
            forward.expectancy_r - baseline.expectancy_r
            if forward.expectancy_r is not None
            else None
        ),
        delta_sharpe=forward.sharpe - baseline.sharpe if forward.sharpe is not None else None,
        delta_max_dd_pct=(
            forward.max_dd_pct - baseline.max_dd_pct if forward.max_dd_pct is not None else None
        ),
    )
    return response


@router.get("/board", response_model=list[CandidateResponse])
async def pipeline_board(
    account_id: int | None = Query(default=None),
    data_origin: AccountDataOrigin | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[CandidateResponse]:
    statement = (
        select(PipelineCandidate)
        .join(Bot, Bot.id == PipelineCandidate.bot_id)
        .join(Account, Account.id == Bot.account_id)
    )
    if account_id is not None:
        statement = statement.where(Bot.account_id == account_id)
    if data_origin is not None:
        statement = statement.where(Account.data_origin == data_origin)
    candidates = list((await session.execute(statement)).scalars().all())
    return [await _candidate_response(session, candidate) for candidate in candidates]


@router.get("/operational-queue", response_model=OperationalQueueResponse)
async def operational_queue(
    settings: Settings = Depends(get_settings),
) -> OperationalQueueResponse:
    """Estado read-only de la cola local; no abre ni controla MT5."""
    return _load_operational_queue_snapshot(settings)


@router.post("/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    body: CreateCandidateRequest, session: AsyncSession = Depends(get_session)
) -> CandidateResponse:
    bot = await session.get(Bot, body.bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")
    candidate = PipelineCandidate(
        bot_id=body.bot_id,
        current_phase=PipelinePhase.F1,
        entered_phase_at=datetime.now(UTC),
        incubation_days=0,
        oos_trades=0,
    )
    session.add(candidate)
    await session.flush()
    record_phase_transition(
        session,
        candidate,
        from_phase=None,
        to_phase=PipelinePhase.F1,
        actor=ActorType.HUMAN,
        reason="CANDIDATE_CREATED",
    )
    await session.commit()
    return await _candidate_response(session, candidate)


@router.post("/{candidate_id}/promote", response_model=CandidateResponse)
async def promote_candidate(
    candidate_id: int, session: AsyncSession = Depends(get_session)
) -> CandidateResponse:
    candidate = await _get_candidate(session, candidate_id)
    if candidate.current_phase not in _MANUAL_PHASES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "ascensos F4+ solo por gate automatico (PARTE 6.3), no manual",
        )
    next_index = _PHASE_ORDER.index(candidate.current_phase) + 1
    prior_phase = candidate.current_phase
    candidate.current_phase = _PHASE_ORDER[next_index]
    candidate.entered_phase_at = datetime.now(UTC)
    record_phase_transition(
        session,
        candidate,
        from_phase=prior_phase,
        to_phase=candidate.current_phase,
        actor=ActorType.HUMAN,
        reason="MANUAL_PROMOTION",
    )
    await session.commit()
    return await _candidate_response(session, candidate)


@router.post("/{candidate_id}/demo-readiness", response_model=DemoReadinessResponse)
async def check_demo_readiness(
    candidate_id: int, session: AsyncSession = Depends(get_session)
) -> DemoReadinessResponse:
    """Runs the F3 admission preflight without opening MT5 or changing an EA."""
    candidate = await _get_candidate(session, candidate_id)
    if candidate.current_phase != PipelinePhase.F3:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "la comprobacion de admision demo solo corresponde a F3",
        )
    return await _demo_readiness(session, candidate)


@router.post("/{candidate_id}/demo-attachment", response_model=DemoReadinessResponse)
async def register_demo_attachment_from_pipeline(
    candidate_id: int,
    body: RegisterDemoAttachmentRequest,
    session: AsyncSession = Depends(get_session),
) -> DemoReadinessResponse:
    """Persiste evidencia de un adjunto humano; nunca controla MetaTrader."""
    candidate = await _get_candidate(session, candidate_id)
    try:
        await register_demo_attachment(
            session,
            candidate=candidate,
            manifest=body.manifest,
            source_path=Path(f"pipeline-candidate-{candidate.id}-demo-attachment.json"),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await session.commit()
    return await _demo_readiness(session, candidate)


@router.post("/{candidate_id}/kill", response_model=CemeteryEntryResponse)
async def kill_candidate(
    candidate_id: int,
    body: KillRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> CemeteryEntry:
    candidate = await _get_candidate(session, candidate_id)
    bot = await session.get(Bot, candidate.bot_id)
    if bot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bot no encontrado")

    try:
        await apply_cemetery_archival(
            session, redis, bot, body.cause, body.autopsy_text, body.lesson
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    prior_phase = candidate.current_phase
    candidate.current_phase = PipelinePhase.CEMENTERIO
    record_phase_transition(
        session,
        candidate,
        from_phase=prior_phase,
        to_phase=PipelinePhase.CEMENTERIO,
        actor=ActorType.HUMAN,
        reason=body.cause.value,
    )
    await session.commit()

    entry = (
        await session.execute(select(CemeteryEntry).where(CemeteryEntry.bot_id == bot.id))
    ).scalar_one()
    return entry


@router.get("/{candidate_id}/gate", response_model=CandidateResponse)
async def candidate_gate(
    candidate_id: int, session: AsyncSession = Depends(get_session)
) -> CandidateResponse:
    return await _candidate_response(session, await _get_candidate(session, candidate_id))


@router.get("/{candidate_id}/history", response_model=list[PipelinePhaseTransitionResponse])
async def candidate_history(
    candidate_id: int, session: AsyncSession = Depends(get_session)
) -> list[PipelinePhaseTransition]:
    await _get_candidate(session, candidate_id)
    result = await session.execute(
        select(PipelinePhaseTransition)
        .where(PipelinePhaseTransition.candidate_id == candidate_id)
        .order_by(PipelinePhaseTransition.occurred_at)
    )
    return list(result.scalars().all())
