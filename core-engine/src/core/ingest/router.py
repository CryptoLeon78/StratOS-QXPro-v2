"""PARTE 9.1: rutas de ingesta. Autenticadas via `X-API-Key`
(`require_api_key`), finas a proposito -- resuelven la cuenta, delegan en
`services/`, comitean. La logica real vive en `services/`, testeable sin
HTTP."""

from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings, get_settings
from core.db.base import get_session
from core.http_client import get_http_client
from core.ingest.accounts import resolve_account
from core.ingest.schemas import (
    EaStateIngestRequest,
    EquityIngestRequest,
    ExecutionIngestRequest,
    HeartbeatIngestRequest,
    IngestResponse,
    PositionsIngestRequest,
    SignalsIngestRequest,
    TradesIngestRequest,
)
from core.ingest.security import require_api_key
from core.ingest.services.ea_state import ingest_ea_state
from core.ingest.services.equity import ingest_equity
from core.ingest.services.execution import ingest_execution
from core.ingest.services.heartbeat import ingest_heartbeat
from core.ingest.services.positions import ingest_positions
from core.ingest.services.signals import ingest_signals
from core.ingest.services.trades import ingest_trades
from core.notifications.dispatch import dispatch_new_alerts
from core.redis import get_redis
from core.services.f6_evaluation import evaluate_f5_candidates_for_account
from core.services.f6_staging import evaluate_f6_candidates_for_account
from core.services.incubation_observation import advance_observed_f4_candidates
from core.state_machines.types import ChallengerConfig, PipelineGateConfig

router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(require_api_key)])

# Los umbrales pertenecen a PipelineGateConfig/configuración versionada; este
# router sólo reactiva el evaluador cuando entra telemetría read-only.
_PIPELINE_GATE_CONFIG = PipelineGateConfig()
_CHALLENGER_CONFIG = ChallengerConfig()


@router.post("/trades", response_model=IngestResponse)
async def post_trades(
    req: TradesIngestRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_trades(session, account, req)
    # La ingesta se confirma antes de evaluar, por el mismo criterio que
    # `post_positions`: el trabajo que no es la ingesta va DESPUES del commit.
    # Evaluando dentro de la transaccion, los locks de las filas de `trade` se
    # retienen durante todo el pipeline y los lotes solapados del conector se
    # serializan unos detras de otros hasta llenar el pool. El trade es dato
    # primario e idempotente; la evaluacion es derivada y se repite en el
    # siguiente lote o en el barrido del worker.
    await session.commit()
    await evaluate_f5_candidates_for_account(session, redis, account.id, _PIPELINE_GATE_CONFIG)
    await evaluate_f6_candidates_for_account(
        session, redis, account.id, _PIPELINE_GATE_CONFIG, _CHALLENGER_CONFIG
    )
    await session.commit()
    return IngestResponse(**outcome._asdict())


@router.post("/positions", response_model=IngestResponse)
async def post_positions(
    req: PositionsIngestRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """P5 (PARTE 2/16 criterio 12): una posicion sin SL dispara una `Alert`
    CRITICA (`services/positions.py::_apply_p5_check`, misma transaccion) y
    debe llegar a Telegram en <60s -- no puede esperar al proximo barrido
    ARQ (el mas frecuente, killswitch, es cada 1 min). Por eso el despacho
    va inline aqui, no en un `task_*` de `jobs/tasks.py`, siempre DESPUES
    del commit (un fallo de red de Telegram no debe arriesgar un rollback
    de dominio)."""
    run_start = datetime.now(UTC)
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_positions(session, account, req)
    await session.commit()
    # redis-py stub tipa Redis.rpush como Awaitable[int] | int (soporta
    # pipelines sincronas) -- nunca subtipo estructural del retorno
    # `Coroutine[..., object]` que exige el Protocol `_RedisLike`
    # (dispatch.py). Mismo criterio ya usado en este repo para friccion de
    # stubs (pubsub.aclose() en ws/bridge.py, .loc/.items() de pandas).
    await dispatch_new_alerts(session, redis, http_client, settings, run_start)  # type: ignore[arg-type]
    return IngestResponse(**outcome._asdict())


@router.post("/equity", response_model=IngestResponse)
async def post_equity(
    req: EquityIngestRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_equity(session, account, req)
    # Mismo criterio que en `post_trades`: confirmar la ingesta antes de
    # evaluar, para no retener sus locks durante todo el pipeline.
    await session.commit()
    await advance_observed_f4_candidates(session, redis, account)
    await evaluate_f5_candidates_for_account(session, redis, account.id, _PIPELINE_GATE_CONFIG)
    await evaluate_f6_candidates_for_account(
        session, redis, account.id, _PIPELINE_GATE_CONFIG, _CHALLENGER_CONFIG
    )
    await session.commit()
    return IngestResponse(**outcome._asdict())


@router.post("/heartbeat", response_model=IngestResponse)
async def post_heartbeat(
    req: HeartbeatIngestRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_heartbeat(session, account, req)
    await session.flush()
    await advance_observed_f4_candidates(session, redis, account)
    await evaluate_f5_candidates_for_account(session, redis, account.id, _PIPELINE_GATE_CONFIG)
    await evaluate_f6_candidates_for_account(
        session, redis, account.id, _PIPELINE_GATE_CONFIG, _CHALLENGER_CONFIG
    )
    await session.commit()
    return IngestResponse(**outcome._asdict())


@router.post("/signals", response_model=IngestResponse)
async def post_signals(
    req: SignalsIngestRequest, session: AsyncSession = Depends(get_session)
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_signals(session, account, req)
    await session.commit()
    return IngestResponse(**outcome._asdict())


@router.post("/execution", response_model=IngestResponse)
async def post_execution(
    req: ExecutionIngestRequest, session: AsyncSession = Depends(get_session)
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_execution(session, account, req)
    await session.commit()
    return IngestResponse(**outcome._asdict())


@router.post("/ea_state", response_model=IngestResponse)
async def post_ea_state(
    req: EaStateIngestRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_ea_state(session, account, req, redis)
    await session.flush()
    await evaluate_f5_candidates_for_account(session, redis, account.id, _PIPELINE_GATE_CONFIG)
    await evaluate_f6_candidates_for_account(
        session, redis, account.id, _PIPELINE_GATE_CONFIG, _CHALLENGER_CONFIG
    )
    await session.commit()
    return IngestResponse(**outcome._asdict())
