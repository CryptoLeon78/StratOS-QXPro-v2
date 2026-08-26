"""PARTE 12 G1, criterio de salida: "test de sello IngestBatch". El sello
real (SHA-256 del payload canonico del lote) lo calcula el conector/ingest
en G4/G5; aqui se verifica que el esquema lo soporta y lo exige (PARTE 5.2:
"lotes sellados (hash+ts)", NOT NULL en `sha256`)."""

import hashlib

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.market import IngestBatch
from tests.factories import AccountFactory, IngestBatchFactory


async def test_ingest_batch_persists_with_valid_seal(db_session: AsyncSession) -> None:
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()

    payload = f"{account.id}-trades-1".encode()
    seal = hashlib.sha256(payload).hexdigest()
    batch = IngestBatchFactory(account_id=account.id, sha256=seal)
    db_session.add(batch)
    await db_session.commit()

    stored = await db_session.get(IngestBatch, batch.id)
    assert stored is not None
    assert stored.sha256 == seal
    assert len(stored.sha256) == 64
    assert stored.account_id == account.id
    assert stored.ts == batch.ts
    assert stored.server_ts == batch.server_ts


async def test_ingest_batch_requires_seal(db_session: AsyncSession) -> None:
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()

    batch = IngestBatch(
        ts=IngestBatchFactory().ts,
        connector_instance_id="connector-test-1",
        account_id=account.id,
        batch_type="trades",
        records=1,
        sha256=None,  # type: ignore[arg-type]
        server_ts=IngestBatchFactory().server_ts,
    )
    db_session.add(batch)

    try:
        await db_session.commit()
        raise AssertionError("se esperaba IntegrityError por sha256 NULL")
    except IntegrityError:
        await db_session.rollback()


async def test_ingest_batch_seal_is_queryable_by_hash(db_session: AsyncSession) -> None:
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()

    seal = hashlib.sha256(b"lote-2").hexdigest()
    batch = IngestBatchFactory(account_id=account.id, sha256=seal)
    db_session.add(batch)
    await db_session.commit()

    result = await db_session.execute(select(IngestBatch).where(IngestBatch.sha256 == seal))
    found = result.scalar_one()
    assert found.id == batch.id
