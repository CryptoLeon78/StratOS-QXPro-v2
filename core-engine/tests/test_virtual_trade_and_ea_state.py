"""G4/migracion 011e: `VirtualTrade` (POST /ingest/signals, trades virtuales
NARANJA) y `EaState` (POST /ingest/ea_state, ultimo estado conocido por EA) -
tablas nuevas, aprobadas por el operador, fuera de las 25 de PARTE 5.2/G1.
Aqui solo se verifica que el esquema soporta lo que la ingesta real (unidades
siguientes) va a necesitar: unicidad y upsert."""

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.market import EaState, VirtualTrade
from tests.factories import AccountFactory, EaStateFactory, IngestBatchFactory, VirtualTradeFactory


async def test_virtual_trade_persists_and_is_queryable(db_session: AsyncSession) -> None:
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()
    batch = IngestBatchFactory(account_id=account.id)
    db_session.add(batch)
    await db_session.flush()

    vt = VirtualTradeFactory(account_id=account.id, ingest_batch_id=batch.id)
    db_session.add(vt)
    await db_session.commit()

    found = (
        await db_session.execute(select(VirtualTrade).where(VirtualTrade.id == vt.id))
    ).scalar_one()
    assert found.account_id == account.id
    assert found.bot_id is None  # huerfano permitido, igual que Trade
    assert found.signal_id == vt.signal_id


async def test_virtual_trade_unique_per_account_magic_signal(db_session: AsyncSession) -> None:
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()
    batch = IngestBatchFactory(account_id=account.id)
    db_session.add(batch)
    await db_session.flush()

    db_session.add(
        VirtualTradeFactory(account_id=account.id, ingest_batch_id=batch.id, signal_id="sig-1")
    )
    await db_session.commit()

    db_session.add(
        VirtualTradeFactory(account_id=account.id, ingest_batch_id=batch.id, signal_id="sig-1")
    )
    try:
        await db_session.commit()
        raise AssertionError("se esperaba IntegrityError por signal_id duplicado")
    except IntegrityError:
        await db_session.rollback()


async def test_ea_state_upserts_on_account_magic(db_session: AsyncSession) -> None:
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()
    account_id = account.id
    batch = IngestBatchFactory(account_id=account_id)
    db_session.add(batch)
    await db_session.flush()
    batch_id = batch.id

    ea = EaStateFactory(account_id=account_id, ingest_batch_id=batch_id, ea_version="1.0.0")
    db_session.add(ea)
    await db_session.commit()
    # Capturados antes del rollback de abajo: un rollback invalida TODOS los
    # objetos ORM de la sesion (incluso con expire_on_commit=False, que solo
    # cubre el caso commit) -- releerlos despues dispara un lazy-load
    # sincrono fuera de contexto greenlet (MissingGreenlet en modo async).
    magic_number = ea.magic_number
    last_ingested_at = ea.last_ingested_at

    # "ultimo estado conocido": una segunda fila con la misma PK
    # (account_id, magic_number) debe chocar con IntegrityError -- el UPSERT
    # real (ON CONFLICT DO UPDATE) vive en el servicio de ingesta, no aqui.
    # INSERT via Core (no ORM) para forzar que el choque llegue de verdad a
    # Postgres, en vez de que el identity map de la sesion lo intercepte antes.
    duplicate = insert(EaState).values(
        account_id=account_id,
        magic_number=magic_number,
        ea_version="1.0.1",
        mode="REAL",
        autotrading=True,
        schedule_filter=None,
        news_windows=None,
        ingest_batch_id=batch_id,
        last_ingested_at=last_ingested_at,
    )
    try:
        await db_session.execute(duplicate)
        await db_session.commit()
        raise AssertionError(
            "se esperaba IntegrityError por PK (account_id, magic_number) duplicada"
        )
    except IntegrityError:
        await db_session.rollback()

    stored = await db_session.get(EaState, (account_id, magic_number))
    assert stored is not None
    assert stored.ea_version == "1.0.0"


async def test_ea_state_stores_jsonb_fields(db_session: AsyncSession) -> None:
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()
    batch = IngestBatchFactory(account_id=account.id)
    db_session.add(batch)
    await db_session.flush()

    windows = [{"from": "2026-08-26T12:00:00Z", "to": "2026-08-26T13:00:00Z"}]
    ea = EaStateFactory(
        account_id=account.id,
        ingest_batch_id=batch.id,
        schedule_filter={"days": ["MON", "TUE"]},
        news_windows=windows,
    )
    db_session.add(ea)
    await db_session.commit()

    stored = await db_session.get(EaState, (account.id, ea.magic_number))
    assert stored is not None
    assert stored.schedule_filter == {"days": ["MON", "TUE"]}
    assert stored.news_windows == windows
