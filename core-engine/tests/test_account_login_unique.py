"""G10/migracion 0c2d: `Account.login` UNIQUE (docs/backlog.md, encontrado en
G4) -- sin esto, `ingest/accounts.py::resolve_account` podia lanzar
MultipleResultsFound (500) en vez de fallar limpio ante un seed con logins
duplicados."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import AccountFactory


async def test_account_login_is_unique(db_session: AsyncSession) -> None:
    db_session.add(AccountFactory(login="123456"))
    await db_session.commit()

    db_session.add(AccountFactory(login="123456"))
    try:
        await db_session.commit()
        raise AssertionError("se esperaba IntegrityError por login duplicado")
    except IntegrityError:
        await db_session.rollback()


async def test_different_logins_coexist(db_session: AsyncSession) -> None:
    db_session.add(AccountFactory(login="111111"))
    db_session.add(AccountFactory(login="222222"))
    await db_session.commit()
