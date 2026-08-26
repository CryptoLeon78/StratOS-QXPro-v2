"""PARTE 9.2: `GET /api/v1/checklists/current` + `POST /{id}/items/{item}/sign`
-- checklists periodicas (7.9/14). Reutiliza `checklists.py` (core/services/,
ya existe, G5). `{id}` es el `checklist_type` (SUNDAY/BIWEEKLY/MONTHLY/
QUARTERLY/ANNUAL) -- no hay un id numerico hasta que `ChecklistRun` se
cierra (una sola fila inmutable por periodo)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import ChecklistType
from core.db.models.governance import User
from core.services.checklists import (
    DEFAULT_CHECKLIST_CATALOG,
    ChecklistCatalog,
    get_progress,
    period_key_for,
    sign_item,
)

router = APIRouter(
    prefix="/api/v1/checklists", tags=["checklists"], dependencies=[Depends(get_current_user)]
)

_CATALOG = ChecklistCatalog()


class ChecklistItemProgress(BaseModel):
    item_key: str
    signed: bool
    signed_by: str | None


class ChecklistProgressResponse(BaseModel):
    checklist_type: ChecklistType
    period_key: str
    items: list[ChecklistItemProgress]
    completed: bool


class SignResponse(BaseModel):
    completed: bool
    progress: ChecklistProgressResponse


async def _progress(
    session: AsyncSession, checklist_type: ChecklistType, now: datetime
) -> ChecklistProgressResponse:
    period_key = period_key_for(checklist_type, now)
    signatures = await get_progress(session, checklist_type, period_key)
    signed_by_item = {s.item_key: s.signed_by for s in signatures}
    catalog_items = DEFAULT_CHECKLIST_CATALOG[checklist_type]
    items = [
        ChecklistItemProgress(
            item_key=item, signed=item in signed_by_item, signed_by=signed_by_item.get(item)
        )
        for item in catalog_items
    ]
    return ChecklistProgressResponse(
        checklist_type=checklist_type,
        period_key=period_key,
        items=items,
        completed=all(i.signed for i in items),
    )


@router.get("/current", response_model=ChecklistProgressResponse)
async def current_checklist(
    checklist_type: ChecklistType, session: AsyncSession = Depends(get_session)
) -> ChecklistProgressResponse:
    return await _progress(session, checklist_type, datetime.now(UTC))


@router.post("/{checklist_type}/items/{item_key}/sign", response_model=SignResponse)
async def sign(
    checklist_type: ChecklistType,
    item_key: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SignResponse:
    now = datetime.now(UTC)
    try:
        run = await sign_item(session, checklist_type, item_key, user.email, _CATALOG, now)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await session.commit()
    progress = await _progress(session, checklist_type, now)
    return SignResponse(completed=run is not None, progress=progress)
