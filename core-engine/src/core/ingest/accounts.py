"""PARTE 9.1: resolucion de `account_login` -> `Account`. Toda ruta de
ingesta arranca por aqui."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account


async def resolve_account(session: AsyncSession, account_login: str) -> Account:
    """`Account.login` es UNIQUE desde G10 (migracion aditiva, cierra el gap
    de G4/ASSUMPTIONS/backlog) -- `scalar_one_or_none()` nunca puede
    encontrar mas de una fila, la constraint de BBDD lo garantiza."""
    result = await session.execute(select(Account).where(Account.login == account_login))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"unknown account_login: {account_login}"
        )
    return account
