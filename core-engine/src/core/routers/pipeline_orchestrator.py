"""Plano de control de Pipeline para FORJA/SQX y el agente demo local.

El core registra solicitudes; no lanza procesos Windows ni acepta destinos reales.
"""

import hashlib
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.config import Settings, get_settings
from core.db.base import get_session
from core.db.enums import AssetAdmissionStatus
from core.db.models.operations import (
    OperationalAsset,
    OperationalAssetEvent,
    PipelineAgentCommand,
    PipelineAgentCommandEvent,
    PipelineWorkItem,
)
from core.db.models.pipeline import F6Evaluation, F6StagingEvaluation, PipelineCandidate
from core.services.incubation_observation import assemble_incubation_observation

router = APIRouter(prefix="/api/v1/pipeline-orchestrator", tags=["pipeline-orchestrator"])

_ALLOWED_COMMAND_TARGETS = {
    "FORJA_GENERATE": {"ANALYSIS"},
    "SQX_START": {"ANALYSIS"},
    "SQX_STOP": {"ANALYSIS"},
    "MT5_TESTER": {"SQX_VS_MT5_TESTER"},
    "DEMO_INSTALL": {"CONTABO_INCUBATOR_DEMO"},
}


class WorkItemIn(BaseModel):
    kind: str = Field(min_length=1)
    source_key: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)


class CommandIn(BaseModel):
    command_type: str
    payload: dict[str, object] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)
    confirmed: bool = False


class AgentResultIn(BaseModel):
    status: str = Field(pattern="^(SUCCEEDED|FAILED)$")
    result: dict[str, object] = Field(default_factory=dict)


class F2BatchIn(BaseModel):
    asset_ids: list[int] = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


def _work_item_status(command_type: str, command_status: str) -> str:
    """Translate a terminal agent event to the visible F1 project status."""
    if command_status == "FAILED":
        return "FAILED"
    return {
        "FORJA_GENERATE": "GENERATED",
        "SQX_START": "MINING",
        "SQX_STOP": "STOPPED",
    }.get(command_type, "COMPLETED")


def _command_hash(value: CommandIn) -> str:
    return hashlib.sha256(
        json.dumps(value.model_dump(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@router.get("/work-items", dependencies=[Depends(get_current_user)], response_model=None)
async def list_work_items(
    phase: str | None = None,
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[PipelineWorkItem]:
    query = select(PipelineWorkItem).where(PipelineWorkItem.retired_at.is_(None))
    if phase:
        query = query.where(PipelineWorkItem.phase == phase)
    query = query.order_by(PipelineWorkItem.updated_at.desc()).offset(offset).limit(limit)
    return list((await session.scalars(query)).all())


@router.get("/static-assets", dependencies=[Depends(get_current_user)], response_model=None)
async def list_static_assets(
    offset: int = 0, limit: int = 100, session: AsyncSession = Depends(get_session)
) -> list[OperationalAsset]:
    static_event = exists().where(
        OperationalAssetEvent.asset_id == OperationalAsset.id,
        OperationalAssetEvent.status == AssetAdmissionStatus.STATIC_VALIDATED,
    )
    query = (
        select(OperationalAsset)
        .where(static_event)
        .order_by(OperationalAsset.id)
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(query)).all())


@router.get("/f3/backtest-evidence", dependencies=[Depends(get_current_user)], response_model=None)
async def list_f3_backtest_evidence(
    offset: int = 0, limit: int = 100, session: AsyncSession = Depends(get_session)
) -> list[dict[str, object]]:
    rows = await session.execute(
        select(OperationalAsset, OperationalAssetEvent)
        .join(OperationalAssetEvent, OperationalAssetEvent.asset_id == OperationalAsset.id)
        .where(OperationalAssetEvent.status == AssetAdmissionStatus.BACKTEST_VALIDATED)
        .order_by(OperationalAssetEvent.occurred_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [
        {
            "asset_id": asset.id,
            "strategy_name": asset.strategy_name,
            "symbol": asset.symbol,
            "timeframe": asset.timeframe,
            "evidence": event.evidence,
            "occurred_at": event.occurred_at,
        }
        for asset, event in rows
    ]


@router.get("/f5/incubation", dependencies=[Depends(get_current_user)], response_model=None)
async def list_f5_incubation(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    """F5 read model; baseline and demo observation are never mixed."""
    candidates = list(
        (
            await session.scalars(
                select(PipelineCandidate).where(
                    PipelineCandidate.current_phase.in_(("F4", "F5", "F6", "F7"))
                )
            )
        ).all()
    )
    result: list[dict[str, object]] = []
    for candidate in candidates:
        observation = await assemble_incubation_observation(session, candidate)
        if observation is None:
            continue
        result.append(
            {
                "candidate_id": observation.candidate_id,
                "bot_id": observation.bot_id,
                "magic_number": observation.magic_number,
                "current_phase": observation.current_phase,
                "observation_started_at": observation.observation_started_at,
                "tester_baseline": observation.tester_baseline,
                "demo_trade_count": observation.demo_trade_count,
                "demo_trade_first_open_at": observation.demo_trade_first_open_at,
                "demo_trade_last_close_at": observation.demo_trade_last_close_at,
                "valid_observation_days": observation.valid_observation_days,
                "ea_state": observation.ea_state,
                "latest_heartbeat_at": observation.latest_heartbeat_at,
                "latest_equity": observation.latest_equity,
                "observation_status": observation.observation_status,
                "missing_evidence": observation.missing_evidence,
            }
        )
    return result


@router.get("/f6/evaluations", dependencies=[Depends(get_current_user)], response_model=None)
async def list_f6_evaluations(
    candidate_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[F6Evaluation]:
    """Ledger read-only de Aprobar/Posponer/Rechazar derivado de F5."""
    query = (
        select(F6Evaluation).order_by(F6Evaluation.evaluated_at.desc()).offset(offset).limit(limit)
    )
    if candidate_id is not None:
        query = query.where(F6Evaluation.candidate_id == candidate_id)
    return list((await session.scalars(query)).all())


@router.get(
    "/f6/staging-evaluations", dependencies=[Depends(get_current_user)], response_model=None
)
async def list_f6_staging_evaluations(
    candidate_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[F6StagingEvaluation]:
    """Ledger read-only de escalado F6 y comparación challenger/champion.

    La respuesta expone planes, no una orden MT5 ni una promoción F7.
    """
    query = (
        select(F6StagingEvaluation)
        .order_by(F6StagingEvaluation.evaluated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if candidate_id is not None:
        query = query.where(F6StagingEvaluation.candidate_id == candidate_id)
    return list((await session.scalars(query)).all())


@router.post("/f2/backtest-batches", dependencies=[Depends(get_current_user)], response_model=None)
async def enqueue_f2_batch(
    body: F2BatchIn, session: AsyncSession = Depends(get_session)
) -> list[dict[str, object]]:
    """Encola Tester de uno en uno; no inventa ni registra un veredicto F3."""
    asset_query = select(OperationalAsset).where(OperationalAsset.id.in_(body.asset_ids))
    assets = list((await session.scalars(asset_query)).all())
    if len(assets) != len(set(body.asset_ids)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "static asset not found")
    commands: list[dict[str, object]] = []
    now = datetime.now(UTC)
    for asset in assets:
        if not asset.sqx_path or not asset.mql5_path:
            raise HTTPException(status.HTTP_409_CONFLICT, "asset is missing sealed source paths")
        item = await session.scalar(
            select(PipelineWorkItem).where(
                PipelineWorkItem.kind == "F2_TESTER",
                PipelineWorkItem.source_key == f"asset:{asset.id}",
            )
        )
        if item is None:
            item = PipelineWorkItem(
                kind="F2_TESTER",
                source_key=f"asset:{asset.id}",
                phase="F2",
                status="QUEUED",
                payload={
                    "asset_id": asset.id,
                    "strategy_name": asset.strategy_name,
                    "sqx_path": asset.sqx_path,
                    "mql5_path": asset.mql5_path,
                },
                created_at=now,
                updated_at=now,
            )
            session.add(item)
            await session.flush()
        key = f"{body.idempotency_key}:{asset.id}"
        existing = await session.scalar(
            select(PipelineAgentCommand).where(PipelineAgentCommand.idempotency_key == key)
        )
        if existing is None:
            payload = {
                "target_group": "SQX_VS_MT5_TESTER",
                "asset_id": asset.id,
                "sqx_path": asset.sqx_path,
                "mql5_path": asset.mql5_path,
            }
            request_sha256 = hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest()
            command = PipelineAgentCommand(
                work_item_id=item.id,
                command_type="MT5_TESTER",
                idempotency_key=key,
                request_sha256=request_sha256,
                payload=payload,
                requested_at=now,
            )
            session.add(command)
            commands.append({"id": command.id, "asset_id": asset.id, "status": "PENDING"})
        else:
            commands.append({"id": existing.id, "asset_id": asset.id, "status": "PENDING"})
    await session.commit()
    return commands


@router.post(
    "/work-items",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
    response_model=None,
)
async def create_work_item(
    body: WorkItemIn, session: AsyncSession = Depends(get_session)
) -> PipelineWorkItem:
    existing = await session.scalar(
        select(PipelineWorkItem).where(
            PipelineWorkItem.kind == body.kind,
            PipelineWorkItem.source_key == body.source_key,
        )
    )
    if existing:
        return existing
    now = datetime.now(UTC)
    item = PipelineWorkItem(**body.model_dump(), status="PENDING", created_at=now, updated_at=now)
    session.add(item)
    await session.commit()
    return item


@router.post(
    "/work-items/{item_id}/retire",
    dependencies=[Depends(get_current_user)],
    response_model=None,
)
async def retire_work_item(
    item_id: int, session: AsyncSession = Depends(get_session)
) -> PipelineWorkItem:
    item = await session.get(PipelineWorkItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "work item not found")
    item.retired_at = item.updated_at = datetime.now(UTC)
    await session.commit()
    return item


@router.post(
    "/work-items/{item_id}/commands",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
    response_model=None,
)
async def request_command(
    item_id: int, body: CommandIn, session: AsyncSession = Depends(get_session)
) -> dict[str, object]:
    item = await session.get(PipelineWorkItem, item_id)
    if item is None or item.retired_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "work item unavailable")
    allowed_targets = _ALLOWED_COMMAND_TARGETS.get(body.command_type)
    if allowed_targets is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "command is not allowed")
    if body.command_type == "DEMO_INSTALL" and not body.confirmed:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "demo install requires individual confirmation"
        )
    target_group = str(body.payload.get("target_group", ""))
    if target_group not in allowed_targets:
        raise HTTPException(status.HTTP_409_CONFLICT, "target is not allowed for command")
    existing = await session.scalar(
        select(PipelineAgentCommand).where(
            PipelineAgentCommand.idempotency_key == body.idempotency_key
        )
    )
    if existing:
        if existing.request_sha256 != _command_hash(body):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "idempotency key belongs to a different request"
            )
        return {"id": existing.id, "status": "PENDING"}
    command = PipelineAgentCommand(
        work_item_id=item.id,
        command_type=body.command_type,
        idempotency_key=body.idempotency_key,
        request_sha256=_command_hash(body),
        payload=body.payload,
        requested_at=datetime.now(UTC),
    )
    item.status = "QUEUED"
    item.updated_at = command.requested_at
    session.add(command)
    await session.commit()
    return {"id": command.id, "status": "PENDING"}


@router.get("/agent/commands", response_model=None)
async def agent_commands(
    x_pipeline_agent_key: str = Header(default=""),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> list[PipelineAgentCommand]:
    if (
        not settings.pipeline_agent_api_key
        or x_pipeline_agent_key != settings.pipeline_agent_api_key
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "agent authentication failed")
    terminal_event = exists().where(
        PipelineAgentCommandEvent.command_id == PipelineAgentCommand.id,
        PipelineAgentCommandEvent.status.in_(("SUCCEEDED", "FAILED")),
    )
    statement = (
        select(PipelineAgentCommand)
        .where(~terminal_event)
        .order_by(PipelineAgentCommand.requested_at)
        .limit(1)
    )
    return list((await session.scalars(statement)).all())


@router.post("/agent/commands/{command_id}/result", response_model=None)
async def agent_result(
    command_id: int,
    body: AgentResultIn,
    x_pipeline_agent_key: str = Header(default=""),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> PipelineAgentCommandEvent:
    if (
        not settings.pipeline_agent_api_key
        or x_pipeline_agent_key != settings.pipeline_agent_api_key
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "agent authentication failed")
    command = await session.get(PipelineAgentCommand, command_id)
    if command is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "command is not reportable")
    completed = await session.scalar(
        select(PipelineAgentCommandEvent).where(
            PipelineAgentCommandEvent.command_id == command_id,
            PipelineAgentCommandEvent.status.in_(("SUCCEEDED", "FAILED")),
        )
    )
    if completed is not None:
        return completed
    now = datetime.now(UTC)
    event = PipelineAgentCommandEvent(
        command_id=command.id,
        status=body.status,
        result=body.result,
        occurred_at=now,
    )
    if command.work_item_id is not None:
        item = await session.get(PipelineWorkItem, command.work_item_id)
        if item is not None and item.retired_at is None:
            item.status = _work_item_status(command.command_type, body.status)
            item.result = body.result
            item.updated_at = now
    session.add(event)
    await session.commit()
    return event
