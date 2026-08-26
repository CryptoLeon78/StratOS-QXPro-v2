"""PARTE 9.1: rutas de ingesta. Autenticadas via `X-API-Key`
(`require_api_key`), finas a proposito -- resuelven la cuenta, delegan en
`services/`, comitean. La logica real vive en `services/`, testeable sin
HTTP."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.base import get_session
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
    req: PositionsIngestRequest, session: AsyncSession = Depends(get_session)
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_positions(session, account, req)
    await session.commit()
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
