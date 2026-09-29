"""Alcance por cuenta (ADR 0013): `?account_id=` opcional y validado, comun a
todos los endpoints de lectura. `None` conserva el comportamiento de
portfolio (uso interno: sweeps, jobs); la UI siempre lo envia."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.base import get_session
from core.db.models.accounts import Account


async def get_account_scope(
    account_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
) -> int | None:
    if account_id is None:
        return None
    exists = (
        await session.execute(select(Account.id).where(Account.id == account_id))
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="account not found")
    return account_id


AccountScope = Annotated[int | None, Depends(get_account_scope)]
