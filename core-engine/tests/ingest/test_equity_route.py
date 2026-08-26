"""PARTE 9.1: `POST /ingest/equity` end-to-end -- idempotencia (P9),
drawdown_pct calculado (diseno propio, ASSUMPTIONS G4: pico historico vs
nuevo)."""

from typing import Any

from httpx import AsyncClient
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.market import EquitySnapshot
from core.ingest.schemas import EquityIngestRequest
from tests.factories import AccountFactory
from tests.ingest.conftest import TEST_INGEST_API_KEY

HEADERS = {"X-API-Key": TEST_INGEST_API_KEY}


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _sealed_equity_payload(
    account_login: str,
    ts: str,
    equity: float,
    balance: float,
    connector_instance_id: str = "conn-1",
) -> dict[str, Any]:
    draft = {
        "account_login": account_login,
        "connector_instance_id": connector_instance_id,
        "ts": ts,
        "equity": equity,
        "balance": balance,
        "margin_level": 1500.0,
        "free_margin": 175000.0,
        "batch_sha256": "0" * 64,
    }
    parsed = EquityIngestRequest.model_validate(draft)
    canonical_record = parsed.model_dump(mode="json", exclude={"batch_sha256"})
    seal = compute_batch_sha256(account_login, "equity", [canonical_record])
    return {**draft, "batch_sha256": seal}


async def test_ingests_first_snapshot_with_zero_drawdown(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_equity_payload(account.login, "2026-08-26T12:00:00Z", 100000.0, 100000.0)
    response = await ingest_client.post("/ingest/equity", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1

    async with _session(db_connection) as session2:
        snap = (
            await session2.execute(
                select(EquitySnapshot).where(EquitySnapshot.account_id == account.id)
            )
        ).scalar_one()
        assert str(snap.drawdown_pct) == "0.000"


async def test_drawdown_computed_against_historical_peak(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    peak = _sealed_equity_payload(account.login, "2026-08-26T10:00:00Z", 100000.0, 100000.0)
    await ingest_client.post("/ingest/equity", json=peak, headers=HEADERS)

    dip = _sealed_equity_payload(account.login, "2026-08-26T11:00:00Z", 98000.0, 98000.0)
    response = await ingest_client.post("/ingest/equity", json=dip, headers=HEADERS)
    assert response.status_code == 200

    async with _session(db_connection) as session2:
        snap = (
            await session2.execute(select(EquitySnapshot).where(EquitySnapshot.equity == 98000))
        ).scalar_one()
        # (100000-98000)/100000*100 = 2.000
        assert str(snap.drawdown_pct) == "2.000"


async def test_zero_equity_does_not_crash_on_division(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    # margin call extremo: no deberia dividir por cero al calcular el pico
    payload = _sealed_equity_payload(account.login, "2026-08-26T12:00:00Z", 0.0, 0.0)
    response = await ingest_client.post("/ingest/equity", json=payload, headers=HEADERS)
    assert response.status_code == 200

    async with _session(db_connection) as session2:
        snap = (
            await session2.execute(
                select(EquitySnapshot).where(EquitySnapshot.account_id == account.id)
            )
        ).scalar_one()
        assert str(snap.drawdown_pct) == "0.000"


async def test_resend_same_snapshot_does_not_duplicate(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_equity_payload(account.login, "2026-08-26T12:00:00Z", 100000.0, 100000.0)
    first = await ingest_client.post("/ingest/equity", json=payload, headers=HEADERS)
    assert first.json()["accepted"] == 1

    second = await ingest_client.post("/ingest/equity", json=payload, headers=HEADERS)
    assert second.json()["accepted"] == 0
    assert second.json()["duplicated"] == 1

    async with _session(db_connection) as session2:
        rows = (
            await session2.execute(
                select(EquitySnapshot).where(EquitySnapshot.account_id == account.id)
            )
        ).scalars()
        assert len(list(rows)) == 1


async def test_tampered_seal_is_rejected_and_persists_nothing(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_equity_payload(account.login, "2026-08-26T12:00:00Z", 100000.0, 100000.0)
    seal = payload["batch_sha256"]
    payload["batch_sha256"] = ("0" if seal[0] != "0" else "1") + seal[1:]

    response = await ingest_client.post("/ingest/equity", json=payload, headers=HEADERS)
    assert response.status_code == 422

    async with _session(db_connection) as session2:
        result = await session2.execute(
            select(EquitySnapshot).where(EquitySnapshot.account_id == account.id)
        )
        assert result.first() is None


async def test_unknown_account_login_is_404(ingest_client: AsyncClient) -> None:
    payload = _sealed_equity_payload("no-such-login", "2026-08-26T12:00:00Z", 100000.0, 100000.0)
    response = await ingest_client.post("/ingest/equity", json=payload, headers=HEADERS)
    assert response.status_code == 404
