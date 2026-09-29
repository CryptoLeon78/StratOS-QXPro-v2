"""G10 (docs/backlog.md): `GET /api/v1/alerts` -- lista de solo lectura
sobre `Alert` (ya poblada por watchdog.py/config_drift.py/audit.py/etc
desde G5, header.py solo la contaba nunca la listaba). Necesario para
"errores de EA" de la vista dominical (grupo n, PARTE 14: "revision
TECNICA -- errores de EA, desconexiones, ordenes rechazadas") -- sin
formula ni logica de negocio nueva, query directa."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.routers.scope import AccountScope, account_or_portfolio

router = APIRouter(
    prefix="/api/v1/alerts", tags=["alerts"], dependencies=[Depends(get_current_user)]
)


class AlertResponse(BaseModel):
    id: int
    ts: datetime
    level: AlertLevel
    module: str
    message: str
    action_required: str | None
    resolved: bool
    resolved_at: datetime | None
    account_id: int | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    account_id: AccountScope,
    module: str | None = None,
    include_resolved: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[Alert]:
    query = select(Alert).order_by(Alert.ts.desc())
    if module is not None:
        query = query.where(Alert.module == module)
    if account_id is not None:
        query = query.where(account_or_portfolio(Alert.account_id, account_id))
    if not include_resolved:
        query = query.where(Alert.resolved.is_(False))
    return list((await session.execute(query)).scalars().all())
