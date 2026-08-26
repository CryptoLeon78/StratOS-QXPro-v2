"""PARTE 9.1: rutas de ingesta. Autenticadas via `X-API-Key`
(`require_api_key`), finas a proposito -- resuelven la cuenta, delegan en
`services/`, comitean. La logica real vive en `services/`, testeable sin
HTTP."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.base import get_session
from core.ingest.accounts import resolve_account
from core.ingest.schemas import EquityIngestRequest, IngestResponse, TradesIngestRequest
from core.ingest.security import require_api_key
from core.ingest.services.equity import ingest_equity
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


@router.post("/equity", response_model=IngestResponse)
async def post_equity(
    req: EquityIngestRequest, session: AsyncSession = Depends(get_session)
) -> IngestResponse:
    account = await resolve_account(session, req.account_login)
    outcome = await ingest_equity(session, account, req)
    await session.commit()
    return IngestResponse(**outcome._asdict())
