"""PARTE 12 G1, criterio de salida: "test de inmutabilidad por permisos".
P6/P15.3: el rol `stratos_app` puede INSERT/SELECT en las 6 tablas
inmutables pero nunca UPDATE/DELETE — verificado contra Postgres de verdad
(no mockeado), conectado como ese rol restringido (fixture `app_engine`).
"""

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.db.enums import DecisionStatus
from core.db.models.accounts import Account, Bot
from core.db.models.decisions import Decision, DecisionLog, KillSwitchEvent, SemaphoreTransition
from core.db.models.governance import ChecklistRun, WithdrawalLog
from core.db.models.market import IngestBatch
from tests.factories import (
    AccountFactory,
    BotFactory,
    ChecklistRunFactory,
    DecisionLogFactory,
    IngestBatchFactory,
    KillSwitchEventFactory,
    SemaphoreTransitionFactory,
    WithdrawalLogFactory,
)


@pytest_asyncio.fixture
async def app_session(app_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(app_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


async def _create_account(session: AsyncSession) -> Account:
    account = AccountFactory()
    session.add(account)
    await session.commit()
    return account


async def _create_bot(session: AsyncSession, account_id: int) -> Bot:
    bot = BotFactory(account_id=account_id)
    session.add(bot)
    await session.commit()
    return bot


async def _assert_update_and_delete_denied(
    session: AsyncSession, model: type[Any], pk_value: Any, set_values: dict[str, Any]
) -> None:
    pk_col = next(iter(model.__table__.primary_key.columns))

    with pytest.raises(DBAPIError, match="InsufficientPrivilege"):
        await session.execute(update(model).where(pk_col == pk_value).values(**set_values))
    await session.rollback()

    with pytest.raises(DBAPIError, match="InsufficientPrivilege"):
        await session.execute(delete(model).where(pk_col == pk_value))
    await session.rollback()


async def test_decision_log_insert_ok_update_delete_denied(app_session: AsyncSession) -> None:
    row = DecisionLogFactory()
    app_session.add(row)
    await app_session.commit()

    await _assert_update_and_delete_denied(app_session, DecisionLog, row.id, {"module": "x"})


async def test_ingest_batch_insert_ok_update_delete_denied(app_session: AsyncSession) -> None:
    account = await _create_account(app_session)
    row = IngestBatchFactory(account_id=account.id)
    app_session.add(row)
    await app_session.commit()

    await _assert_update_and_delete_denied(app_session, IngestBatch, row.id, {"records": 2})


async def test_semaphore_transition_insert_ok_update_delete_denied(
    app_session: AsyncSession,
) -> None:
    account = await _create_account(app_session)
    bot = await _create_bot(app_session, account.id)
    row = SemaphoreTransitionFactory(bot_id=bot.id)
    app_session.add(row)
    await app_session.commit()

    await _assert_update_and_delete_denied(
        app_session, SemaphoreTransition, row.id, {"confirmed_by": "operator"}
    )


async def test_killswitch_event_insert_ok_update_delete_denied(app_session: AsyncSession) -> None:
    row = KillSwitchEventFactory()
    app_session.add(row)
    await app_session.commit()

    await _assert_update_and_delete_denied(app_session, KillSwitchEvent, row.id, {"level": 2})


async def test_withdrawal_log_insert_ok_update_delete_denied(app_session: AsyncSession) -> None:
    row = WithdrawalLogFactory()
    app_session.add(row)
    await app_session.commit()

    await _assert_update_and_delete_denied(
        app_session, WithdrawalLog, row.id, {"amount": Decimal("1.00")}
    )


async def test_checklist_run_insert_ok_update_delete_denied(app_session: AsyncSession) -> None:
    row = ChecklistRunFactory()
    app_session.add(row)
    await app_session.commit()

    await _assert_update_and_delete_denied(app_session, ChecklistRun, row.id, {"completed": False})


async def test_decision_is_mutable_for_contrast(app_session: AsyncSession) -> None:
    """Control negativo: `Decision` (no es una de las 6 inmutables) SI admite
    UPDATE para stratos_app — confirma que el test anterior mide lo que
    dice medir y no un fallo generico de permisos."""
    row = Decision(
        ts=DecisionLogFactory().ts,
        module="test",
        title="t",
        description="d",
        instruction_text="i",
        evidence=None,
        status=DecisionStatus.PENDING,
        decided_at=None,
        decided_by=None,
        postpone_until=None,
    )
    app_session.add(row)
    await app_session.commit()

    await app_session.execute(
        update(Decision).where(Decision.id == row.id).values(status=DecisionStatus.CONFIRMED)
    )
    await app_session.commit()
