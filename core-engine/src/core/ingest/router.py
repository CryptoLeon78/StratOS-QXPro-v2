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

router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(require_api_key)])


@router.post("/trades", response_model=IngestResponse)
async def post_trades(
    req: TradesIngestRequest, session: AsyncSession = Depends(get_session)
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_trades(session, account, req)
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
    req: EquityIngestRequest, session: AsyncSession = Depends(get_session)
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_equity(session, account, req)
    await session.commit()
    return IngestResponse(**outcome._asdict())


@router.post("/heartbeat", response_model=IngestResponse)
async def post_heartbeat(
    req: HeartbeatIngestRequest, session: AsyncSession = Depends(get_session)
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_heartbeat(session, account, req)
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
    req: EaStateIngestRequest, session: AsyncSession = Depends(get_session)
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_ea_state(session, account, req)
    await session.commit()
    return IngestResponse(**outcome._asdict())
